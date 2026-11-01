"""Business entity management and gastronomy establishment REST API endpoints."""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.models.entities import Business, Container, User
from src.models.enums import BusinessType, UserRole
from src.security.dependencies import (
    get_current_user,
    require_role,
    verify_business_access,
)

router = APIRouter()


class BusinessCreatePayload(BaseModel):
    """Payload for onboarding a new food business establishment."""

    name: str = Field(..., max_length=150)
    business_type: BusinessType
    num_fryers: int = Field(1, ge=1)
    avg_daily_customers: int = Field(100, ge=0)
    latitude: float
    longitude: float
    address: str = Field(..., max_length=255)
    city: str = Field("San Pedro de Macorís", max_length=100)
    contact_name: str | None = Field(None, max_length=120)
    phone: str | None = Field(None, max_length=30)
    is_active: bool = True


@router.get(
    "/",
    summary="List businesses with geographic coordinates and container overview",
)
def list_businesses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """List establishments according to RBAC scope."""
    user_role_val = (
        current_user.role.value
        if hasattr(current_user.role, "value")
        else str(current_user.role)
    )

    query = db.query(Business)
    if user_role_val == UserRole.BUSINESS_OWNER.value:
        query = query.filter(Business.id == current_user.business_id)

    businesses = query.order_by(Business.name.asc()).all()
    results = []
    for b in businesses:
        results.append(
            {
                "id": str(b.id),
                "name": b.name,
                "business_type": (
                    b.business_type.value
                    if hasattr(b.business_type, "value")
                    else str(b.business_type)
                ),
                "num_fryers": b.num_fryers,
                "avg_daily_customers": b.avg_daily_customers,
                "latitude": b.latitude,
                "longitude": b.longitude,
                "address": b.address,
                "city": b.city,
                "contact_name": b.contact_name,
                "phone": b.phone,
                "is_active": b.is_active,
                "containers_count": len(b.containers),
            }
        )
    return results


@router.get(
    "/{id}",
    summary="Get business detail with smart containers status",
)
def get_business_detail(
    id: str = Path(..., description="UUID of the food establishment"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve detailed profile and container status for a specific business."""
    verify_business_access(id, current_user)

    business = db.query(Business).filter(Business.id == id).first()
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Business '{id}' not found",
        )

    containers_data = [
        {
            "id": str(c.id),
            "device_token": c.device_token,
            "capacity_liters": c.capacity_liters,
            "current_volume_liters": c.current_volume_liters,
            "current_fill_percentage": c.current_fill_percentage,
            "status": (
                c.status.value if hasattr(c.status, "value") else str(c.status)
            ),
            "last_telemetry_at": (
                c.last_telemetry_at.isoformat() if c.last_telemetry_at else None
            ),
        }
        for c in business.containers
    ]

    return {
        "id": str(business.id),
        "name": business.name,
        "business_type": (
            business.business_type.value
            if hasattr(business.business_type, "value")
            else str(business.business_type)
        ),
        "num_fryers": business.num_fryers,
        "avg_daily_customers": business.avg_daily_customers,
        "latitude": business.latitude,
        "longitude": business.longitude,
        "address": business.address,
        "city": business.city,
        "contact_name": business.contact_name,
        "phone": business.phone,
        "is_active": business.is_active,
        "containers": containers_data,
    }


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Onboard new gastronomy establishment (Admin only)",
)
def create_business(
    payload: BusinessCreatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> Dict[str, Any]:
    """Register a new food business into SICRA."""
    new_biz = Business(
        name=payload.name,
        business_type=payload.business_type,
        num_fryers=payload.num_fryers,
        avg_daily_customers=payload.avg_daily_customers,
        latitude=payload.latitude,
        longitude=payload.longitude,
        address=payload.address,
        city=payload.city,
        contact_name=payload.contact_name,
        phone=payload.phone,
        is_active=payload.is_active,
    )
    db.add(new_biz)
    db.commit()
    db.refresh(new_biz)

    return {
        "id": str(new_biz.id),
        "name": new_biz.name,
        "business_type": (
            new_biz.business_type.value
            if hasattr(new_biz.business_type, "value")
            else str(new_biz.business_type)
        ),
        "is_active": new_biz.is_active,
    }
