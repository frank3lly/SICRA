"""Business entity management and gastronomy establishment REST API endpoints."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
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
    search: Optional[str] = Query(None, description="Filter by business name or address"),
    limit: Optional[int] = Query(None, ge=1, le=500, description="Max establishments to return"),
) -> List[Dict[str, Any]]:
    """List establishments according to RBAC scope with optional search and limit."""
    user_role_val = (
        current_user.role.value
        if hasattr(current_user.role, "value")
        else str(current_user.role)
    )

    query = db.query(Business)
    if user_role_val == UserRole.BUSINESS_OWNER.value:
        query = query.filter(Business.id == current_user.business_id)

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(Business.name.ilike(term) | Business.address.ilike(term))

    query = query.order_by(Business.name.asc())
    if limit is not None:
        query = query.limit(limit)

    businesses = query.all()
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


class BusinessUpdatePayload(BaseModel):
    """Payload for modifying an existing business establishment (Admin only)."""

    name: Optional[str] = Field(None, max_length=150)
    business_type: Optional[BusinessType] = None
    num_fryers: Optional[int] = Field(None, ge=1)
    avg_daily_customers: Optional[int] = Field(None, ge=0)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    contact_name: Optional[str] = Field(None, max_length=120)
    phone: Optional[str] = Field(None, max_length=30)
    is_active: Optional[bool] = None


@router.put(
    "/{id}",
    summary="Update business establishment (Admin only)",
)
def update_business(
    id: str,
    payload: BusinessUpdatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> Dict[str, Any]:
    """Modify parameters, contact info, or operational status of a business establishment."""
    business = db.query(Business).filter(Business.id == id).first()
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comercio '{id}' no encontrado.",
        )

    if payload.name is not None:
        business.name = payload.name.strip()
    if payload.business_type is not None:
        business.business_type = payload.business_type
    if payload.num_fryers is not None:
        business.num_fryers = payload.num_fryers
    if payload.avg_daily_customers is not None:
        business.avg_daily_customers = payload.avg_daily_customers
    if payload.latitude is not None:
        business.latitude = payload.latitude
    if payload.longitude is not None:
        business.longitude = payload.longitude
    if payload.address is not None:
        business.address = payload.address.strip()
    if payload.city is not None:
        business.city = payload.city.strip()
    if payload.contact_name is not None:
        business.contact_name = payload.contact_name.strip() if payload.contact_name else None
    if payload.phone is not None:
        business.phone = payload.phone.strip() if payload.phone else None
    if payload.is_active is not None:
        business.is_active = payload.is_active

    db.commit()
    db.refresh(business)

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
        "containers_count": len(business.containers),
    }


@router.delete(
    "/{id}",
    summary="Delete business establishment and cascade dependencies (Admin only)",
)
def delete_business(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> Dict[str, Any]:
    """Delete a business establishment, its containers, and unbind associated user accounts."""
    business = db.query(Business).filter(Business.id == id).first()
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comercio '{id}' no encontrado.",
        )

    # 1. Unbind any users associated with this business
    users_bound = db.query(User).filter(User.business_id == id).all()
    for u in users_bound:
        u.business_id = None

    # 2. Delete business (cascading containers, telemetries, predictions, alerts)
    biz_name = business.name
    db.delete(business)
    db.commit()

    return {
        "status": "deleted",
        "id": id,
        "message": f"Comercio '{biz_name}' y sus recursos asociados han sido eliminados.",
    }
