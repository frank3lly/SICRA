"""Integration test suite for chronological validation, Golden Rule decision gate, and model registry."""

import json
from pathlib import Path
import tempfile
import time
import numpy as np
import pandas as pd
import pytest

from src.ml.base import BasePredictor
from src.ml.baselines import SeasonalNaivePredictor
from src.ml.evaluator import ChronologicalEvaluator, evaluate_golden_rule
from src.ml.inference import InferenceEngine
from src.ml.linear_models import GLMPredictor, RegularizedLinearPredictor
from src.ml.registry import ModelRegistry


@pytest.fixture
def processed_data():
    """Loads chronological train and test datasets if present."""
    train_path = Path("data/processed/train_chronological.csv")
    test_path = Path("data/processed/test_chronological.csv")
    if not train_path.exists() or not test_path.exists():
        pytest.skip("Processed chronological datasets not found.")
    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)
    return train_df, test_df


def test_chronological_split_has_no_future_leakage(processed_data) -> None:
    """Asserts timestamps in training strictly precede validation sets in TimeSeriesSplit."""
    train_df, _ = processed_data
    evaluator = ChronologicalEvaluator(time_col="date")
    splits = evaluator.get_chronological_splits(train_df, n_splits=5)

    assert len(splits) == 5
    for train_idx, val_idx in splits:
        train_split = train_df.iloc[train_idx]
        val_split = train_df.iloc[val_idx]

        max_train_date = pd.to_datetime(train_split["date"]).max()
        min_val_date = pd.to_datetime(val_split["date"]).min()

        # Strict temporal directionality: train max date must strictly precede val min date
        assert max_train_date < min_val_date


def test_golden_rule_promotion_when_superior() -> None:
    """Asserts that when MAE_candidate < MAE_baseline, the candidate is marked as active."""
    result = evaluate_golden_rule(candidate_mae=1.42, baseline_mae=1.89)

    assert result.passed is True
    assert result.active_model_type == "CANDIDATE"
    assert result.candidate_mae == 1.42
    assert result.baseline_mae == 1.89
    assert result.improvement_pct == pytest.approx(24.8677, abs=1e-3)


def test_golden_rule_fallback_when_inferior() -> None:
    """Simulates a degraded model and asserts InferenceEngine falls back to Seasonal Naive."""
    result = evaluate_golden_rule(candidate_mae=10.0, baseline_mae=5.0)

    assert result.passed is False
    assert result.active_model_type == "SEASONAL_NAIVE_FALLBACK"
    assert result.improvement_pct == -100.0

    # Test that fallback is registered and deployed safely
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = ModelRegistry(tmpdir)
        fallback_model = SeasonalNaivePredictor()
        # Mock fit fallback
        df_train = pd.DataFrame({
            "business_id": ["biz_fallback"],
            "business_type": ["FRITURA"],
            "day_of_week": [1],
            "daily_liters": [12.0],
        })
        fallback_model.fit(df_train, df_train["daily_liters"])

        # When golden rule fails, register fallback
        meta = {
            "model_id": "fallback_test_v1",
            "algorithm": "SeasonalNaivePredictor",
            "r04_passed": False,
            "test_mae": 10.0,
            "baseline_mae": 5.0,
        }
        registry.register_model(
            model=fallback_model,
            metadata=meta,
            fallback_model=fallback_model,
        )

        engine = InferenceEngine(models_dir=tmpdir)
        assert engine.metadata["r04_passed"] is False

        # Should infer without raising exceptions
        pred = engine.predict_daily_volume(
            business_type="FRITURA",
            num_fryers=2,
            avg_daily_customers=150,
            day_of_week=1,
            lag_7d_liters=10.0,
            business_id="biz_fallback",
        )
        assert pred == pytest.approx(12.0, abs=1e-4)


def test_inference_engine_non_negative_outputs(processed_data) -> None:
    """Asserts all predictions from InferenceEngine.predict_daily_volume() are strictly >= 0.0."""
    train_df, _ = processed_data
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = ModelRegistry(tmpdir)
        model = RegularizedLinearPredictor(method="ridge", alpha=1.0)
        model.fit(train_df, train_df["daily_liters"])

        meta = {
            "model_id": "ridge_test_v1",
            "algorithm": "RegularizedLinearPredictor",
            "r04_passed": True,
        }
        registry.register_model(model=model, metadata=meta)

        engine = InferenceEngine(models_dir=tmpdir)

        # Extreme input cases
        for b_type in ["FRITURA", "CAFETERIA", "PICA_POLLO", "RESTAURANTE", "UNKNOWN"]:
            for dow in range(7):
                pred = engine.predict_daily_volume(
                    business_type=b_type,
                    num_fryers=0,
                    avg_daily_customers=0,
                    day_of_week=dow,
                    lag_7d_liters=0.0,
                )
                assert pred >= 0.0


def test_inference_engine_latency_under_10ms(processed_data) -> None:
    """Asserts InferenceEngine responds to prediction requests in < 10 ms."""
    train_df, _ = processed_data
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = ModelRegistry(tmpdir)
        model = RegularizedLinearPredictor(method="ridge", alpha=1.0)
        model.fit(train_df, train_df["daily_liters"])

        meta = {"model_id": "latency_test", "algorithm": "Ridge", "r04_passed": True}
        registry.register_model(model=model, metadata=meta)

        engine = InferenceEngine(models_dir=tmpdir)

        # Warmup
        engine.predict_daily_volume("FRITURA", 3, 200, 5, 12.0)

        latencies = []
        for _ in range(50):
            t0 = time.perf_counter()
            engine.predict_daily_volume("FRITURA", 3, 200, 5, 12.0)
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000.0)

        avg_latency = float(np.mean(latencies))
        assert avg_latency < 10.0


def test_registry_serialization_and_deserialization(processed_data) -> None:
    """Asserts that saving and reloading preserves model weights and metadata fidelity."""
    train_df, test_df = processed_data
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = ModelRegistry(tmpdir)
        model = GLMPredictor(family="gamma", alpha=0.1)
        model.fit(train_df, train_df["daily_liters"])

        fallback = SeasonalNaivePredictor()
        fallback.fit(train_df, train_df["daily_liters"])

        metadata = {
            "model_id": "glm_gamma_unit_test",
            "algorithm": "GLMPredictor",
            "r04_passed": True,
            "test_mae": 6.33,
            "baseline_mae": 5.91,
            "improvement_pct": -7.1,
            "train_records_count": len(train_df),
            "hyperparameters": {"family": "gamma", "alpha": 0.1},
            "features": model.feature_names_,
        }

        registry.register_model(
            model=model, metadata=metadata, fallback_model=fallback
        )

        assert registry.is_production_ready()

        # Load back
        loaded_model, loaded_meta = registry.load_production_model()
        loaded_fallback = registry.load_fallback_model()

        assert isinstance(loaded_model, GLMPredictor)
        assert isinstance(loaded_fallback, SeasonalNaivePredictor)
        assert loaded_meta["model_id"] == "glm_gamma_unit_test"
        assert loaded_meta["r04_passed"] is True
        assert loaded_meta["features"] == model.feature_names_

        orig_preds = model.predict(test_df)
        loaded_preds = loaded_model.predict(test_df)
        np.testing.assert_allclose(orig_preds, loaded_preds)


def test_predict_hours_to_80_percent_boundary_conditions() -> None:
    """Verifies edge cases for hours to critical threshold calculation."""
    engine = InferenceEngine()

    # 1. Already above 80% (42L of 50L capacity)
    assert engine.predict_hours_to_80_percent(42.0, 50.0, 10.0) == 0.0

    # 2. Inactive / negative pour rate -> infinity
    assert engine.predict_hours_to_80_percent(20.0, 50.0, 0.0) == float("inf")
    assert engine.predict_hours_to_80_percent(20.0, 50.0, -5.0) == float("inf")

    # 3. Standard active rate: 50L capacity, currently at 20L (threshold 40L, remaining 20L)
    # Rate: 24 L/day (= 1 L/h) -> remaining 20 hours
    hours = engine.predict_hours_to_80_percent(20.0, 50.0, 24.0)
    assert hours == pytest.approx(20.0, abs=1e-5)


def test_evaluator_cross_validation_metrics(processed_data) -> None:
    """Verifies that ChronologicalEvaluator.cross_validate() computes fold metrics."""
    train_df, _ = processed_data
    evaluator = ChronologicalEvaluator(time_col="date", target_col="daily_liters")
    model = RegularizedLinearPredictor(method="ridge", alpha=1.0)

    cv_results = evaluator.cross_validate(model=model, df=train_df, n_splits=5)

    assert cv_results["n_splits"] == 5
    assert len(cv_results["fold_maes"]) == 5
    assert len(cv_results["fold_rmses"]) == 5
    assert len(cv_results["fold_r2s"]) == 5
    assert cv_results["mean_mae"] > 0.0
    assert cv_results["mean_rmse"] > 0.0


def test_cli_end_to_end_execution(processed_data, monkeypatch) -> None:
    """Verifies that the CLI executes end-to-end, evaluates Golden Rule, and persists artifacts."""
    from src.ml.cli import main

    with tempfile.TemporaryDirectory() as tmpdir:
        test_args = [
            "cli.py",
            "--data-dir", "data/processed",
            "--model-type", "glm",
            "--family", "poisson",
            "--alpha", "0.1",
            "--enforce-r04",
            "--save-dir", tmpdir,
        ]
        monkeypatch.setattr("sys.argv", test_args)

        exit_code = main()
        assert exit_code == 0

        reg = ModelRegistry(tmpdir)
        assert reg.is_production_ready()
        meta = reg.load_metadata()
        assert meta["r04_passed"] is True
        assert meta["algorithm"] == "GLMPredictor"
        assert meta["test_mae"] < meta["baseline_mae"]
