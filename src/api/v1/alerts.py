"""Operational Alert REST API endpoints for SICRA."""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.models.entities import User
from src.models.enums import UserRole
from src.security.dependencies import require_role
from src.services.alert_service import AlertService

router = APIRouter()


@router.get(
    "/active",
    response_model=List[Dict[str, Any]],
    summary="List all unresolved 80% and critical operational alerts",
)
def get_active_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.COLLECTOR])),
):
    """Retrieve all unresolved alerts with associated business and container metrics."""
    return AlertService.get_active_alerts(db)


@router.post(
    "/{id}/resolve",
    summary="Manually resolve an operational alert",
    status_code=status.HTTP_200_OK,
)
def resolve_alert(
    id: str = Path(..., description="UUID of the operational alert"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.COLLECTOR])),
):
    """Mark an active operational alert as manually resolved."""
    alert = AlertService.resolve_alert(id, db)
    return {
        "id": str(alert.id),
        "container_id": str(alert.container_id),
        "alert_type": (
            alert.alert_type.value
            if hasattr(alert.alert_type, "value")
            else str(alert.alert_type)
        ),
        "is_resolved": alert.is_resolved,
        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
    }
