"""SQLAlchemy 2.0 ORM Entity models for SICRA."""

from datetime import date, datetime, timezone
from typing import Any, Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import AuditMixin, Base
from src.models.enums import (
    AlertType,
    BusinessType,
    ContainerStatus,
    RouteStatus,
    TelemetryFlag,
    UserRole,
)


class Business(AuditMixin, Base):
    """Represents food businesses generating used cooking oil (ACU)."""

    __tablename__ = "businesses"

    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    business_type: Mapped[BusinessType] = mapped_column(
        SQLEnum(BusinessType, native_enum=False, validate_strings=True),
        nullable=False,
        index=True,
    )
    num_fryers: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    avg_daily_customers: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(
        String(100), nullable=False, default="San Pedro de Macorís"
    )
    contact_name: Mapped[Optional[str]] = mapped_column(
        String(120), nullable=True
    )
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    # Relationships
    containers: Mapped[list["Container"]] = relationship(
        "Container",
        back_populates="business",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    users: Mapped[list["User"]] = relationship(
        "User", back_populates="business"
    )


class Container(AuditMixin, Base):
    """Represents smart HDPE containers installed at gastronomy businesses."""

    __tablename__ = "containers"

    business_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_token: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )
    capacity_liters: Mapped[float] = mapped_column(Float, nullable=False)
    tare_weight_kg: Mapped[float] = mapped_column(
        Float, nullable=False, default=2.5
    )
    oil_density_kg_l: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.92
    )
    status: Mapped[ContainerStatus] = mapped_column(
        SQLEnum(ContainerStatus, native_enum=False, validate_strings=True),
        nullable=False,
        default=ContainerStatus.ACTIVE,
    )
    current_volume_liters: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    current_fill_percentage: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    last_telemetry_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    business: Mapped["Business"] = relationship(
        "Business", back_populates="containers"
    )
    telemetries: Mapped[list["Telemetry"]] = relationship(
        "Telemetry",
        back_populates="container",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    predictions: Mapped[list["Prediction"]] = relationship(
        "Prediction",
        back_populates="container",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert",
        back_populates="container",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Telemetry(AuditMixin, Base):
    """Time-series record of IoT weight readings and container diagnostics."""

    __tablename__ = "telemetries"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    container_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("containers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    measurement_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    raw_weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    calculated_liters: Mapped[float] = mapped_column(Float, nullable=False)
    fill_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    battery_voltage_mv: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    battery_percentage: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    is_synthetic: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )
    flag: Mapped[TelemetryFlag] = mapped_column(
        SQLEnum(TelemetryFlag, native_enum=False, validate_strings=True),
        nullable=False,
        default=TelemetryFlag.NORMAL,
    )

    # Relationships
    container: Mapped["Container"] = relationship(
        "Container", back_populates="telemetries"
    )

    __table_args__ = (
        Index(
            "ix_telemetries_container_measurement_desc",
            "container_id",
            text("measurement_timestamp DESC"),
        ),
    )


class Prediction(AuditMixin, Base):
    """Daily predictive model volumetric projection logs."""

    __tablename__ = "predictions"

    container_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("containers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    calculation_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    target_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    predicted_daily_liters: Mapped[float] = mapped_column(
        Float, nullable=False
    )
    projected_hours_to_80_percent: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    model_identifier: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    is_synthetic: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    historical_mae: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )

    # Relationships
    container: Mapped["Container"] = relationship(
        "Container", back_populates="predictions"
    )


class Alert(AuditMixin, Base):
    """Operational notifications for threshold and collection alerts."""

    __tablename__ = "alerts"

    container_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("containers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alert_type: Mapped[AlertType] = mapped_column(
        SQLEnum(AlertType, native_enum=False, validate_strings=True),
        nullable=False,
        index=True,
    )
    triggered_percentage: Mapped[float] = mapped_column(
        Float, nullable=False
    )
    is_resolved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    container: Mapped["Container"] = relationship(
        "Container", back_populates="alerts"
    )


class CollectionRoute(AuditMixin, Base):
    """Optimized itinerary and dispatch sequence for oil collection trucks."""

    __tablename__ = "collection_routes"

    scheduled_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    status: Mapped[RouteStatus] = mapped_column(
        SQLEnum(RouteStatus, native_enum=False, validate_strings=True),
        nullable=False,
        default=RouteStatus.SUGGESTED,
        index=True,
    )
    total_distance_km: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    total_estimated_volume_liters: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    stops_order_json: Mapped[Any] = mapped_column(
        JSON,
        nullable=False,
    )
    collector_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    collector: Mapped[Optional["User"]] = relationship(
        "User", back_populates="collection_routes"
    )


class User(AuditMixin, Base):
    """User accounts and authentication profiles for RBAC."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        unique=True,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, native_enum=False, validate_strings=True),
        nullable=False,
        default=UserRole.BUSINESS_OWNER,
        index=True,
    )
    business_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("businesses.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # Relationships
    business: Mapped[Optional["Business"]] = relationship(
        "Business", back_populates="users"
    )
    collection_routes: Mapped[list["CollectionRoute"]] = relationship(
        "CollectionRoute", back_populates="collector"
    )


# Spanish Domain Aliases (mapping directly to the primary entities)
Negocio = Business
Recipiente = Container
Telemetria = Telemetry
Prediccion = Prediction
Alerta = Alert
RutaRecoleccion = CollectionRoute
Usuario = User
