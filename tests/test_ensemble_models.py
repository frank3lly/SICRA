"""Unit and integration tests for non-linear tree ensembles and fine-tuning pipeline."""

from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
import pytest

from src.ml.ensemble_models import TreeEnsemblePredictor


@pytest.fixture
def processed_data():
    """Loads chronological train and test datasets if available."""
    train_path = Path("data/processed/train_chronological.csv")
    test_path = Path("data/processed/test_chronological.csv")
    if not train_path.exists() or not test_path.exists():
        pytest.skip("Processed chronological datasets not found.")
    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)
    return train_df, test_df


class TestTreeEnsemblePredictor:
    """Test suite for TreeEnsemblePredictor."""

    def test_pretraining_and_finetuning_continuity(self, processed_data) -> None:
        """Fit pre-training on synthetic slice, execute fine-tuning on real slice, verify MAE."""
        train_df, test_df = processed_data

        # Separate synthetic vs empirical rows if flag present, or create partition
        if "is_synthetic" in train_df.columns:
            synth_mask = train_df["is_synthetic"] == True
            real_mask = train_df["is_synthetic"] == False
            if real_mask.sum() > 20:
                X_synth = train_df[synth_mask]
                y_synth = train_df.loc[synth_mask, "daily_liters"]
                X_real = train_df[real_mask]
                y_real = train_df.loc[real_mask, "daily_liters"]
            else:
                # Use split partition
                X_synth = train_df.iloc[:1400]
                y_synth = train_df["daily_liters"].iloc[:1400]
                X_real = train_df.iloc[1400:]
                y_real = train_df["daily_liters"].iloc[1400:]
        else:
            X_synth = train_df.iloc[:1400]
            y_synth = train_df["daily_liters"].iloc[:1400]
            X_real = train_df.iloc[1400:]
            y_real = train_df["daily_liters"].iloc[1400:]

        model = TreeEnsemblePredictor(
            algorithm="hist_gradient_boosting",
            n_estimators=50,
            max_depth=6,
            random_state=42,
        )

        # Baseline pre-training
        model.fit(X_synth, y_synth)
        pretrain_mae = model.evaluate_mae(X_synth, y_synth)
        assert isinstance(pretrain_mae, float)
        assert pretrain_mae >= 0.0

        # Fine-tuning calibration
        model.pretrain_and_finetune(
            X_synth=X_synth,
            y_synth=y_synth,
            X_real=X_real,
            y_real=y_real,
            real_weight_multiplier=10.0,
        )

        preds = model.predict(test_df)
        assert len(preds) == len(test_df)
        assert not np.isnan(preds).any()
        assert np.min(preds) >= 0.0

    def test_feature_importance_sanity(self, processed_data) -> None:
        """Assert num_fryers or avg_daily_customers ranks among the top 3 features."""
        train_df, _ = processed_data

        # 1. Test RandomForestRegressor
        rf_model = TreeEnsemblePredictor(
            algorithm="random_forest",
            n_estimators=50,
            max_depth=8,
            random_state=42,
        )
        rf_model.fit(train_df, train_df["daily_liters"])
        rf_imp = rf_model.get_feature_importances()

        assert list(rf_imp.columns) == ["feature", "importance"]
        top_3_rf = set(rf_imp.head(3)["feature"].tolist())
        target_features = {
            "num_fryers",
            "avg_daily_customers",
            "num_fryers * avg_daily_customers",
        }
        assert len(top_3_rf.intersection(target_features)) > 0

        # 2. Test HistGradientBoostingRegressor
        hgb_model = TreeEnsemblePredictor(
            algorithm="hist_gradient_boosting",
            n_estimators=50,
            max_depth=6,
            random_state=42,
        )
        hgb_model.fit(train_df, train_df["daily_liters"])
        hgb_imp = hgb_model.get_feature_importances()

        top_3_hgb = set(hgb_imp.head(3)["feature"].tolist())
        assert len(top_3_hgb.intersection(target_features)) > 0

    def test_non_negativity_constraint(self, processed_data) -> None:
        """Assert all predictions satisfy y_hat >= 0.0 across 1,000 extreme edge samples."""
        train_df, _ = processed_data
        model = TreeEnsemblePredictor(
            algorithm="hist_gradient_boosting",
            n_estimators=50,
            max_depth=6,
            random_state=42,
        )
        model.fit(train_df, train_df["daily_liters"])

        rng = np.random.default_rng(42)
        n_samples = 1000
        extreme_df = pd.DataFrame({
            "business_id": ["biz_extreme"] * n_samples,
            "business_type": rng.choice(
                ["FRITURA", "PICA_POLLO", "CAFETERIA", "RESTAURANTE"], size=n_samples
            ),
            "day_of_week": rng.integers(0, 7, size=n_samples),
            "num_fryers": rng.integers(0, 2, size=n_samples),
            "avg_daily_customers": rng.integers(0, 5, size=n_samples),
            "lag_7d_liters": np.zeros(n_samples),
        })

        preds = model.predict(extreme_df)
        assert len(preds) == n_samples
        assert np.min(preds) >= 0.0

    def test_reproducibility(self, processed_data) -> None:
        """With random_state=42, two separate runs must yield identical predictions."""
        train_df, test_df = processed_data

        m1 = TreeEnsemblePredictor(
            algorithm="hist_gradient_boosting",
            n_estimators=40,
            max_depth=6,
            random_state=42,
        ).fit(train_df, train_df["daily_liters"])

        m2 = TreeEnsemblePredictor(
            algorithm="hist_gradient_boosting",
            n_estimators=40,
            max_depth=6,
            random_state=42,
        ).fit(train_df, train_df["daily_liters"])

        p1 = m1.predict(test_df)
        p2 = m2.predict(test_df)

        np.testing.assert_allclose(p1, p2, atol=1e-6)

    def test_serialization(self, processed_data) -> None:
        """Assert saving and reloading preserves model weights and prediction values."""
        train_df, test_df = processed_data
        model = TreeEnsemblePredictor(
            algorithm="random_forest",
            n_estimators=30,
            max_depth=6,
            random_state=42,
        ).fit(train_df, train_df["daily_liters"])

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "ensemble_model.joblib"
            model.save(model_path)
            assert model_path.exists()

            loaded = TreeEnsemblePredictor.load(model_path)
            assert isinstance(loaded, TreeEnsemblePredictor)

            orig_preds = model.predict(test_df)
            loaded_preds = loaded.predict(test_df)
            np.testing.assert_allclose(orig_preds, loaded_preds)
