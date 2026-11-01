"""API v1 router composition for SICRA."""

from fastapi import APIRouter
from src.api.v1.alerts import router as alerts_router
from src.api.v1.auth import router as auth_router
from src.api.v1.businesses import router as businesses_router
from src.api.v1.containers import router as containers_router
from src.api.v1.predictions import router as predictions_router
from src.api.v1.routes import router as routes_router
from src.api.v1.stats import router as stats_router
from src.api.v1.telemetry import router as telemetry_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth_router, prefix="/auth", tags=["Authentication & RBAC"])
api_v1_router.include_router(telemetry_router, prefix="/telemetry", tags=["Telemetry Ingestion & Sensors"])
api_v1_router.include_router(businesses_router, prefix="/businesses", tags=["Food Businesses"])
api_v1_router.include_router(containers_router, prefix="/containers", tags=["Smart Containers"])
api_v1_router.include_router(alerts_router, prefix="/alerts", tags=["Operational Alerts"])
api_v1_router.include_router(routes_router, prefix="/routes", tags=["Dynamic Route Optimizer"])
api_v1_router.include_router(predictions_router, prefix="/predictions", tags=["Predictive Analytics"])
api_v1_router.include_router(stats_router, prefix="/stats", tags=["Environmental Statistics & Compliance"])

__all__ = ["api_v1_router"]
