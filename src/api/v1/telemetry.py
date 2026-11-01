"""IoT Telemetry REST API endpoints for SICRA."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.models.entities import Container, Telemetry, User
from src.schemas.telemetry import (
    TelemetryIngestPayload,
    TelemetryIngestResponse,
    TelemetryResponse,
)
from src.security.dependencies import get_current_user, verify_business_access
from src.services.telemetry_service import TelemetryService

router = APIRouter()


@router.post(
    "/ingest",
    response_model=TelemetryIngestResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest single or batch IoT telemetry readings",
)
def ingest_telemetry(
    payload: TelemetryIngestPayload,
    x_device_token: Optional[str] = Header(None, alias="X-Device-Token"),
    db: Session = Depends(get_db),
):
    """Ingest IoT load cell sensor transmissions.

    Authenticates hardware devices via `X-Device-Token` header or `payload.device_token`.
    Supports single real-time packets or multi-reading arrays buffered during network disconnects.
    """
    token = x_device_token or payload.device_token
    if not token or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing device authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    container = TelemetryService.authenticate_device(token, db)
    return TelemetryService.process_ingest_payload(container, payload, db)


@router.get(
    "/container/{container_id}",
    response_model=List[TelemetryResponse],
    summary="Retrieve historical telemetry series for a container",
)
def get_container_telemetry(
    container_id: str,
    limit: int = Query(100, ge=1, le=1000, description="Max records to retrieve"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve historical time-series telemetry records for a container.

    Enforces data isolation: Business owners may only inspect containers belonging to their business.
    """
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container not found",
        )

    verify_business_access(container.business_id, current_user)

    telemetries = (
        db.query(Telemetry)
        .filter(Telemetry.container_id == container.id)
        .order_by(Telemetry.measurement_timestamp.desc())
        .limit(limit)
        .all()
    )

    return [
        TelemetryResponse(
            id=t.id,
            container_id=str(t.container_id),
            measurement_timestamp=t.measurement_timestamp,
            raw_weight_kg=t.raw_weight_kg,
            calculated_liters=t.calculated_liters,
            fill_percentage=t.fill_percentage,
            battery_voltage_mv=t.battery_voltage_mv,
            battery_percentage=t.battery_percentage,
            is_synthetic=t.is_synthetic,
            flag=(
                t.flag.value if hasattr(t.flag, "value") else str(t.flag)
            ),
        )
        for t in telemetries
    ]
