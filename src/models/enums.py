"""Domain enumeration types for SICRA entities."""

import enum


class BusinessType(str, enum.Enum):
    """Categorical classification of food establishments producing waste oil."""

    FRITURA = "FRITURA"
    PICA_POLLO = "PICA_POLLO"
    CAFETERIA = "CAFETERIA"
    RESTAURANTE = "RESTAURANTE"


class ContainerStatus(str, enum.Enum):
    """Operational status of a smart waste oil collection container."""

    ACTIVE = "ACTIVE"
    MAINTENANCE = "MAINTENANCE"
    INACTIVE = "INACTIVE"


class TelemetryFlag(str, enum.Enum):
    """Classification tags for raw incoming telemetry sensor events."""

    NORMAL = "NORMAL"
    DRAIN_EVENT = "DRAIN_EVENT"
    OUTLIER_REJECTED = "OUTLIER_REJECTED"
    BATTERY_LOW = "BATTERY_LOW"


class AlertType(str, enum.Enum):
    """Operational warning and collection trigger classifications."""

    CAPACITY_80_PERCENT = "CAPACITY_80_PERCENT"
    CAPACITY_95_CRITICAL = "CAPACITY_95_CRITICAL"
    BATTERY_LOW = "BATTERY_LOW"
    COMMUNICATION_TIMEOUT = "COMMUNICATION_TIMEOUT"


class RouteStatus(str, enum.Enum):
    """Lifecycle stages of logistics dispatch routes."""

    SUGGESTED = "SUGGESTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class UserRole(str, enum.Enum):
    """Role-Based Access Control (RBAC) tiers."""

    ADMIN = "ADMIN"
    COLLECTOR = "COLLECTOR"
    BUSINESS_OWNER = "BUSINESS_OWNER"
