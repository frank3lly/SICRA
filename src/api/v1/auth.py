"""Authentication and access control endpoints for SICRA API."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.models.entities import Container, User
from src.models.enums import UserRole
from src.security.dependencies import (
    get_current_user,
    require_role,
    verify_business_access,
)
from src.security.tokens import create_access_token, verify_password

router = APIRouter()


class LoginRequest(BaseModel):
    """Credentials payload for JWT token issuance."""

    email: Optional[str] = None
    username: Optional[str] = None
    password: str


class UserResponse(BaseModel):
    """Public user identity and role representation."""

    id: str
    email: str
    full_name: str
    role: str
    business_id: Optional[str] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Bearer access token payload."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive JWT token",
)
async def login(
    request: Request,
    db: Session = Depends(get_db),
):
    """Issue JWT access token upon successful credential verification.

    Accepts either JSON payload (`email` or `username` + `password`)
    or standard `application/x-www-form-urlencoded` form data.
    """
    content_type = request.headers.get("content-type", "")
    identifier: Optional[str] = None
    password: Optional[str] = None

    if "application/json" in content_type:
        try:
            body = await request.json()
            identifier = body.get("email") or body.get("username")
            password = body.get("password")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload",
            )
    else:
        try:
            form = await request.form()
            identifier = form.get("username") or form.get("email")
            password = form.get("password")
        except Exception:
            pass

    if not identifier or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing email/username or password",
        )

    user = db.query(User).filter(User.email == identifier.strip().lower()).first()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    role_val = (
        user.role.value if hasattr(user.role, "value") else str(user.role)
    )
    token = create_access_token(
        data={
            "sub": user.email,
            "role": role_val,
            "business_id": user.business_id,
        }
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=role_val,
            business_id=user.business_id,
            is_active=user.is_active,
        ),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the profile information of the currently authenticated user."""
    role_val = (
        current_user.role.value
        if hasattr(current_user.role, "value")
        else str(current_user.role)
    )
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=role_val,
        business_id=current_user.business_id,
        is_active=current_user.is_active,
    )


@router.get(
    "/admin-only",
    summary="Admin-restricted verification endpoint",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def admin_only_check(current_user: User = Depends(get_current_user)):
    """Restricted endpoint accessible exclusively to administrators."""
    return {
        "status": "ok",
        "message": "Admin authorization verified",
        "email": current_user.email,
    }


@router.get(
    "/collector-only",
    summary="Collector-restricted verification endpoint",
    dependencies=[Depends(require_role([UserRole.COLLECTOR, UserRole.ADMIN]))],
)
def collector_only_check(current_user: User = Depends(get_current_user)):
    """Restricted endpoint accessible to collectors and administrators."""
    return {
        "status": "ok",
        "message": "Collector authorization verified",
        "email": current_user.email,
    }


@router.get(
    "/business-data/{business_id}",
    summary="Data isolation verified business endpoint",
)
def access_business_data(
    business_id: str,
    current_user: User = Depends(get_current_user),
):
    """Retrieve business-level data subject to data isolation policy."""
    verify_business_access(business_id, current_user)
    return {
        "status": "access_granted",
        "business_id": business_id,
        "email": current_user.email,
    }


@router.get(
    "/container-telemetry-check/{container_id}",
    summary="Data isolation container telemetry inspection",
)
def check_container_access(
    container_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verify that a business owner can only inspect telemetry belonging to their container."""
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container not found",
        )

    verify_business_access(container.business_id, current_user)
    return {
        "status": "access_granted",
        "container_id": container.id,
        "business_id": container.business_id,
        "email": current_user.email,
    }
