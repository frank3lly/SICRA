"""Vehicle routing and dispatch itinerary REST API endpoints for SICRA."""

from datetime import date
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.models.entities import CollectionRoute, User
from src.models.enums import UserRole
from src.security.dependencies import require_role
from src.services.routing_service import RoutingService

router = APIRouter()


@router.post(
    "/generate-today",
    summary="Generate optimized daily collection route via Nearest Neighbor and 2-Opt",
    status_code=status.HTTP_200_OK,
)
def generate_today_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.COLLECTOR])),
):
    """Synthesize an optimal vehicle route visiting all containers currently in 80% alert status."""
    route = RoutingService.generate_daily_route(
        db=db,
        collector_user_id=current_user.id,
        target_date=date.today(),
    )
    return {
        "route_id": str(route.id),
        "scheduled_date": route.scheduled_date.isoformat(),
        "status": (
            route.status.value
            if hasattr(route.status, "value")
            else str(route.status)
        ),
        "total_distance_km": route.total_distance_km,
        "total_estimated_liters": route.total_estimated_volume_liters,
        "total_stops": len(
            [s for s in route.stops_order_json if not s.get("is_depot")]
        ),
        "itinerary": route.stops_order_json,
    }


@router.get(
    "/today",
    summary="Get active or suggested collection route for today",
)
def get_today_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.COLLECTOR])),
):
    """Retrieve the latest scheduled collection dispatch route for the current date."""
    today = date.today()
    route = (
        db.query(CollectionRoute)
        .filter(CollectionRoute.scheduled_date == today)
        .order_by(CollectionRoute.created_at.desc())
        .first()
    )

    if not route:
        # Check latest overall route as fallback
        route = (
            db.query(CollectionRoute)
            .order_by(CollectionRoute.created_at.desc())
            .first()
        )

    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No collection routes found",
        )

    return {
        "route_id": str(route.id),
        "scheduled_date": route.scheduled_date.isoformat(),
        "status": (
            route.status.value
            if hasattr(route.status, "value")
            else str(route.status)
        ),
        "total_distance_km": route.total_distance_km,
        "total_estimated_liters": route.total_estimated_volume_liters,
        "total_stops": len(
            [s for s in route.stops_order_json if not s.get("is_depot")]
        ),
        "itinerary": route.stops_order_json,
    }


@router.post(
    "/{id}/confirm-stop/{business_id}",
    summary="Driver confirmation of pickup stop and container tare reset",
)
def confirm_route_stop(
    id: str = Path(..., description="UUID of the collection route"),
    business_id: str = Path(..., description="UUID of the visited establishment"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.COLLECTOR])),
):
    """Confirm driver arrival and oil collection at an establishment stop."""
    return RoutingService.confirm_stop(route_id=id, business_id=business_id, db=db)
