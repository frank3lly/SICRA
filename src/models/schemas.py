"""Pydantic V2 schemas and type specifications for SICRA."""

from datetime import date, datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from src.models.enums import (
    AlertType,
    BusinessType,
    ContainerStatus,
    RouteStatus,
    TelemetryFlag,
    UserRole,
)


class RouteStop(BaseModel):
    """Specification of an individual stop within an optimized collection route."""

    sequence: int = Field(..., ge=1, description="Order sequence in the route itinerary")
    business_id: str = Field(..., description="UUID identifier of the food establishment")
    business_name: str = Field(..., description="Establishment commercial name")
    latitude: float = Field(..., description="WGS 84 latitude coordinate")
    longitude: float = Field(..., description="WGS 84 longitude coordinate")
    estimated_liters: float = Field(..., ge=0.0, description="Estimated oil volume to retrieve")


# ==============================================================================
# Business Schemas
# ==============================================================================


class BusinessBase(BaseModel):
    """Base fields for business models."""

    name: str = Field(..., max_length=150)
    business_type: BusinessType
    num_fryers: int = Field(1, ge=1)
    avg_daily_customers: int = Field(100, ge=0)
    latitude: float
    longitude: float
    address: str = Field(..., max_length=255)
    city: str = Field("San Pedro de Macorís", max_length=100)
    contact_name: Optional[str] = Field(None, max_length=120)
    phone: Optional[str] = Field(None, max_length=30)
    is_active: bool = True


class BusinessCreate(BusinessBase):
    """Schema for creating a new business."""

    pass


class BusinessUpdate(BaseModel):
    """Schema for updating an existing business."""

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


class BusinessResponse(BusinessBase):
    """Schema for business responses."""

    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# Container Schemas
# ==============================================================================


class ContainerBase(BaseModel):
    """Base fields for container models."""

    business_id: str
    device_token: str = Field(..., max_length=64)
    capacity_liters: float = Field(..., gt=0.0)
    tare_weight_kg: float = Field(2.5, ge=0.0)
    oil_density_kg_l: float = Field(0.92, gt=0.0)
    status: ContainerStatus = ContainerStatus.ACTIVE
    current_volume_liters: float = Field(0.0, ge=0.0)
    current_fill_percentage: float = Field(0.0, ge=0.0, le=100.0)
    last_telemetry_at: Optional[datetime] = None


class ContainerCreate(BaseModel):
    """Schema for creating/provisioning a container."""

    business_id: str
    device_token: str = Field(..., max_length=64)
    capacity_liters: float = Field(..., gt=0.0)
    tare_weight_kg: float = Field(2.5, ge=0.0)
    oil_density_kg_l: float = Field(0.92, gt=0.0)
    status: ContainerStatus = ContainerStatus.ACTIVE


class ContainerUpdate(BaseModel):
    """Schema for updating container attributes."""

    capacity_liters: Optional[float] = Field(None, gt=0.0)
    tare_weight_kg: Optional[float] = Field(None, ge=0.0)
    oil_density_kg_l: Optional[float] = Field(None, gt=0.0)
    status: Optional[ContainerStatus] = None
    current_volume_liters: Optional[float] = Field(None, ge=0.0)
    current_fill_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    last_telemetry_at: Optional[datetime] = None


class ContainerResponse(ContainerBase):
    """Schema for container responses."""

    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# Telemetry Schemas
# ==============================================================================


class TelemetryBase(BaseModel):
    """Base fields for telemetry measurements."""

    container_id: str
    measurement_timestamp: datetime
    raw_weight_kg: float = Field(..., ge=0.0)
    calculated_liters: float = Field(..., ge=0.0)
    fill_percentage: float = Field(..., ge=0.0)
    battery_voltage_mv: Optional[int] = Field(None, ge=0)
    battery_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    is_synthetic: bool = True
    flag: TelemetryFlag = TelemetryFlag.NORMAL


class TelemetryCreate(TelemetryBase):
    """Schema for ingesting raw sensor telemetry."""

    pass


class TelemetryResponse(TelemetryBase):
    """Schema for telemetry query responses."""

    id: int
    received_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# Prediction Schemas
# ==============================================================================


class PredictionBase(BaseModel):
    """Base fields for ML predictions."""

    container_id: str
    calculation_timestamp: datetime
    target_date: date
    predicted_daily_liters: float = Field(..., ge=0.0)
    projected_hours_to_80_percent: Optional[float] = Field(None, ge=0.0)
    model_identifier: str = Field(..., max_length=64)
    is_synthetic: bool = True
    historical_mae: Optional[float] = Field(None, ge=0.0)


class PredictionCreate(PredictionBase):
    """Schema for logging predictive estimates."""

    pass


class PredictionResponse(PredictionBase):
    """Schema for prediction query responses."""

    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# Alert Schemas
# ==============================================================================


class AlertBase(BaseModel):
    """Base fields for system capacity/maintenance alerts."""

    container_id: str
    alert_type: AlertType
    triggered_percentage: float = Field(..., ge=0.0)
    is_resolved: bool = False
    resolved_at: Optional[datetime] = None


class AlertCreate(AlertBase):
    """Schema for generating a new alert."""

    pass


class AlertUpdate(BaseModel):
    """Schema for resolving or updating an alert."""

    is_resolved: Optional[bool] = None
    resolved_at: Optional[datetime] = None


class AlertResponse(AlertBase):
    """Schema for alert responses."""

    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# Collection Route Schemas
# ==============================================================================


class CollectionRouteBase(BaseModel):
    """Base fields for logistics collection routes."""

    scheduled_date: date
    status: RouteStatus = RouteStatus.SUGGESTED
    total_distance_km: float = Field(0.0, ge=0.0)
    total_estimated_volume_liters: float = Field(0.0, ge=0.0)
    stops_order_json: Any
    collector_user_id: Optional[str] = None
    completed_at: Optional[datetime] = None


class CollectionRouteCreate(CollectionRouteBase):
    """Schema for creating a planned collection route."""

    pass


class CollectionRouteUpdate(BaseModel):
    """Schema for updating a collection route itinerary or status."""

    status: Optional[RouteStatus] = None
    total_distance_km: Optional[float] = Field(None, ge=0.0)
    total_estimated_volume_liters: Optional[float] = Field(None, ge=0.0)
    stops_order_json: Optional[Any] = None
    collector_user_id: Optional[str] = None
    completed_at: Optional[datetime] = None


class CollectionRouteResponse(CollectionRouteBase):
    """Schema for route responses."""

    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# User & RBAC Schemas
# ==============================================================================


class UserBase(BaseModel):
    """Base fields for user authentication accounts."""

    email: str = Field(..., max_length=150, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    full_name: str = Field(..., max_length=150)
    role: UserRole = UserRole.BUSINESS_OWNER
    business_id: Optional[str] = None
    is_active: bool = True


class UserCreate(UserBase):
    """Schema for registering a user."""

    password: str = Field(..., min_length=8, description="Raw password to be hashed")


class UserUpdate(BaseModel):
    """Schema for modifying user account profiles."""

    email: Optional[str] = Field(None, max_length=150, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    full_name: Optional[str] = Field(None, max_length=150)
    role: Optional[UserRole] = None
    business_id: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8)


class UserResponse(UserBase):
    """Schema for user profile responses."""

    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
