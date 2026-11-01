"""Load cell telemetry rate estimator for short-term volume slope and time-to-80%."""

from datetime import datetime
from typing import Optional, Tuple, Union
import numpy as np
import pandas as pd
from scipy.ndimage import median_filter


class LoadCellRateEstimator:
    """Estimates the real-time slope of volume change (delta V / delta t)

    from recent load cell telemetry to project hours remaining until reaching
    the critical 80% container capacity threshold.
    """

    def __init__(self, window_hours: int = 48, min_samples: int = 6) -> None:
        """Initializes the fill rate estimator.

        Args:
            window_hours: Retrospective sliding window duration in operational hours.
            min_samples: Minimum number of samples required to compute a reliable slope.
        """
        self.window_hours = window_hours
        self.min_samples = min_samples

    def _extract_and_prepare(
        self, telemetry_df: pd.DataFrame
    ) -> Tuple[np.ndarray, np.ndarray, float]:
        """Extracts cleaned operational hours, volume, and current volume.

        Applies sliding window filtering, median filtering for transient sensor noise,
        and excludes prior drain/collection cycles.

        Returns:
            Tuple of (t_hours, volumes, current_volume).
        """
        if telemetry_df.empty:
            return np.array([]), np.array([]), 0.0

        df = telemetry_df.copy()

        # 1. Resolve timestamp column
        time_col = None
        for col in [
            "measurement_timestamp",
            "timestamp",
            "created_at",
            "datetime",
            "time",
            "date",
        ]:
            if col in df.columns:
                time_col = col
                break

        if time_col is not None:
            col_series = df[time_col]
            if pd.api.types.is_numeric_dtype(col_series):
                if float(col_series.max()) > 1e8:
                    df["_dt_"] = pd.to_datetime(col_series, unit="s")
                else:
                    df["_dt_"] = pd.to_timedelta(col_series, unit="h") + pd.Timestamp(
                        "2026-01-01"
                    )
            else:
                df["_dt_"] = pd.to_datetime(col_series)
        elif isinstance(df.index, pd.DatetimeIndex):
            df["_dt_"] = df.index
        elif "t" in df.columns:
            df["_dt_"] = pd.to_timedelta(df["t"], unit="h") + pd.Timestamp("2026-01-01")
        else:
            raise ValueError(
                "telemetry_df must contain a datetime column or index (e.g. 'measurement_timestamp', 'timestamp')."
            )

        # 2. Resolve volume column
        vol_col = None
        for col in [
            "calculated_liters",
            "volume_liters",
            "liters",
            "volume",
            "current_volume_liters",
            "v",
        ]:
            if col in df.columns:
                vol_col = col
                break

        if vol_col is None:
            raise ValueError(
                "telemetry_df must contain a volume column (e.g. 'calculated_liters', 'volume_liters', 'liters')."
            )

        df["_vol_"] = df[vol_col].astype(float)

        # Sort chronologically
        df = df.sort_values("_dt_").reset_index(drop=True)

        # Filter by retrospective window
        max_time = df["_dt_"].max()
        cutoff_time = max_time - pd.Timedelta(hours=self.window_hours)
        df = df[df["_dt_"] >= cutoff_time].reset_index(drop=True)

        if len(df) == 0:
            return np.array([]), np.array([]), 0.0

        current_volume = float(df["_vol_"].iloc[-1])

        # Exclude sudden negative volume drops (ΔV < -5.0 L) from drain/collection events
        diffs = df["_vol_"].diff()
        drain_indices = df.index[diffs < -5.0].tolist()
        if drain_indices:
            last_drain_idx = drain_indices[-1]
            df = df.iloc[last_drain_idx:].reset_index(drop=True)

        if len(df) < self.min_samples:
            return np.array([]), np.array([]), current_volume

        # Median filter to eliminate transient sensor noise (mode='nearest' preserves ramp slopes)
        v_raw = df["_vol_"].to_numpy(dtype=float)
        v_clean = median_filter(v_raw, size=3, mode="nearest")

        # Convert timestamps to elapsed hours
        t_seconds = (df["_dt_"] - df["_dt_"].iloc[0]).dt.total_seconds().to_numpy(dtype=float)
        t_hours = t_seconds / 3600.0

        return t_hours, v_clean, current_volume

    def calculate_slope(self, telemetry_df: pd.DataFrame) -> float:
        """Calculates local linear rate of change (m = ΔV / Δt) in Liters / Hour.

        Uses Ordinary Least Squares on windowed telemetry data.

        Args:
            telemetry_df: DataFrame of load cell telemetry readings.

        Returns:
            Slope m in Liters/hour. Returns 0.0 if insufficient data or zero variance.
        """
        t, v, _ = self._extract_and_prepare(telemetry_df)
        if len(t) < self.min_samples:
            return 0.0

        t_diff = t - np.mean(t)
        v_diff = v - np.mean(v)
        denominator = float(np.sum(t_diff**2))
        if denominator == 0.0:
            return 0.0

        return float(np.sum(t_diff * v_diff) / denominator)

    def estimate_hours_to_threshold(
        self,
        telemetry_df: pd.DataFrame,
        capacity_liters: float,
        threshold_pct: float = 0.80,
    ) -> Optional[float]:
        """Projects exact hours remaining until reaching threshold capacity.

        Formulation:
            Hours to threshold =
                (threshold_pct * V_capacity - V_current) / m   if m > 0 and V_current < threshold
                0.0                                           if V_current >= threshold
                inf                                           if m <= 0 (container inactive or emptied)

        Args:
            telemetry_df: Telemetry readings DataFrame.
            capacity_liters: Total capacity of the container in liters.
            threshold_pct: Critical percentage threshold (default: 0.80 for 80%).

        Returns:
            Hours remaining as float, or None if insufficient samples.
        """
        if telemetry_df.empty:
            return None

        t, v, current_volume = self._extract_and_prepare(telemetry_df)
        threshold_liters = threshold_pct * capacity_liters

        # If already at or above threshold
        if current_volume >= threshold_liters:
            return 0.0

        if len(t) < self.min_samples:
            return None

        m = self.calculate_slope(telemetry_df)
        if m <= 0.0:
            return float("inf")

        hours_remaining = (threshold_liters - current_volume) / m
        return max(0.0, float(hours_remaining))

    def detect_drain_event(
        self,
        telemetry_df: pd.DataFrame,
        capacity_liters: Optional[float] = None,
    ) -> bool:
        """Identifies abrupt drops (> 30% capacity reduction in < 1 hour).

        Args:
            telemetry_df: Telemetry readings DataFrame.
            capacity_liters: Optional total capacity in liters. If None,
                inferred from dataframe or max observed volume.

        Returns:
            True if an abrupt drain event is detected, False otherwise.
        """
        if telemetry_df.empty or len(telemetry_df) < 2:
            return False

        df = telemetry_df.copy()

        # Find timestamp
        time_col = None
        for col in [
            "measurement_timestamp",
            "timestamp",
            "created_at",
            "datetime",
            "time",
            "date",
        ]:
            if col in df.columns:
                time_col = col
                break

        if time_col is not None:
            col_series = df[time_col]
            if pd.api.types.is_numeric_dtype(col_series):
                if float(col_series.max()) > 1e8:
                    df["_dt_"] = pd.to_datetime(col_series, unit="s")
                else:
                    df["_dt_"] = pd.to_timedelta(col_series, unit="h") + pd.Timestamp(
                        "2026-01-01"
                    )
            else:
                df["_dt_"] = pd.to_datetime(col_series)
        elif isinstance(df.index, pd.DatetimeIndex):
            df["_dt_"] = df.index
        elif "t" in df.columns:
            df["_dt_"] = pd.to_timedelta(df["t"], unit="h") + pd.Timestamp("2026-01-01")
        else:
            return False

        df = df.sort_values("_dt_").reset_index(drop=True)

        # 1. Check via fill_percentage if present
        if "fill_percentage" in df.columns:
            pcts = df["fill_percentage"].to_numpy(dtype=float)
            dts = df["_dt_"]
            for i in range(len(pcts)):
                for j in range(i + 1, len(pcts)):
                    dt_hours = (dts.iloc[j] - dts.iloc[i]).total_seconds() / 3600.0
                    if dt_hours > 1.0:
                        break
                    if pcts[i] - pcts[j] > 30.0:
                        return True

        # 2. Check via volume column
        vol_col = None
        for col in [
            "calculated_liters",
            "volume_liters",
            "liters",
            "volume",
            "current_volume_liters",
            "v",
        ]:
            if col in df.columns:
                vol_col = col
                break

        if vol_col is None:
            return False

        vols = df[vol_col].to_numpy(dtype=float)
        dts = df["_dt_"]

        if capacity_liters is not None:
            cap = float(capacity_liters)
        elif "capacity_liters" in df.columns:
            cap = float(df["capacity_liters"].iloc[0])
        else:
            cap = float(np.nanmax(vols)) if len(vols) > 0 else 0.0

        drop_threshold = 0.30 * cap if cap > 0 else 5.0

        for i in range(len(vols)):
            for j in range(i + 1, len(vols)):
                dt_hours = (dts.iloc[j] - dts.iloc[i]).total_seconds() / 3600.0
                if dt_hours > 1.0:
                    break
                if vols[i] - vols[j] > drop_threshold:
                    return True

        return False
