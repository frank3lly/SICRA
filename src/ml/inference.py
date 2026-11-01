"""Unified inference engine facade for production predictions and fill rate estimates."""

from pathlib import Path
from typing import Any, Dict, Optional, Union
import numpy as np
import pandas as pd

from src.ml.base import BasePredictor
from src.ml.baselines import SeasonalNaivePredictor
from src.ml.rate_estimator import LoadCellRateEstimator
from src.ml.registry import ModelRegistry


class InferenceEngine:
    """High-level production inference API facade for daily generation and fill projections."""

    def __init__(
        self,
        models_dir: Union[str, Path] = "models/production",
        model: Optional[BasePredictor] = None,
        fallback_model: Optional[BasePredictor] = None,
    ) -> None:
        """Initializes inference engine with active model and fallback benchmark.

        Args:
            models_dir: Directory where production model artifacts are persisted.
            model: Optional pre-loaded or in-memory candidate predictor.
            fallback_model: Optional pre-loaded or in-memory fallback predictor.
        """
        self.models_dir = Path(models_dir)
        self.registry = ModelRegistry(self.models_dir)
        self.metadata: Dict[str, Any] = {}

        if model is not None:
            self.model: BasePredictor = model
            self.fallback_model: Optional[BasePredictor] = fallback_model
            self.metadata = {
                "algorithm": model.__class__.__name__,
                "r04_passed": True,
            }
        elif self.registry.is_production_ready():
            self.model, self.metadata = self.registry.load_production_model()
            self.fallback_model = self.registry.load_fallback_model()
        else:
            # Standalone uninitialized fallback
            self.model = fallback_model or SeasonalNaivePredictor()
            self.fallback_model = None

        self.rate_estimator = LoadCellRateEstimator()

    def predict_daily_volume(
        self,
        business_type: str,
        num_fryers: int,
        avg_daily_customers: int,
        day_of_week: int,
        lag_7d_liters: float,
        business_id: Optional[str] = None,
    ) -> float:
        """Returns non-negative predicted volume in liters for an establishment day.

        Args:
            business_type: Food establishment classification (e.g. 'FRITURA').
            num_fryers: Number of fryers/boilers installed.
            avg_daily_customers: Estimated average daily customer throughput.
            day_of_week: Target weekday index (0 = Monday, ..., 6 = Sunday).
            lag_7d_liters: Volume generated on the same weekday one week prior.
            business_id: Optional unique identifier for establishment-specific lookups.

        Returns:
            Non-negative volume prediction in liters/day (float >= 0.0).
        """
        # 1. Direct fast-path for SeasonalNaivePredictor (< 0.05 ms)
        if isinstance(self.model, SeasonalNaivePredictor):
            b_id = str(business_id) if business_id else None
            dow = int(day_of_week) if isinstance(day_of_week, (int, np.integer)) else 0
            b_type = (
                business_type.value
                if hasattr(business_type, "value")
                else str(business_type).upper().strip()
            )
            val = None
            if b_id in self.model.lookup_table_:
                val = self.model.lookup_table_[b_id].get(dow)
            if val is None:
                if b_type in self.model.type_lookup_:
                    val = self.model.type_lookup_[b_type].get(dow)
            if val is None:
                val = self.model.global_mean_
            return max(0.0, float(val))

        # 2. Fast-path for pipeline-based models (< 0.5 ms)
        if hasattr(self.model, "pipeline_") and hasattr(
            self.model.pipeline_, "transform_single"
        ) and getattr(self.model, "model_", None) is not None:
            try:
                x_single = self.model.pipeline_.transform_single(
                    business_type=business_type,
                    num_fryers=num_fryers,
                    avg_daily_customers=avg_daily_customers,
                    day_of_week=day_of_week,
                    lag_7d_liters=lag_7d_liters,
                    business_id=business_id,
                )
                raw_pred = self.model.model_.predict(x_single)
                return max(0.0, float(raw_pred[0]))
            except Exception:
                pass

        # 3. Standard DataFrame path
        input_df = pd.DataFrame([
            {
                "business_id": business_id or "unspecified",
                "business_type": business_type,
                "num_fryers": num_fryers,
                "avg_daily_customers": avg_daily_customers,
                "day_of_week": day_of_week,
                "lag_7d_liters": lag_7d_liters,
            }
        ])

        try:
            preds = self.model.predict(input_df)
            val = float(preds[0])
        except Exception:
            # Safe runtime fallback to benchmark model
            if self.fallback_model is not None:
                preds = self.fallback_model.predict(input_df)
                val = float(preds[0])
            else:
                raise

        return max(0.0, val)

    def predict_hours_to_80_percent(
        self,
        current_liters: float,
        capacity_liters: float,
        daily_pour_rate: float,
        telemetry_df: Optional[pd.DataFrame] = None,
    ) -> float:
        """Returns projected hours until reaching 80% volume threshold.

        If continuous telemetry is provided, utilizes LoadCellRateEstimator.
        Otherwise, projects via the daily pour rate.

        Args:
            current_liters: Current volume of oil in container.
            capacity_liters: Container maximum rated capacity.
            daily_pour_rate: Estimated daily oil addition rate in liters/day.
            telemetry_df: Optional recent load cell telemetry time-series.

        Returns:
            Hours remaining until 80% threshold (0.0 if full, inf if rate <= 0).
        """
        threshold_liters = 0.80 * capacity_liters

        # Immediate threshold boundary check
        if current_liters >= threshold_liters:
            return 0.0

        if telemetry_df is not None and not telemetry_df.empty:
            estimate = self.rate_estimator.estimate_hours_to_threshold(
                telemetry_df=telemetry_df,
                capacity_liters=capacity_liters,
                threshold_pct=0.80,
            )
            if estimate is not None:
                return float(estimate)

        # Standard pour rate calculation
        if daily_pour_rate <= 0.0:
            return float("inf")

        hourly_rate = daily_pour_rate / 24.0
        hours_remaining = (threshold_liters - current_liters) / hourly_rate
        return max(0.0, float(hours_remaining))
