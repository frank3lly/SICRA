"""Unit and integration tests for baseline predictors and fill rate estimator."""

import math
from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
import pytest

from src.ml.base import BasePredictor
from src.ml.baselines import SeasonalNaivePredictor
from src.ml.rate_estimator import LoadCellRateEstimator


class TestSeasonalNaivePredictor:
    """Test suite for SeasonalNaivePredictor."""

    def test_seasonal_naive_invariance(self) -> None:
        """Verify predictions for same business on given weekday yield historical mean."""
        # 3 Mondays (dow=0) with 10.0, 12.0, 14.0 -> mean 12.0
        # 2 Tuesdays (dow=1) with 20.0, 30.0 -> mean 25.0
        data = {
            "business_id": ["biz_1", "biz_1", "biz_1", "biz_1", "biz_1"],
            "business_type": ["FRITURA"] * 5,
            "day_of_week": [0, 0, 0, 1, 1],
            "daily_liters": [10.0, 12.0, 14.0, 20.0, 30.0],
        }
        df = pd.DataFrame(data)
        X = df[["business_id", "business_type", "day_of_week"]]
        y = df["daily_liters"]

        predictor = SeasonalNaivePredictor()
        predictor.fit(X, y)

        # Predict Monday and Tuesday for biz_1
        X_test = pd.DataFrame({
            "business_id": ["biz_1", "biz_1"],
            "day_of_week": [0, 1],
        })
        preds = predictor.predict(X_test)

        assert len(preds) == 2
        assert preds[0] == pytest.approx(12.0, abs=1e-5)
        assert preds[1] == pytest.approx(25.0, abs=1e-5)

    def test_fallback_integrity_unseen_business(self) -> None:
        """Unseen business falls back to business_type average, then global mean."""
        train_data = {
            "business_id": ["b1", "b1", "b2", "b2"],
            "business_type": ["CAFETERIA", "CAFETERIA", "CAFETERIA", "CAFETERIA"],
            "day_of_week": [0, 1, 0, 1],
            "daily_liters": [5.0, 7.0, 9.0, 11.0],
        }
        train_df = pd.DataFrame(train_data)
        predictor = SeasonalNaivePredictor()
        predictor.fit(
            train_df[["business_id", "business_type", "day_of_week"]],
            train_df["daily_liters"],
        )

        # 1. Unseen business with known business_type: should use type mean on Monday (mean of 5.0 and 9.0 = 7.0)
        unseen_type_test = pd.DataFrame({
            "business_id": ["unseen_store"],
            "business_type": ["CAFETERIA"],
            "day_of_week": [0],
        })
        pred_type = predictor.predict(unseen_type_test)
        assert pred_type[0] == pytest.approx(7.0, abs=1e-5)

        # 2. Unseen business with unseen business_type: should fallback to global mean (32.0 / 4 = 8.0)
        unseen_global_test = pd.DataFrame({
            "business_id": ["unseen_store_2"],
            "business_type": ["UNKNOWN_TYPE"],
            "day_of_week": [0],
        })
        pred_global = predictor.predict(unseen_global_test)
        assert pred_global[0] == pytest.approx(8.0, abs=1e-5)

    def test_non_negativity_constraint(self) -> None:
        """Verify all outputs are strictly >= 0.0 even with edge-case negative targets."""
        train_data = {
            "business_id": ["b_neg"],
            "business_type": ["FRITURA"],
            "day_of_week": [2],
            "daily_liters": [-5.0],
        }
        train_df = pd.DataFrame(train_data)
        predictor = SeasonalNaivePredictor()
        predictor.fit(
            train_df[["business_id", "business_type", "day_of_week"]],
            train_df["daily_liters"],
        )

        test_df = pd.DataFrame({
            "business_id": ["b_neg"],
            "day_of_week": [2],
        })
        preds = predictor.predict(test_df)
        assert preds[0] >= 0.0

    def test_serialization_and_deserialization(self) -> None:
        """Verify model save and load produces identical predictions."""
        train_data = {
            "business_id": ["b1", "b2"],
            "business_type": ["PICA_POLLO", "RESTAURANTE"],
            "day_of_week": [3, 4],
            "daily_liters": [22.4, 15.1],
        }
        df = pd.DataFrame(train_data)
        predictor = SeasonalNaivePredictor()
        predictor.fit(df[["business_id", "business_type", "day_of_week"]], df["daily_liters"])

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "baseline_model.joblib"
            predictor.save(model_path)
            assert model_path.exists()

            loaded = SeasonalNaivePredictor.load(model_path)
            assert isinstance(loaded, SeasonalNaivePredictor)

            test_x = pd.DataFrame({
                "business_id": ["b1", "b2", "unseen"],
                "business_type": ["PICA_POLLO", "RESTAURANTE", "RESTAURANTE"],
                "day_of_week": [3, 4, 4],
            })
            original_preds = predictor.predict(test_x)
            loaded_preds = loaded.predict(test_x)
            np.testing.assert_allclose(original_preds, loaded_preds)

    def test_evaluate_mae_on_processed_dataset(self) -> None:
        """Fit on train_chronological.csv and evaluate MAE on test_chronological.csv."""
        train_path = Path("data/processed/train_chronological.csv")
        test_path = Path("data/processed/test_chronological.csv")

        if not train_path.exists() or not test_path.exists():
            pytest.skip("Processed chronological datasets not present.")

        train_df = pd.read_csv(train_path)
        test_df = pd.read_csv(test_path)

        predictor = SeasonalNaivePredictor()
        predictor.fit(
            train_df[["business_id", "business_type", "day_of_week"]],
            train_df["daily_liters"],
        )

        mae = predictor.evaluate_mae(
            test_df[["business_id", "business_type", "day_of_week"]],
            test_df["daily_liters"],
        )

        assert isinstance(mae, float)
        assert mae > 0.0
        assert mae < 20.0  # Realistic error margin for daily oil generation


class TestLoadCellRateEstimator:
    """Test suite for LoadCellRateEstimator."""

    def test_slope_rate_accuracy_and_hours_to_80_percent(self) -> None:
        """Synthetic linear series: 0.5 L/h over 24h on 50L container starting at 10L.

        Assert estimated hours to 80% (40L) equals (40 - 22) / 0.5 = 36.0 hours ± 0.1 h.
        """
        timestamps = pd.date_range("2026-10-01 00:00:00", periods=25, freq="1h")
        volumes = 10.0 + 0.5 * np.arange(25)  # t=0 -> 10.0L, t=24 -> 22.0L
        telemetry_df = pd.DataFrame({
            "measurement_timestamp": timestamps,
            "calculated_liters": volumes,
        })

        estimator = LoadCellRateEstimator(window_hours=48, min_samples=6)
        slope = estimator.calculate_slope(telemetry_df)
        assert slope == pytest.approx(0.5, abs=0.01)

        hours_to_80 = estimator.estimate_hours_to_threshold(
            telemetry_df=telemetry_df,
            capacity_liters=50.0,
            threshold_pct=0.80,
        )
        assert hours_to_80 is not None
        assert hours_to_80 == pytest.approx(36.0, abs=0.1)

    def test_threshold_already_reached(self) -> None:
        """When container current volume >= 80% capacity, return 0.0 hours."""
        timestamps = pd.date_range("2026-10-01 00:00:00", periods=10, freq="1h")
        volumes = 35.0 + 1.0 * np.arange(10)  # reaches 44L on 50L capacity (80% = 40L)
        telemetry_df = pd.DataFrame({
            "measurement_timestamp": timestamps,
            "calculated_liters": volumes,
        })

        estimator = LoadCellRateEstimator(window_hours=24, min_samples=4)
        hours = estimator.estimate_hours_to_threshold(telemetry_df, capacity_liters=50.0)
        assert hours == 0.0

    def test_flat_or_negative_slope_returns_infinity(self) -> None:
        """When slope <= 0, container is not filling; return inf."""
        timestamps = pd.date_range("2026-10-01 00:00:00", periods=10, freq="1h")
        volumes = np.full(10, 15.0)  # constant volume -> slope 0
        telemetry_df = pd.DataFrame({
            "measurement_timestamp": timestamps,
            "calculated_liters": volumes,
        })

        estimator = LoadCellRateEstimator(window_hours=24, min_samples=4)
        slope = estimator.calculate_slope(telemetry_df)
        assert slope == pytest.approx(0.0, abs=1e-5)

        hours = estimator.estimate_hours_to_threshold(telemetry_df, capacity_liters=50.0)
        assert math.isinf(hours)
        assert hours > 0.0

    def test_insufficient_samples_returns_none(self) -> None:
        """When fewer than min_samples are available, return None."""
        timestamps = pd.date_range("2026-10-01 00:00:00", periods=3, freq="1h")
        volumes = [10.0, 11.0, 12.0]
        telemetry_df = pd.DataFrame({
            "measurement_timestamp": timestamps,
            "calculated_liters": volumes,
        })

        estimator = LoadCellRateEstimator(window_hours=48, min_samples=6)
        assert estimator.calculate_slope(telemetry_df) == 0.0
        assert estimator.estimate_hours_to_threshold(telemetry_df, capacity_liters=50.0) is None

    def test_drain_event_detection_and_exclusion(self) -> None:
        """Verify abrupt drops (>30% in <1h) are detected and excluded from active slope."""
        # 1. Detect drain event
        t1 = pd.Timestamp("2026-10-01 10:00:00")
        t2 = pd.Timestamp("2026-10-01 10:30:00")
        drain_df = pd.DataFrame({
            "measurement_timestamp": [t1, t2],
            "calculated_liters": [40.0, 5.0],  # 35L drop on 50L container = 70% drop
            "capacity_liters": [50.0, 50.0],
        })
        estimator = LoadCellRateEstimator()
        assert estimator.detect_drain_event(drain_df, capacity_liters=50.0) is True

        # 2. Normal slow fill should not trigger drain event
        normal_df = pd.DataFrame({
            "measurement_timestamp": [t1, t2],
            "calculated_liters": [20.0, 20.3],
            "capacity_liters": [50.0, 50.0],
        })
        assert estimator.detect_drain_event(normal_df, capacity_liters=50.0) is False

    def test_slope_recovers_after_drain_event(self) -> None:
        """Readings prior to a drain event (> 5L drop) are filtered out, using only post-drain cycle."""
        # Container was at 30L, drained to 2L, then filled at 0.5 L/h for 10 hours
        t_pre = pd.date_range("2026-10-01 00:00:00", periods=5, freq="1h")
        v_pre = [28.0, 28.5, 29.0, 29.5, 30.0]

        t_post = pd.date_range("2026-10-01 05:00:00", periods=10, freq="1h")
        v_post = 2.0 + 0.5 * np.arange(10)  # 2.0 to 6.5 L

        all_t = list(t_pre) + list(t_post)
        all_v = list(v_pre) + list(v_post)
        telemetry_df = pd.DataFrame({
            "measurement_timestamp": all_t,
            "calculated_liters": all_v,
        })

        estimator = LoadCellRateEstimator(window_hours=48, min_samples=6)
        slope = estimator.calculate_slope(telemetry_df)
        assert slope == pytest.approx(0.5, abs=0.02)
