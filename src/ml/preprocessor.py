"""Feature engineering and preprocessing pipeline for SICRA linear and GLM models."""

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler, StandardScaler


class FeaturePipeline:
    """Transforms raw food establishment features and temporal indicators into encoded matrices.

    Pipeline Transformations:
    - Continuous predictors ('num_fryers', 'avg_daily_customers'): standardized via StandardScaler.
    - Continuous interaction ('num_fryers * avg_daily_customers'): standardized via StandardScaler.
    - 7-day seasonal lag ('lag_7d_liters'): imputed with establishment historical median
      (or global median) and scaled via RobustScaler.
    - Categorical predictor ('business_type'): one-hot encoded with 'CAFETERIA' as reference (drop first).
    - Categorical predictor ('day_of_week'): one-hot encoded with 'Monday' as reference (drop first).
    - Domain interaction terms: explicit products of each non-reference business type and weekday.
    """

    CATEGORIES_BUSINESS_TYPE = ["FRITURA", "PICA_POLLO", "RESTAURANTE"]
    REFERENCE_BUSINESS_TYPE = "CAFETERIA"

    CATEGORIES_DAY_OF_WEEK = [
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    REFERENCE_DAY_OF_WEEK = "Monday"

    DAY_MAP = {
        0: "Monday",
        1: "Tuesday",
        2: "Wednesday",
        3: "Thursday",
        4: "Friday",
        5: "Saturday",
        6: "Sunday",
    }

    def __init__(self) -> None:
        """Initializes internal scalers, imputation statistics, and feature names."""
        self.scaler_fryers_ = StandardScaler()
        self.scaler_customers_ = StandardScaler()
        self.scaler_interaction_ = StandardScaler()
        self.scaler_lag_ = RobustScaler()

        self.global_median_lag_: float = 0.0
        self.biz_median_lag_: Dict[str, float] = {}
        self.global_median_fryers_: float = 1.0
        self.global_median_customers_: float = 100.0

        self.feature_names_out_: List[str] = []
        self._is_fitted: bool = False

    def _normalize_business_type(self, df: pd.DataFrame) -> pd.Series:
        """Normalizes business type values to standardized uppercase string."""
        if "business_type" in df.columns:
            s = df["business_type"]
            return s.apply(
                lambda t: (
                    t.value if hasattr(t, "value") else str(t).upper().strip()
                )
                if pd.notna(t)
                else self.REFERENCE_BUSINESS_TYPE
            )
        return pd.Series(
            [self.REFERENCE_BUSINESS_TYPE] * len(df), index=df.index
        )

    def _normalize_day_of_week(self, df: pd.DataFrame) -> pd.Series:
        """Normalizes day of week to standard English day name."""
        if "day_of_week" in df.columns:
            s = df["day_of_week"]
            if pd.api.types.is_numeric_dtype(s):
                return s.astype(int).map(self.DAY_MAP).fillna(self.REFERENCE_DAY_OF_WEEK)
            else:
                def _parse_val(val: Any) -> str:
                    if pd.isna(val):
                        return self.REFERENCE_DAY_OF_WEEK
                    val_str = str(val).strip()
                    if val_str.isdigit():
                        return self.DAY_MAP.get(int(val_str), self.REFERENCE_DAY_OF_WEEK)
                    cap = val_str.capitalize()
                    return (
                        cap
                        if cap in [self.REFERENCE_DAY_OF_WEEK] + self.CATEGORIES_DAY_OF_WEEK
                        else self.REFERENCE_DAY_OF_WEEK
                    )

                return s.apply(_parse_val)
        elif "date" in df.columns:
            return pd.to_datetime(df["date"]).dt.day_name()
        elif "timestamp" in df.columns:
            return pd.to_datetime(df["timestamp"]).dt.day_name()
        return pd.Series([self.REFERENCE_DAY_OF_WEEK] * len(df), index=df.index)

    def fit(self, df: pd.DataFrame) -> "FeaturePipeline":
        """Fits scalers and learns imputation statistics from training dataset.

        Args:
            df: Input training DataFrame.

        Returns:
            Fitted FeaturePipeline instance.
        """
        # 1. Continuous predictors
        fryers = (
            df["num_fryers"].fillna(1.0).to_numpy(dtype=float).reshape(-1, 1)
            if "num_fryers" in df.columns
            else np.ones((len(df), 1))
        )
        self.global_median_fryers_ = float(np.median(fryers))
        self.scaler_fryers_.fit(fryers)

        customers = (
            df["avg_daily_customers"].fillna(100.0).to_numpy(dtype=float).reshape(-1, 1)
            if "avg_daily_customers" in df.columns
            else np.full((len(df), 1), 100.0)
        )
        self.global_median_customers_ = float(np.median(customers))
        self.scaler_customers_.fit(customers)

        # Continuous interaction: fryers * customers
        interaction = (fryers * customers).reshape(-1, 1)
        self.scaler_interaction_.fit(interaction)

        # 2. 7-day seasonal lag imputation and scaling
        if "lag_7d_liters" in df.columns:
            lag_series = df["lag_7d_liters"].copy()
            if "daily_liters" in df.columns:
                fallback_val = float(df["daily_liters"].median())
            else:
                fallback_val = float(lag_series.dropna().median()) if not lag_series.dropna().empty else 0.0

            self.global_median_lag_ = (
                float(lag_series.dropna().median())
                if not lag_series.dropna().empty
                else fallback_val
            )

            if "business_id" in df.columns:
                self.biz_median_lag_ = (
                    df.groupby("business_id")["lag_7d_liters"]
                    .median()
                    .dropna()
                    .to_dict()
                )
                for biz_id, med in self.biz_median_lag_.items():
                    mask = (df["business_id"] == biz_id) & lag_series.isna()
                    lag_series.loc[mask] = med

            lag_series = lag_series.fillna(self.global_median_lag_)
            lag_arr = lag_series.to_numpy(dtype=float).reshape(-1, 1)
        else:
            self.global_median_lag_ = 0.0
            self.biz_median_lag_ = {}
            lag_arr = np.zeros((len(df), 1))

        self.scaler_lag_.fit(lag_arr)

        # 3. Assemble human-readable feature names
        names = [
            "num_fryers",
            "avg_daily_customers",
            "lag_7d_liters",
            "num_fryers * avg_daily_customers",
        ]
        for bt in self.CATEGORIES_BUSINESS_TYPE:
            names.append(f"business_type[{bt}]")
        for d in self.CATEGORIES_DAY_OF_WEEK:
            names.append(f"day_of_week[{d}]")
        for bt in self.CATEGORIES_BUSINESS_TYPE:
            for d in self.CATEGORIES_DAY_OF_WEEK:
                names.append(f"business_type[{bt}] * day_of_week[{d}]")

        self.feature_names_out_ = names
        self._is_fitted = True
        return self

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """Transforms input DataFrame into the dense scaled and encoded feature matrix.

        Args:
            df: Input DataFrame.

        Returns:
            Dense 2D numpy array of shape (N, 31).
        """
        if not self._is_fitted:
            raise RuntimeError("FeaturePipeline must be fitted before calling transform.")

        n_samples = len(df)
        if n_samples == 0:
            return np.empty((0, len(self.feature_names_out_)), dtype=float)

        # 1. Continuous predictors
        fryers = (
            df["num_fryers"].fillna(self.global_median_fryers_).to_numpy(dtype=float).reshape(-1, 1)
            if "num_fryers" in df.columns
            else np.full((n_samples, 1), self.global_median_fryers_)
        )
        scaled_fryers = self.scaler_fryers_.transform(fryers)

        customers = (
            df["avg_daily_customers"].fillna(self.global_median_customers_).to_numpy(dtype=float).reshape(-1, 1)
            if "avg_daily_customers" in df.columns
            else np.full((n_samples, 1), self.global_median_customers_)
        )
        scaled_customers = self.scaler_customers_.transform(customers)

        interaction = (fryers * customers).reshape(-1, 1)
        scaled_interaction = self.scaler_interaction_.transform(interaction)

        # 2. Lag imputation and scaling
        if "lag_7d_liters" in df.columns:
            lag_series = df["lag_7d_liters"].copy()
            if "business_id" in df.columns:
                for biz_id, med in self.biz_median_lag_.items():
                    mask = (df["business_id"] == biz_id) & lag_series.isna()
                    lag_series.loc[mask] = med
            lag_series = lag_series.fillna(self.global_median_lag_)
            lag_arr = lag_series.to_numpy(dtype=float).reshape(-1, 1)
        else:
            lag_arr = np.full((n_samples, 1), self.global_median_lag_)

        scaled_lag = self.scaler_lag_.transform(lag_arr)

        # 3. Categorical normalizations
        norm_types = self._normalize_business_type(df)
        norm_days = self._normalize_day_of_week(df)

        cols = [scaled_fryers, scaled_customers, scaled_lag, scaled_interaction]

        # Categorical main dummies
        type_dummies = {}
        for bt in self.CATEGORIES_BUSINESS_TYPE:
            d_arr = (norm_types == bt).to_numpy(dtype=float).reshape(-1, 1)
            type_dummies[bt] = d_arr
            cols.append(d_arr)

        day_dummies = {}
        for d in self.CATEGORIES_DAY_OF_WEEK:
            d_arr = (norm_days == d).to_numpy(dtype=float).reshape(-1, 1)
            day_dummies[d] = d_arr
            cols.append(d_arr)

        # Domain interaction terms: business_type * day_of_week
        for bt in self.CATEGORIES_BUSINESS_TYPE:
            for d in self.CATEGORIES_DAY_OF_WEEK:
                inter_arr = type_dummies[bt] * day_dummies[d]
                cols.append(inter_arr)

        return np.hstack(cols)

    def fit_transform(self, df: pd.DataFrame) -> np.ndarray:
        """Fits pipeline parameters and returns transformed matrix.

        Args:
            df: Input DataFrame.

        Returns:
            Dense 2D numpy array of shape (N, 31).
        """
        return self.fit(df).transform(df)

    def get_feature_names_out(self) -> List[str]:
        """Returns ordered human-readable feature column names.

        Returns:
            List of 31 feature names matching columns in transform() output.
        """
        if not self._is_fitted:
            raise RuntimeError("FeaturePipeline must be fitted before retrieving feature names.")
        return list(self.feature_names_out_)
