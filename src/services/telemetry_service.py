"""IoT Telemetry processing service, physical calibrations, and drain event detection."""

from datetime import datetime, timezone
import logging
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.models.entities import Alert, Container, Telemetry
from src.models.enums import AlertType, ContainerStatus, TelemetryFlag
from src.schemas.telemetry import (
    TelemetryIngestPayload,
    TelemetryIngestResponse,
    TelemetryReadingItem,
)

logger = logging.getLogger("sicra.services.telemetry")


def normalize_utc(dt: datetime) -> datetime:
    """Normalize datetime to UTC without tzinfo for consistent DB indexing and comparison."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


class TelemetryService:
    """Domain service managing IoT telemetry validation, physical conversion, and drain detection."""

    @staticmethod
    def authenticate_device(token: Optional[str], db: Session) -> Container:
        """Authenticate transmission credentials against active containers.

        Raises:
            HTTPException: 401 if token is absent, unknown, or container inactive.
        """
        if not token or not token.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing device authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        container = (
            db.query(Container)
            .filter(Container.device_token == token.strip())
            .first()
        )

        if not container:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid device authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if container.status != ContainerStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Container is decommissioned or inactive (status: {container.status.value})",
            )

        return container

    @staticmethod
    def compute_volume_liters(raw_weight_kg: float, container: Container) -> float:
        """Calculate calibrated fluid volume in liters based on tare weight and oil density."""
        net_weight = raw_weight_kg - container.tare_weight_kg
        return max(0.0, net_weight / container.oil_density_kg_l)

    @staticmethod
    def compute_fill_percentage(liters: float, container: Container) -> float:
        """Calculate volumetric fill percentage bounded to [0.0, 100.0]."""
        if container.capacity_liters <= 0:
            return 0.0
        return min(100.0, (liters / container.capacity_liters) * 100.0)

    @staticmethod
    def compute_battery_percentage(battery_mv: Optional[int]) -> Optional[float]:
        """Interpolate linear battery state between 3400 mV (0%) and 4200 mV (100%)."""
        if battery_mv is None:
            return None
        pct = (battery_mv - 3400) / (4200 - 3400) * 100.0
        return min(100.0, max(0.0, pct))

    @staticmethod
    def is_drain_event(
        current_weight: float,
        previous_weight: float,
        container: Container,
    ) -> bool:
        """Determine if a weight delta represents an emptying/drain event.

        Condition: ΔWeight < -0.35 * (capacity_liters * density)
        """
        delta_w = current_weight - previous_weight
        threshold = -0.35 * (container.capacity_liters * container.oil_density_kg_l)
        return delta_w < threshold

    @classmethod
    def process_ingest_payload(
        cls,
        container: Container,
        payload: TelemetryIngestPayload,
        db: Session,
    ) -> TelemetryIngestResponse:
        """Process incoming telemetry readings with deduplication, conversions, and drain detection.

        Satisfies Requirement R-09: Supports batch arrays and offline resilience.
        """
        total_incoming = len(payload.readings)
        if total_incoming == 0:
            return TelemetryIngestResponse(
                status="success",
                container_id=str(container.id),
                accepted_count=0,
                duplicate_count=0,
                current_volume_liters=container.current_volume_liters,
                current_fill_percentage=container.current_fill_percentage,
            )

        # 1. Sort readings chronologically
        sorted_readings: List[TelemetryReadingItem] = sorted(
            payload.readings, key=lambda item: item.timestamp
        )

        # 2. In-payload deduplication (keep first chronological occurrence per timestamp)
        seen_timestamps = set()
        unique_batch_readings: List[TelemetryReadingItem] = []
        for reading in sorted_readings:
            norm_ts = normalize_utc(reading.timestamp)
            if norm_ts not in seen_timestamps:
                seen_timestamps.add(norm_ts)
                unique_batch_readings.append(reading)

        # 3. Database deduplication against existing records for this container
        timestamps_to_check = [r.timestamp for r in unique_batch_readings]
        existing_rows = (
            db.query(Telemetry.measurement_timestamp)
            .filter(
                Telemetry.container_id == container.id,
                Telemetry.measurement_timestamp.in_(timestamps_to_check),
            )
            .all()
        )
        existing_db_timestamps = {
            normalize_utc(row[0]) for row in existing_rows
        }

        fresh_readings = [
            r
            for r in unique_batch_readings
            if normalize_utc(r.timestamp) not in existing_db_timestamps
        ]

        duplicate_count = total_incoming - len(fresh_readings)

        # If all readings are duplicates, return early with current container state
        if not fresh_readings:
            return TelemetryIngestResponse(
                status="success",
                container_id=str(container.id),
                accepted_count=0,
                duplicate_count=duplicate_count,
                current_volume_liters=container.current_volume_liters,
                current_fill_percentage=container.current_fill_percentage,
                drain_events_detected=0,
                alerts_triggered=0,
                alerts_resolved=0,
            )

        # 4. Fetch the latest prior telemetry to initialize delta weight comparison
        first_fresh_ts = fresh_readings[0].timestamp
        latest_prior = (
            db.query(Telemetry)
            .filter(
                Telemetry.container_id == container.id,
                Telemetry.measurement_timestamp < first_fresh_ts,
            )
            .order_by(Telemetry.measurement_timestamp.desc())
            .first()
        )
        prev_weight: Optional[float] = (
            latest_prior.raw_weight_kg if latest_prior else None
        )

        telemetry_records: List[Telemetry] = []
        drain_events_detected = 0
        alerts_triggered = 0
        alerts_resolved = 0

        # 5. Process each fresh measurement
        for reading in fresh_readings:
            liters = cls.compute_volume_liters(reading.raw_weight_kg, container)
            fill_pct = cls.compute_fill_percentage(liters, container)
            batt_pct = cls.compute_battery_percentage(reading.battery_mv)

            flag = TelemetryFlag.NORMAL

            # Drain event evaluation
            if prev_weight is not None and cls.is_drain_event(
                reading.raw_weight_kg, prev_weight, container
            ):
                flag = TelemetryFlag.DRAIN_EVENT
                drain_events_detected += 1

                # Auto-resolve all open alerts for this container
                unresolved_alerts = (
                    db.query(Alert)
                    .filter(
                        Alert.container_id == container.id,
                        Alert.is_resolved == False,
                    )
                    .all()
                )
                now_utc = datetime.now(timezone.utc)
                for alert in unresolved_alerts:
                    alert.is_resolved = True
                    alert.resolved_at = now_utc
                    alerts_resolved += 1

                logger.info(
                    f"Drain event detected for container {container.id}: "
                    f"weight dropped from {prev_weight:.2f} kg to {reading.raw_weight_kg:.2f} kg. "
                    f"Resolved {len(unresolved_alerts)} active alerts."
                )

            # Trigger 80% or 95% alerts if threshold reached and not a drain event
            elif fill_pct >= 80.0:
                alert_type = (
                    AlertType.CAPACITY_95_CRITICAL
                    if fill_pct >= 95.0
                    else AlertType.CAPACITY_80_PERCENT
                )
                existing_open_alert = (
                    db.query(Alert)
                    .filter(
                        Alert.container_id == container.id,
                        Alert.alert_type == alert_type,
                        Alert.is_resolved == False,
                    )
                    .first()
                )
                if not existing_open_alert:
                    new_alert = Alert(
                        container_id=container.id,
                        alert_type=alert_type,
                        triggered_percentage=round(fill_pct, 2),
                        is_resolved=False,
                    )
                    db.add(new_alert)
                    alerts_triggered += 1
                    logger.info(
                        f"Triggered {alert_type.value} alert for container {container.id} "
                        f"at {fill_pct:.1f}% capacity."
                    )

            # Battery low alert (under 15% / ~3520 mV)
            if batt_pct is not None and batt_pct <= 15.0:
                existing_battery_alert = (
                    db.query(Alert)
                    .filter(
                        Alert.container_id == container.id,
                        Alert.alert_type == AlertType.BATTERY_LOW,
                        Alert.is_resolved == False,
                    )
                    .first()
                )
                if not existing_battery_alert:
                    battery_alert = Alert(
                        container_id=container.id,
                        alert_type=AlertType.BATTERY_LOW,
                        triggered_percentage=round(batt_pct, 2),
                        is_resolved=False,
                    )
                    db.add(battery_alert)
                    alerts_triggered += 1

            record = Telemetry(
                container_id=container.id,
                measurement_timestamp=reading.timestamp,
                raw_weight_kg=reading.raw_weight_kg,
                calculated_liters=round(liters, 2),
                fill_percentage=round(fill_pct, 2),
                battery_voltage_mv=reading.battery_mv,
                battery_percentage=(
                    round(batt_pct, 1) if batt_pct is not None else None
                ),
                is_synthetic=reading.is_synthetic,
                flag=flag,
            )
            telemetry_records.append(record)
            prev_weight = reading.raw_weight_kg

        # 6. Bulk persist telemetry records
        db.add_all(telemetry_records)

        # 7. Update container current state with the latest chronological reading
        chronological_latest = max(
            telemetry_records, key=lambda t: t.measurement_timestamp
        )

        should_update_container = (
            container.last_telemetry_at is None
            or normalize_utc(chronological_latest.measurement_timestamp)
            >= normalize_utc(container.last_telemetry_at)
        )

        if should_update_container:
            container.current_volume_liters = chronological_latest.calculated_liters
            container.current_fill_percentage = chronological_latest.fill_percentage
            container.last_telemetry_at = chronological_latest.measurement_timestamp

        db.commit()

        return TelemetryIngestResponse(
            status="success",
            container_id=str(container.id),
            accepted_count=len(telemetry_records),
            duplicate_count=duplicate_count,
            current_volume_liters=container.current_volume_liters,
            current_fill_percentage=container.current_fill_percentage,
            drain_events_detected=drain_events_detected,
            alerts_triggered=alerts_triggered,
            alerts_resolved=alerts_resolved,
        )
