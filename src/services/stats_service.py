"""Environmental Impact and Legal Compliance Statistics Service (Ley 225-20 / Ley 64-00)."""

import os
from typing import Any, Dict
from sqlalchemy.orm import Session

from src.models.entities import CollectionRoute, Container, Telemetry
from src.models.enums import ContainerStatus, TelemetryFlag


class StatsService:
    """Computes aggregate environmental metrics and statutory waste diversion indicators."""

    @staticmethod
    def get_environmental_stats(db: Session) -> Dict[str, Any]:
        """Aggregate total recycled waste oil and potable water preserved.

        Rules according to Ley 225-20 (Residuos Sólidos) and Ley 64-00 (Recursos Hídricos):
        1. 1 Liter of waste cooking oil contaminates 1,000 Liters of potable water.
        2. Carbon offsetting: 2.85 kg CO2e avoided per liter of recycled oil diverted to biodiesel.
        """
        # 1. Calculate total oil diverted from confirmed drain events
        drain_telemetries = (
            db.query(Telemetry)
            .filter(Telemetry.flag == TelemetryFlag.DRAIN_EVENT)
            .all()
        )

        drain_diverted_liters = 0.0
        for dt in drain_telemetries:
            prev_reading = (
                db.query(Telemetry)
                .filter(
                    Telemetry.container_id == dt.container_id,
                    Telemetry.measurement_timestamp < dt.measurement_timestamp,
                )
                .order_by(Telemetry.measurement_timestamp.desc())
                .first()
            )
            if prev_reading and prev_reading.calculated_liters > dt.calculated_liters:
                drain_diverted_liters += prev_reading.calculated_liters - dt.calculated_liters
            else:
                drain_diverted_liters += max(0.0, dt.calculated_liters)

        # 2. Count confirmed route pickups
        routes = db.query(CollectionRoute).all()
        confirmed_pickups_count = 0
        route_diverted_liters = 0.0

        for r in routes:
            if isinstance(r.stops_order_json, list):
                for s in r.stops_order_json:
                    if s.get("visited") and not s.get("is_depot"):
                        confirmed_pickups_count += 1
                        route_diverted_liters += float(s.get("estimated_liters", 0.0))

        # Combined collections count
        total_collections = len(drain_telemetries) + confirmed_pickups_count

        # Total oil diverted (drain events represent verified tare drops; if none yet, route volume is included)
        base_historical_liters = float(os.getenv("BASE_HISTORICAL_OIL_LITERS", "0.0"))
        total_diverted = round(base_historical_liters + drain_diverted_liters + (route_diverted_liters if len(drain_telemetries) == 0 else 0.0), 2)

        # Environmental conversions
        water_preserved = round(total_diverted * 1000.0, 1)
        co2_avoided = round(total_diverted * 2.85, 2)

        active_containers_count = (
            db.query(Container)
            .filter(Container.status == ContainerStatus.ACTIVE)
            .count()
        )

        return {
            "total_oil_diverted_liters": total_diverted,
            "water_preserved_liters": water_preserved,
            "co2_avoided_kg": co2_avoided,
            "total_collections_count": total_collections,
            "active_containers_count": active_containers_count,
            "compliance_framework": "Trazabilidad y Recoleccion Certificada",
        }
