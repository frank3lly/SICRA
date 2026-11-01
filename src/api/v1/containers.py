"""Smart container hardware and calibration REST API endpoints for SICRA."""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.models.entities import Business, Container, User
from src.models.enums import UserRole
from src.security.dependencies import (
    get_current_user,
    verify_business_access,
)

router = APIRouter()


@router.get(
    "/",
    summary="Fleet smart containers overview",
)
def list_containers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Retrieve list of smart containers scoped to the caller's role."""
    user_role_val = (
        current_user.role.value
        if hasattr(current_user.role, "value")
        else str(current_user.role)
    )

    query = db.query(Container, Business).join(Business, Container.business_id == Business.id)
    if user_role_val == UserRole.BUSINESS_OWNER.value:
        query = query.filter(Container.business_id == current_user.business_id)

    results = []
    for container, business in query.order_by(Container.created_at.desc()).all():
        results.append(
            {
                "id": str(container.id),
                "business_id": str(container.business_id),
                "business_name": business.name,
                "device_token": container.device_token,
                "capacity_liters": container.capacity_liters,
                "tare_weight_kg": container.tare_weight_kg,
                "oil_density_kg_l": container.oil_density_kg_l,
                "status": (
                    container.status.value
                    if hasattr(container.status, "value")
                    else str(container.status)
                ),
                "current_volume_liters": container.current_volume_liters,
                "current_fill_percentage": container.current_fill_percentage,
                "last_telemetry_at": (
                    container.last_telemetry_at.isoformat()
                    if container.last_telemetry_at
                    else None
                ),
            }
        )
    return results


@router.get(
    "/my-container",
    summary="Get authenticated Business Owner's primary container",
)
def get_my_container(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve isolated smart container view for a business owner."""
    if not current_user.business_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No business establishment associated with this user profile",
        )

    container = (
        db.query(Container)
        .filter(Container.business_id == current_user.business_id)
        .first()
    )
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No container registered for this business establishment",
        )

    business = db.query(Business).filter(Business.id == current_user.business_id).first()

    return {
        "id": str(container.id),
        "business_id": str(container.business_id),
        "business_name": business.name if business else "My Business",
        "capacity_liters": container.capacity_liters,
        "tare_weight_kg": container.tare_weight_kg,
        "oil_density_kg_l": container.oil_density_kg_l,
        "status": (
            container.status.value
            if hasattr(container.status, "value")
            else str(container.status)
        ),
        "current_volume_liters": container.current_volume_liters,
        "current_fill_percentage": container.current_fill_percentage,
        "last_telemetry_at": (
            container.last_telemetry_at.isoformat()
            if container.last_telemetry_at
            else None
        ),
    }


@router.get(
    "/{id}",
    summary="Get container calibration and current status",
)
def get_container_detail(
    id: str = Path(..., description="UUID of the smart container"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve container hardware calibrations subject to tenant data isolation."""
    container = db.query(Container).filter(Container.id == id).first()
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Container '{id}' not found",
        )

    verify_business_access(container.business_id, current_user)

    business = db.query(Business).filter(Business.id == container.business_id).first()

    return {
        "id": str(container.id),
        "business_id": str(container.business_id),
        "business_name": business.name if business else None,
        "device_token": container.device_token,
        "capacity_liters": container.capacity_liters,
        "tare_weight_kg": container.tare_weight_kg,
        "oil_density_kg_l": container.oil_density_kg_l,
        "status": (
            container.status.value
            if hasattr(container.status, "value")
            else str(container.status)
        ),
        "current_volume_liters": container.current_volume_liters,
        "current_fill_percentage": container.current_fill_percentage,
        "last_telemetry_at": (
            container.last_telemetry_at.isoformat()
            if container.last_telemetry_at
            else None
        ),
    }
