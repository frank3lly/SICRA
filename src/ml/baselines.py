"""Seasonal Naive benchmark predictor for daily oil volume forecasting."""

from pathlib import Path
from typing import Any, Dict, Optional, Union
import joblib
import numpy as np
import pandas as pd

from src.ml.base import BasePredictor


class SeasonalNaivePredictor(BasePredictor):
    """Seasonal Naive Benchmark Predictor.

    Forecasts daily oil volume using the historical empirical average
    of the same day of the week for each specific food establishment.

    Fallback Hierarchy:
    1. Historical average for specific business_id on target day_of_week.
    2. Historical average for establishment's business_type on target day_of_week.
    3. Global daily mean volume across all establishments.
    """

    def __init__(self) -> None:
        """Initializes empty lookup tables and fallback defaults."""
        self.lookup_table_: Dict[str, Dict[int, float]] = {}
        self.type_lookup_: Dict[str, Dict[int, float]] = {}
        self.global_mean_: float = 0.0
        self.business_type_map_: Dict[str, str] = {}

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "SeasonalNaivePredictor":
        """Fits empirical lookup tables from historical features and daily volumes.

        Args:
            X: DataFrame containing at least 'business_id' and 'day_of_week' (or 'date').
               Optional 'business_type' enables category-level fallback.
            y: Target daily volumes in liters.

        Returns:
            Fitted SeasonalNaivePredictor instance.
        """
        df = X.copy()
        y_arr = np.asarray(y, dtype=float)
        df["_target_"] = y_arr

        if len(y_arr) > 0:
            self.global_mean_ = max(0.0, float(np.nanmean(y_arr)))
        else:
            self.global_mean_ = 0.0

        # Ensure day_of_week exists
        if "day_of_week" not in df.columns:
            if "date" in df.columns:
                df["day_of_week"] = pd.to_datetime(df["date"]).dt.dayofweek
            elif "timestamp" in df.columns:
                df["day_of_week"] = pd.to_datetime(df["timestamp"]).dt.dayofweek
            else:
                raise ValueError("DataFrame must contain 'day_of_week', 'date', or 'timestamp'.")

        df["business_id"] = df["business_id"].astype(str)
        df["day_of_week"] = df["day_of_week"].astype(int)

        # 1. Establishment-level lookup table: {business_id: {day_of_week: mean_volume}}
        self.lookup_table_ = {}
        grouped_b = df.groupby(["business_id", "day_of_week"])["_target_"].mean()
        for (b_id, dow), val in grouped_b.items():
            b_id_str = str(b_id)
            dow_int = int(dow)
            if b_id_str not in self.lookup_table_:
                self.lookup_table_[b_id_str] = {}
            self.lookup_table_[b_id_str][dow_int] = max(0.0, float(val))

        # 2. Business type fallback lookup table: {business_type: {day_of_week: mean_volume}}
        self.type_lookup_ = {}
        self.business_type_map_ = {}
        if "business_type" in df.columns:
            df["_norm_btype"] = df["business_type"].apply(
                lambda t: t.value if hasattr(t, "value") else str(t)
            )
            btype_map = (
                df.drop_duplicates(subset=["business_id"])
                .set_index("business_id")["_norm_btype"]
                .to_dict()
            )
            self.business_type_map_ = {str(k): str(v) for k, v in btype_map.items()}

            grouped_t = df.groupby(["_norm_btype", "day_of_week"])["_target_"].mean()
            for (b_type, dow), val in grouped_t.items():
                b_type_str = str(b_type)
                dow_int = int(dow)
                if b_type_str not in self.type_lookup_:
                    self.type_lookup_[b_type_str] = {}
                self.type_lookup_[b_type_str][dow_int] = max(0.0, float(val))

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Returns non-negative predicted volumes in liters/day using hierarchical lookups.

        Args:
            X: Input DataFrame with 'business_id', 'day_of_week' (or 'date'),
               and optional 'business_type'.

        Returns:
            1D numpy array of predicted daily oil generation in liters/day.
        """
        if X.empty:
            return np.array([], dtype=float)

        df = X.copy()
        if "day_of_week" not in df.columns:
            if "date" in df.columns:
                df["day_of_week"] = pd.to_datetime(df["date"]).dt.dayofweek
            elif "timestamp" in df.columns:
                df["day_of_week"] = pd.to_datetime(df["timestamp"]).dt.dayofweek
            else:
                raise ValueError("DataFrame must contain 'day_of_week', 'date', or 'timestamp'.")

        business_ids = (
            df["business_id"].astype(str).tolist()
            if "business_id" in df.columns
            else [None] * len(df)
        )
        dows = df["day_of_week"].astype(int).tolist()

        if "business_type" in df.columns:
            business_types = [
                (t.value if hasattr(t, "value") else str(t)) if pd.notna(t) else None
                for t in df["business_type"]
            ]
        else:
            business_types = [None] * len(df)

        preds = []
        for b_id, dow, b_type in zip(business_ids, dows, business_types):
            val = None

            # 1. Primary lookup: (business_id, day_of_week)
            if b_id is not None and b_id in self.lookup_table_:
                val = self.lookup_table_[b_id].get(dow)

            # 2. Fallback lookup: (business_type, day_of_week)
            if val is None:
                if b_type is None and b_id is not None:
                    b_type = self.business_type_map_.get(b_id)
                if b_type is not None and b_type in self.type_lookup_:
                    val = self.type_lookup_[b_type].get(dow)

            # 3. Global fallback: global_mean_
            if val is None:
                val = self.global_mean_

            preds.append(max(0.0, float(val)))

        return np.array(preds, dtype=float)

    def save(self, path: Union[str, Path]) -> None:
        """Serializes lookup tables and configuration to disk via joblib."""
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, dest)

    @classmethod
    def load(cls, path: Union[str, Path]) -> "SeasonalNaivePredictor":
        """Loads a serialized SeasonalNaivePredictor from disk via joblib."""
        src = Path(path)
        if not src.exists():
            raise FileNotFoundError(f"Model file not found at: {src}")
        loaded = joblib.load(src)
        if not isinstance(loaded, SeasonalNaivePredictor):
            raise TypeError(f"Loaded object is not a SeasonalNaivePredictor: {type(loaded)}")
        return loaded
