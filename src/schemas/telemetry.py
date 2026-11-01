"""Pydantic V2 schemas for IoT telemetry intake, batch processing, and queries."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TelemetryReadingItem(BaseModel):
    """Individual measurement reading recorded by the hardware load cell."""

    timestamp: datetime = Field(
        ..., description="UTC measurement timestamp recorded on device RTC"
    )
    raw_weight_kg: float = Field(
        ..., ge=0.0, description="Gross load cell weight measurement"
    )
    battery_mv: Optional[int] = Field(
        None, ge=2500, le=5000, description="Battery millivolts"
    )
    is_synthetic: bool = Field(
        False,
        description="Explicit discriminator between hardware and synthetic tests",
    )


class TelemetryIngestPayload(BaseModel):
    """Payload contract for single readings or offline batch arrays."""

    device_token: Optional[str] = Field(
        None, description="Container token if not provided in request headers"
    )
    readings: List[TelemetryReadingItem] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Chronological or accumulated array of measurements",
    )


class TelemetryIngestResponse(BaseModel):
    """Operational summary of batch ingestion transaction."""

    status: str = "success"
    container_id: str
    accepted_count: int
    duplicate_count: int
    current_volume_liters: float
    current_fill_percentage: float
    drain_events_detected: int = 0
    alerts_triggered: int = 0
    alerts_resolved: int = 0


class TelemetryResponse(BaseModel):
    """Public representation of a persisted telemetry record."""

    id: int
    container_id: str
    measurement_timestamp: datetime
    raw_weight_kg: float
    calculated_liters: float
    fill_percentage: float
    battery_voltage_mv: Optional[int] = None
    battery_percentage: Optional[float] = None
    is_synthetic: bool
    flag: str

    model_config = ConfigDict(from_attributes=True)
