"""Environmental and Legal Compliance Statistics REST API endpoints."""

from typing import Any, Dict
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.models.entities import User
from src.security.dependencies import get_current_user
from src.services.stats_service import StatsService

router = APIRouter()


@router.get(
    "/environmental",
    summary="Get environmental impact metrics and Ley 225-20 compliance summary",
    status_code=status.HTTP_200_OK,
)
def get_environmental_impact(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve cumulative environmental metrics: oil diverted, water preserved, and CO2 avoided."""
    return StatsService.get_environmental_stats(db)
