"""High-throughput probabilistic Monte Carlo simulation engine for IoT telemetry."""

from datetime import datetime, timedelta, timezone
import os
from typing import Any, Dict, Generator, Iterable, List, Optional
import numpy as np
import pandas as pd
from sqlalchemy import insert
from sqlalchemy.orm import Session

from src.database.session import SessionLocal, get_session_factory
from src.models.entities import Business, Container, Telemetry
from src.models.enums import BusinessType, TelemetryFlag

# Dominican Day of Week Multipliers (M_day)
# Mon-Wed: 0.75 - 0.85 (Baseline)
# Thu: 1.00 (Pre-weekend lift)
# Fri: 1.65 (Viernes social)
# Sat: 2.10 (Peak fast food and chimi)
# Sun: 1.80 (Family dining rush)
DAY_OF_WEEK_MULTIPLIERS = {
    0: 0.78,  # Monday
    1: 0.80,  # Tuesday
    2: 0.82,  # Wednesday
    3: 1.00,  # Thursday
    4: 1.65,  # Friday
    5: 2.10,  # Saturday
    6: 1.80,  # Sunday
}

# Average daily oil disposal coefficient (alpha_type in Liters / fryer / day)
OIL_RATE_BY_BUSINESS_TYPE = {
    BusinessType.PICA_POLLO: 4.5,
    BusinessType.FRITURA: 2.75,
    BusinessType.CAFETERIA: 1.15,
    BusinessType.RESTAURANTE: 1.60,
}

# 24-hour kitchen frying activity profile (normalized)
HOURLY_ACTIVITY_PROFILE = np.array([
    0.005, 0.005, 0.005, 0.005, 0.005, 0.005, 0.005, 0.010,  # 00:00 - 08:00 (Closed)
    0.040, 0.050, 0.060, 0.090, 0.100, 0.100, 0.070, 0.040,  # 08:00 - 16:00 (Prep & Lunch)
    0.040, 0.050, 0.080, 0.090, 0.090, 0.070, 0.030, 0.010,  # 16:00 - 24:00 (Dinner Peak)
])
HOURLY_ACTIVITY_PROFILE = HOURLY_ACTIVITY_PROFILE / HOURLY_ACTIVITY_PROFILE.sum()


def chunk_iterator(data: List[Any], chunk_size: int = 5000) -> Generator[List[Any], None, None]:
    """Yield successive chunks of specified size from a list."""
    for i in range(0, len(data), chunk_size):
        yield data[i : i + chunk_size]


class MonteCarloSimulator:
    """Probabilistic Monte Carlo time-series telemetry generator for smart oil containers."""

    def __init__(self, db_session: Optional[Session] = None, seed: int = 42) -> None:
        """Initialize simulator with deterministic seed and optional database session."""
        self.db_session = db_session
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    def _get_interval_weights(self, interval_hours: int) -> np.ndarray:
        """Compute relative intraday pouring weights for the chosen interval frequency."""
        n_intervals = 24 // interval_hours
        weights = []
        for i in range(n_intervals):
            h_start = i * interval_hours
            h_end = min(24, h_start + interval_hours)
            weights.append(HOURLY_ACTIVITY_PROFILE[h_start:h_end].sum())
        w = np.array(weights)
        return w / w.sum()

    def simulate_business_timeline(
        self,
        container: Container,
        start_date: datetime,
        days: int = 90,
        interval_hours: int = 2,
    ) -> List[Dict[str, Any]]:
        """Simulate realistic telemetry time series for a single container over a period of days."""
        # Extract business parameters
        business = container.business
        if business is not None:
            biz_type = business.business_type
            if isinstance(biz_type, str):
                biz_type = BusinessType(biz_type)
            num_fryers = business.num_fryers or 1
            lambda_b = float(business.avg_daily_customers or 100)
        else:
            biz_type = BusinessType.FRITURA
            num_fryers = 2
            lambda_b = 150.0

        alpha = OIL_RATE_BY_BUSINESS_TYPE.get(biz_type, 2.5)
        capacity = float(container.capacity_liters)
        tare_weight = float(container.tare_weight_kg)
        density = float(container.oil_density_kg_l or 0.92)

        # Container initial physical state
        current_volume = float(self.rng.uniform(0.5, 3.0))
        # Battery state: starts between 3900 and 4180 mV
        v_battery = float(self.rng.uniform(3900.0, 4180.0))
        # Battery hourly discharge rate: ~800 mV drop over 35 days (840h) ~ 0.95 mV/h
        battery_drain_per_hour = 0.95

        intervals_per_day = 24 // interval_hours
        interval_weights = self._get_interval_weights(interval_hours)

        records: List[Dict[str, Any]] = []
        scheduled_pickup_at: Optional[datetime] = None

        # Base starting timestamp normalized to start of day UTC
        base_time = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

        for day_idx in range(days):
            current_day = base_time + timedelta(days=day_idx)
            dow = current_day.weekday()
            m_day = DAY_OF_WEEK_MULTIPLIERS.get(dow, 1.0)

            # 1. Customer footfall (Poisson distribution)
            customers = float(self.rng.poisson(max(1.0, lambda_b * m_day)))

            # 2. Daily oil rate (Gamma distribution)
            # mu = alpha * fryers * (customers / lambda_b)
            mu_rate = alpha * num_fryers * (customers / lambda_b)
            k_shape = 2.2
            theta_scale = max(0.01, mu_rate / k_shape)
            daily_oil = float(self.rng.gamma(k_shape, theta_scale))

            for int_idx in range(intervals_per_day):
                timestamp = current_day + timedelta(hours=int_idx * interval_hours)
                incremental_volume = daily_oil * interval_weights[int_idx]

                # Check if a scheduled pickup occurs at or before this interval
                is_drain_event = False
                if scheduled_pickup_at is not None and timestamp >= scheduled_pickup_at:
                    # Emptying / collection occurs
                    residual = float(self.rng.uniform(0.2, 0.6))
                    current_volume = residual
                    scheduled_pickup_at = None
                    is_drain_event = True
                    # Maintenance / collection visit also swaps/recharges battery
                    v_battery = float(self.rng.uniform(4150.0, 4200.0))
                else:
                    current_volume = min(capacity, current_volume + incremental_volume)

                # Fill percentage calculation
                fill_percentage_net = (current_volume / capacity) * 100.0

                # Check if 80% threshold reached and pickup not yet scheduled
                if fill_percentage_net >= 80.0 and scheduled_pickup_at is None:
                    pickup_delay_hours = float(self.rng.uniform(12.0, 36.0))
                    scheduled_pickup_at = timestamp + timedelta(hours=pickup_delay_hours)

                # Battery discharge model
                discharge = battery_drain_per_hour * interval_hours * float(self.rng.uniform(0.85, 1.15))
                v_battery = max(3350.0, v_battery - discharge)

                # Recharge / maintenance if battery hits critical cutoff
                is_battery_low = False
                if v_battery <= 3400.0:
                    is_battery_low = True
                    # Battery replacement occurs within next cycle
                    v_battery = float(self.rng.uniform(4160.0, 4200.0))

                battery_pct = max(0.0, min(100.0, ((v_battery - 3400.0) / (4200.0 - 3400.0)) * 100.0))

                # Sensor weight reading with Gaussian noise
                noise = float(self.rng.normal(0.0, 0.03))
                raw_weight = tare_weight + (current_volume * density) + noise
                # Physical law guard: scale cannot read below tare weight (minus tiny vibration noise)
                raw_weight = max(tare_weight - 0.05, round(raw_weight, 3))

                calculated_liters = max(0.0, round((raw_weight - tare_weight) / density, 3))
                fill_percentage = min(100.0, max(0.0, round((calculated_liters / capacity) * 100.0, 2)))

                # Determine telemetry flag
                if is_drain_event:
                    flag = TelemetryFlag.DRAIN_EVENT
                elif is_battery_low:
                    flag = TelemetryFlag.BATTERY_LOW
                else:
                    flag = TelemetryFlag.NORMAL

                # Received timestamp with slight network delay (1-5s)
                net_delay = float(self.rng.uniform(1.0, 5.0))
                received_at = timestamp + timedelta(seconds=net_delay)

                records.append({
                    "container_id": container.id,
                    "measurement_timestamp": timestamp,
                    "received_at": received_at,
                    "raw_weight_kg": raw_weight,
                    "calculated_liters": calculated_liters,
                    "fill_percentage": fill_percentage,
                    "battery_voltage_mv": int(round(v_battery)),
                    "battery_percentage": round(battery_pct, 1),
                    "is_synthetic": True,
                    "flag": flag.value,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                })

        return records

    def generate_synthetic_telemetry(
        self,
        days: int = 90,
        interval_hours: int = 2,
        start_date: Optional[datetime] = None,
        to_db: bool = True,
        output_csv: Optional[str] = None,
        chunk_size: int = 5000,
        containers: Optional[List[Container]] = None,
    ) -> List[Dict[str, Any]]:
        """Generate complete synthetic telemetry dataset across containers with bulk persistence."""
        session = self.db_session
        should_close_session = False

        if session is None:
            session = SessionLocal()
            should_close_session = True

        try:
            # Resolve target containers
            target_containers: List[Container] = []
            if containers is not None:
                target_containers = containers
            elif session is not None:
                target_containers = session.query(Container).join(Business).all()

            if not target_containers and session is not None:
                # If no containers exist yet, seed initial Dominican businesses
                from src.database.seed import seed_database
                seed_database(quiet=True)
                target_containers = session.query(Container).join(Business).all()

            if start_date is None:
                start_date = datetime.now(timezone.utc) - timedelta(days=days)

            all_records: List[Dict[str, Any]] = []

            for container in target_containers:
                container_records = self.simulate_business_timeline(
                    container=container,
                    start_date=start_date,
                    days=days,
                    interval_hours=interval_hours,
                )
                all_records.extend(container_records)

                # Update container denormalized cache if persisting
                if to_db and session is not None and container_records:
                    last_record = container_records[-1]
                    container.current_volume_liters = last_record["calculated_liters"]
                    container.current_fill_percentage = last_record["fill_percentage"]
                    container.last_telemetry_at = last_record["measurement_timestamp"]

            # Sort chronological by measurement_timestamp
            all_records.sort(key=lambda r: r["measurement_timestamp"])

            # Bulk persistence in chunks
            if to_db and session is not None and all_records:
                for chunk in chunk_iterator(all_records, chunk_size=chunk_size):
                    session.execute(insert(Telemetry), chunk)
                session.commit()

            # Optional CSV export
            if output_csv:
                csv_dir = os.path.dirname(output_csv)
                if csv_dir:
                    os.makedirs(csv_dir, exist_ok=True)
                df = pd.DataFrame(all_records)
                df.to_csv(output_csv, index=False)

            return all_records

        except Exception:
            if session is not None and to_db:
                session.rollback()
            raise
        finally:
            if should_close_session and session is not None:
                session.close()
