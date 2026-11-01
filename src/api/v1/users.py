"""User account management and administration endpoints for SICRA."""

from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.models.entities import Business, User
from src.models.enums import UserRole
from src.security.dependencies import require_role
from src.security.tokens import hash_password

router = APIRouter(tags=["User Management"])


class UserCreatePayload(BaseModel):
    """Payload for creating and provisioning a new system user."""

    full_name: str = Field(
        ...,
        min_length=2,
        max_length=150,
        description="User full legal or commercial name",
    )
    email: str = Field(
        ...,
        max_length=150,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        description="Unique email address for login",
    )
    password: str = Field(
        ...,
        min_length=8,
        description="Cleartext password (hashed with bcrypt server-side)",
    )
    role: UserRole = Field(
        ...,
        description="Assigned system role: ADMIN, COLLECTOR, or BUSINESS_OWNER",
    )
    business_id: Optional[str] = Field(
        None,
        description="UUID of business to bind (Required if role is BUSINESS_OWNER)",
    )


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Create new platform user (Admin only)",
)
def create_user(
    payload: UserCreatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> Dict[str, Any]:
    """Create a new platform user with designated RBAC privileges."""
    # 1. Verify email uniqueness
    normalized_email = payload.email.lower().strip()
    existing_user = db.query(User).filter(User.email == normalized_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El correo '{normalized_email}' ya se encuentra registrado en el sistema.",
        )

    # 2. Validate business binding if BUSINESS_OWNER
    business_name: Optional[str] = None
    if payload.role == UserRole.BUSINESS_OWNER:
        if not payload.business_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Se requiere asignar un comercio ('business_id') para usuarios con rol 'BUSINESS_OWNER'.",
            )
        business = db.query(Business).filter(Business.id == payload.business_id).first()
        if not business:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El comercio especificado no existe.",
            )
        business_name = business.name

    # 3. Hash password securely with bcrypt
    hashed_pw = hash_password(payload.password)

    # 4. Create and persist user entity
    new_user = User(
        id=str(uuid.uuid4()),
        email=normalized_email,
        hashed_password=hashed_pw,
        full_name=payload.full_name.strip(),
        role=payload.role,
        business_id=payload.business_id if payload.role == UserRole.BUSINESS_OWNER else None,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "id": str(new_user.id),
        "email": new_user.email,
        "full_name": new_user.full_name,
        "role": (
            new_user.role.value
            if hasattr(new_user.role, "value")
            else str(new_user.role)
        ),
        "business_id": str(new_user.business_id) if new_user.business_id else None,
        "business_name": business_name,
        "is_active": new_user.is_active,
        "created_at": new_user.created_at.isoformat() if new_user.created_at else None,
    }


@router.get(
    "/",
    summary="List all platform users (Admin only)",
)
def list_users(
    role: Optional[str] = Query(None, description="Filter by user role"),
    search: Optional[str] = Query(None, description="Search by email or name"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> List[Dict[str, Any]]:
    """List system users with optional role and search filters."""
    query = db.query(User).outerjoin(Business, User.business_id == Business.id)

    if role:
        query = query.filter(User.role == role)

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(User.email.ilike(term) | User.full_name.ilike(term))

    users = query.order_by(User.full_name.asc()).all()
    results = []
    for u in users:
        results.append(
            {
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role.value if hasattr(u.role, "value") else str(u.role),
                "business_id": str(u.business_id) if u.business_id else None,
                "business_name": u.business.name if u.business else None,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
        )
    return results
