"""Pipeline aggregating high-frequency sensor telemetry into daily tabular ML features."""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from src.database.session import SessionLocal
from src.models.entities import Business, Container, Telemetry
from src.models.enums import TelemetryFlag


class DailyFeatureAggregator:
    """Transforms raw telemetry time-series into daily feature representations."""

    def __init__(self, db_session: Optional[Session] = None) -> None:
        """Initialize aggregator with optional database session."""
        self.db_session = db_session

    def load_telemetry_from_db(
        self,
        session: Optional[Session] = None,
        container_ids: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """Load telemetry joined with container and business metadata from the database."""
        sess = session or self.db_session or SessionLocal()
        should_close = sess != self.db_session and session is None

        try:
            query = sess.query(
                Telemetry.container_id,
                Telemetry.measurement_timestamp,
                Telemetry.calculated_liters,
                Telemetry.flag,
                Telemetry.is_synthetic,
                Container.business_id,
                Business.name.label("business_name"),
                Business.business_type,
                Business.num_fryers,
                Business.avg_daily_customers,
                Business.city,
            ).join(Container, Telemetry.container_id == Container.id).join(Business, Container.business_id == Business.id)

            if container_ids:
                query = query.filter(Telemetry.container_id.isin(container_ids))

            query = query.order_by(Telemetry.container_id, Telemetry.measurement_timestamp)

            rows = query.all()
            if not rows:
                return pd.DataFrame()

            df = pd.DataFrame(rows, columns=[
                "container_id",
                "measurement_timestamp",
                "calculated_liters",
                "flag",
                "is_synthetic",
                "business_id",
                "business_name",
                "business_type",
                "num_fryers",
                "avg_daily_customers",
                "city",
            ])
            return df

        finally:
            if should_close:
                sess.close()

    def aggregate_daily_features(
        self,
        telemetry_source: Optional[Union[pd.DataFrame, List[Dict[str, Any]]]] = None,
        session: Optional[Session] = None,
    ) -> pd.DataFrame:
        """Resample raw telemetry readings into daily aggregated feature records."""
        if telemetry_source is None:
            df = self.load_telemetry_from_db(session=session)
        elif isinstance(telemetry_source, list):
            df = pd.DataFrame(telemetry_source)
        else:
            df = telemetry_source.copy()

        if df.empty:
            return pd.DataFrame(columns=[
                "date",
                "container_id",
                "business_id",
                "business_name",
                "business_type",
                "num_fryers",
                "avg_daily_customers",
                "day_of_week",
                "is_weekend",
                "lag_7d_liters",
                "daily_liters",
                "is_synthetic",
            ])

        # Ensure timestamp datetime conversion and sort
        df["measurement_timestamp"] = pd.to_datetime(df["measurement_timestamp"])
        df = df.sort_values(["container_id", "measurement_timestamp"]).reset_index(drop=True)
        df["date"] = df["measurement_timestamp"].dt.date

        # Convert business_type enum to string if applicable
        if "business_type" in df.columns:
            df["business_type"] = df["business_type"].apply(
                lambda bt: bt.value if hasattr(bt, "value") else str(bt)
            )

        # 1. Calculate positive volume increments (ignoring emptying drops)
        df["prev_liters"] = df.groupby("container_id")["calculated_liters"].shift(1)
        flag_val = TelemetryFlag.DRAIN_EVENT.value
        df["flag_str"] = df["flag"].apply(lambda f: f.value if hasattr(f, "value") else str(f))

        df["delta_vol"] = np.where(
            (df["flag_str"] != flag_val) & (df["calculated_liters"] >= df["prev_liters"]),
            df["calculated_liters"] - df["prev_liters"],
            0.0,
        )
        df["delta_vol"] = df["delta_vol"].fillna(0.0)

        # 2. Resample / aggregate to daily per container
        group_cols = [
            "container_id",
            "date",
            "business_id",
            "business_name",
            "business_type",
            "num_fryers",
            "avg_daily_customers",
        ]
        # Include optional columns present in df
        present_group_cols = [c for c in group_cols if c in df.columns]

        daily_agg = df.groupby(present_group_cols, as_index=False).agg(
            daily_liters=("delta_vol", "sum"),
            is_synthetic=("is_synthetic", "all"),
        )
        daily_agg["daily_liters"] = daily_agg["daily_liters"].round(3)

        # 3. Add temporal features
        date_series = pd.to_datetime(daily_agg["date"])
        daily_agg["day_of_week"] = date_series.dt.day_of_week  # 0=Mon, ..., 6=Sun
        # In Dominican context: Fri(4), Sat(5), Sun(6) are the weekend peak
        daily_agg["is_weekend"] = daily_agg["day_of_week"].isin([4, 5, 6])

        # 4. Compute 7-day seasonal lag feature (lag_7d_liters)
        daily_agg["lag_date"] = (date_series - pd.Timedelta(days=7)).dt.date
        lag_reference = daily_agg[["container_id", "date", "daily_liters"]].rename(
            columns={"date": "lag_date", "daily_liters": "lag_7d_liters"}
        )
        daily_features = pd.merge(
            daily_agg,
            lag_reference,
            on=["container_id", "lag_date"],
            how="left",
        ).drop(columns=["lag_date"])

        # Format column layout
        final_cols = [
            "date",
            "container_id",
            "business_id",
            "business_name",
            "business_type",
            "num_fryers",
            "avg_daily_customers",
            "day_of_week",
            "is_weekend",
            "lag_7d_liters",
            "daily_liters",
            "is_synthetic",
        ]
        # Retain only requested columns that exist
        available_cols = [c for c in final_cols if c in daily_features.columns]
        daily_features = daily_features.sort_values(["container_id", "date"]).reset_index(drop=True)
        return daily_features[available_cols]
