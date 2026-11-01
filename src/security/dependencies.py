"""FastAPI security dependencies for authentication, RBAC, and data isolation."""

from typing import List, Optional, Union
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.models.entities import User
from src.models.enums import UserRole
from src.security.tokens import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Validate JWT token, verify user existence, and assert active account status.

    Raises:
        HTTPException: 401 if credentials/token invalid or expired.
        HTTPException: 403 if user account is deactivated.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        email: Optional[str] = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    except Exception:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


class RoleGuard:
    """Callable dependency enforcing Role-Based Access Control (RBAC)."""

    def __init__(self, allowed_roles: Union[UserRole, List[UserRole], str, List[str]]):
        if isinstance(allowed_roles, (list, tuple, set)):
            self.allowed_roles = [
                r.value if hasattr(r, "value") else str(r) for r in allowed_roles
            ]
        else:
            self.allowed_roles = [
                allowed_roles.value
                if hasattr(allowed_roles, "value")
                else str(allowed_roles)
            ]

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        user_role_val = (
            current_user.role.value
            if hasattr(current_user.role, "value")
            else str(current_user.role)
        )
        if user_role_val not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Insufficient privileges for this resource",
            )
        return current_user


def require_role(
    required_roles: Union[UserRole, List[UserRole], str, List[str]],
) -> RoleGuard:
    """Dependency factory returning a RoleGuard for the specified roles."""
    return RoleGuard(required_roles)


def verify_business_access(
    business_id: Optional[str],
    current_user: User,
) -> None:
    """Enforce data isolation safeguard preventing business owners from accessing competitors' data.

    Admins and Collectors can access any business data.
    Business owners are strictly restricted to data matching their own business_id.

    Raises:
        HTTPException: 403 Forbidden if a Business Owner attempts cross-tenant access.
    """
    user_role_val = (
        current_user.role.value
        if hasattr(current_user.role, "value")
        else str(current_user.role)
    )

    if user_role_val == UserRole.BUSINESS_OWNER.value:
        if not current_user.business_id or str(current_user.business_id) != str(business_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Data isolation prevents access to other businesses' data",
            )
