"""API v1 router composition for SICRA."""

from fastapi import APIRouter
from src.api.v1.auth import router as auth_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth_router, prefix="/auth", tags=["Authentication & RBAC"])

__all__ = ["api_v1_router"]
