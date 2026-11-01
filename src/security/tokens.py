"""JWT Token generation, verification, and password hashing engine for SICRA."""

from datetime import datetime, timedelta, timezone
import os
from typing import Any, Dict, Optional
import bcrypt

# Ensure bcrypt 4.x compatibility with passlib
if not hasattr(bcrypt, "__about__"):

    class _About:
        __version__ = getattr(bcrypt, "__version__", "4.0.1")

    bcrypt.__about__ = _About()

# Workaround for passlib 1.7.4 password length check with bcrypt >= 4.0.0
_orig_hashpw = bcrypt.hashpw
_orig_checkpw = bcrypt.checkpw


def _safe_hashpw(password, salt):
    if isinstance(password, str):
        password = password.encode("utf-8")
    if len(password) > 72:
        password = password[:72]
    return _orig_hashpw(password, salt)


def _safe_checkpw(password, hashed_password):
    if isinstance(password, str):
        password = password.encode("utf-8")
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode("utf-8")
    if len(password) > 72:
        password = password[:72]
    return _orig_checkpw(password, hashed_password)


bcrypt.hashpw = _safe_hashpw
bcrypt.checkpw = _safe_checkpw

from jose import JWTError, jwt
from passlib.context import CryptContext

# Configuration constants
JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY", "sicra_super_secret_jwt_key_development_2026_default"
)
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")
)

# Passlib CryptContext configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password using Bcrypt via passlib."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a Bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """Generate a cryptographically signed JWT access token.

    Claims included:
    - sub: User email / subject
    - role: User role string
    - business_id: Associated business ID (if applicable)
    - exp: UTC expiration timestamp
    """
    to_encode = data.copy()

    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token.

    Raises:
        JWTError: If signature is invalid, token expired, or malformed.
    """
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
