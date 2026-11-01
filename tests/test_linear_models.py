"""Unit and integration tests for feature preprocessing, regularized regression, and GLMs."""

from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
import pytest

from src.ml.linear_models import GLMPredictor, RegularizedLinearPredictor
from src.ml.preprocessor import FeaturePipeline


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


class TestFeaturePipeline:
    """Test suite for FeaturePipeline."""

    def test_feature_pipeline_dimensions_and_names(self, processed_data) -> None:
        """Verifies dense feature matrix shape (N, 31) and presence of required interaction terms."""
        train_df, test_df = processed_data
        pipeline = FeaturePipeline()
        X_mat = pipeline.fit_transform(train_df)
        feat_names = pipeline.get_feature_names_out()

        assert X_mat.shape == (len(train_df), 31)
        assert len(feat_names) == 31
        assert not np.isnan(X_mat).any()

        # Check key main features
        assert "num_fryers" in feat_names
        assert "avg_daily_customers" in feat_names
        assert "lag_7d_liters" in feat_names
        assert "num_fryers * avg_daily_customers" in feat_names
        assert "business_type[FRITURA]" in feat_names
        assert "day_of_week[Saturday]" in feat_names

        # Check specific domain interaction term
        target_interaction = "business_type[FRITURA] * day_of_week[Saturday]"
        assert target_interaction in feat_names

        # Transform on test set should match column dimension exactly
        X_test_mat = pipeline.transform(test_df)
        assert X_test_mat.shape == (len(test_df), 31)
        assert not np.isnan(X_test_mat).any()

    def test_lag_imputation_handles_missing_values(self) -> None:
        """Verifies that missing lag_7d_liters are imputed without runtime error or NaNs."""
        data = {
            "business_id": ["b1", "b1", "b2", "b2"],
            "business_type": ["RESTAURANTE", "RESTAURANTE", "FRITURA", "FRITURA"],
            "day_of_week": [0, 1, 0, 1],
            "num_fryers": [2, 2, 3, 3],
            "avg_daily_customers": [120, 130, 200, 210],
            "lag_7d_liters": [np.nan, 8.5, np.nan, 14.0],
            "daily_liters": [8.0, 9.0, 14.0, 15.0],
        }
        df = pd.DataFrame(data)
        pipeline = FeaturePipeline()
        X = pipeline.fit_transform(df)

        assert not np.isnan(X).any()
        assert X.shape[0] == 4


class TestRegularizedLinearPredictor:
    """Test suite for RegularizedLinearPredictor."""

    def test_non_negativity_guarantee(self, processed_data) -> None:
        """Assert min(y_hat_Ridge) >= 0.0 across 1,000 synthetic extreme input samples."""
        train_df, _ = processed_data
        model = RegularizedLinearPredictor(method="ridge", alpha=1.0)
        model.fit(train_df, train_df["daily_liters"])

        # Generate 1,000 synthetic extreme inputs (0 customers, 1 fryer, 0 lag)
        rng = np.random.default_rng(42)
        n_samples = 1000
        extreme_df = pd.DataFrame({
            "business_id": ["biz_extreme"] * n_samples,
            "business_type": rng.choice(
                ["FRITURA", "PICA_POLLO", "CAFETERIA", "RESTAURANTE"], size=n_samples
            ),
            "day_of_week": rng.integers(0, 7, size=n_samples),
            "num_fryers": rng.integers(0, 2, size=n_samples),
            "avg_daily_customers": rng.integers(0, 10, size=n_samples),
            "lag_7d_liters": np.zeros(n_samples),
        })

        preds = model.predict(extreme_df)
        assert len(preds) == n_samples
        assert np.min(preds) >= 0.0

    def test_interaction_detection_fritura_saturday(self, processed_data) -> None:
        """Verify business_type[FRITURA] * day_of_week[Saturday] receives positive coefficient."""
        train_df, _ = processed_data
        model = RegularizedLinearPredictor(method="ridge", alpha=1.0)
        model.fit(train_df, train_df["daily_liters"])

        coefs = model.get_coefficients()
        target_term = "business_type[FRITURA] * day_of_week[Saturday]"
        assert target_term in coefs
        assert coefs[target_term] > 0.0

    def test_regularization_penalty_effect(self, processed_data) -> None:
        """Assert ||beta||_{alpha=100} < ||beta||_{alpha=0.01}."""
        train_df, _ = processed_data
        X = train_df
        y = train_df["daily_liters"]

        model_small_alpha = RegularizedLinearPredictor(method="ridge", alpha=0.01)
        model_small_alpha.fit(X, y)
        coefs_small = [
            v for k, v in model_small_alpha.get_coefficients().items() if k != "intercept"
        ]
        norm_small = np.linalg.norm(coefs_small)

        model_large_alpha = RegularizedLinearPredictor(method="ridge", alpha=100.0)
        model_large_alpha.fit(X, y)
        coefs_large = [
            v for k, v in model_large_alpha.get_coefficients().items() if k != "intercept"
        ]
        norm_large = np.linalg.norm(coefs_large)

        assert norm_large < norm_small

    def test_lasso_feature_sparsity(self, processed_data) -> None:
        """Verify Lasso sets non-informative coefficients to exactly 0.0."""
        train_df, _ = processed_data
        model_lasso = RegularizedLinearPredictor(method="lasso", alpha=0.5)
        model_lasso.fit(train_df, train_df["daily_liters"])

        coefs = model_lasso.get_coefficients()
        zero_coefs = [v for k, v in coefs.items() if k != "intercept" and v == 0.0]
        assert len(zero_coefs) > 0

    def test_serialization(self, processed_data) -> None:
        """Assert saving and reloading preserves model weights and prediction values."""
        train_df, test_df = processed_data
        model = RegularizedLinearPredictor(method="ridge", alpha=1.0)
        model.fit(train_df, train_df["daily_liters"])

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ridge_model.joblib"
            model.save(path)
            assert path.exists()

            loaded = RegularizedLinearPredictor.load(path)
            orig_preds = model.predict(test_df)
            loaded_preds = loaded.predict(test_df)
            np.testing.assert_allclose(orig_preds, loaded_preds)


class TestGLMPredictor:
    """Test suite for GLMPredictor."""

    def test_non_negativity_guarantee(self, processed_data) -> None:
        """Assert min(y_hat_GLM) > 0.0 across 1,000 synthetic extreme input samples."""
        train_df, _ = processed_data
        model_gamma = GLMPredictor(family="gamma", alpha=0.1)
        model_gamma.fit(train_df, train_df["daily_liters"])

        model_poisson = GLMPredictor(family="poisson", alpha=0.1)
        model_poisson.fit(train_df, train_df["daily_liters"])

        rng = np.random.default_rng(42)
        n_samples = 1000
        extreme_df = pd.DataFrame({
            "business_id": ["biz_extreme"] * n_samples,
            "business_type": rng.choice(
                ["FRITURA", "PICA_POLLO", "CAFETERIA", "RESTAURANTE"], size=n_samples
            ),
            "day_of_week": rng.integers(0, 7, size=n_samples),
            "num_fryers": rng.integers(0, 2, size=n_samples),
            "avg_daily_customers": rng.integers(0, 10, size=n_samples),
            "lag_7d_liters": np.zeros(n_samples),
        })

        preds_gamma = model_gamma.predict(extreme_df)
        preds_poisson = model_poisson.predict(extreme_df)

        assert len(preds_gamma) == n_samples
        assert np.min(preds_gamma) > 0.0
        assert np.min(preds_poisson) > 0.0

    def test_interaction_detection_gamma(self, processed_data) -> None:
        """Verify GLM captures positive interaction for street frituras on Saturday."""
        train_df, _ = processed_data
        model_gamma = GLMPredictor(family="gamma", alpha=0.1)
        model_gamma.fit(train_df, train_df["daily_liters"])

        coefs = model_gamma.get_coefficients()
        target_term = "business_type[FRITURA] * day_of_week[Saturday]"
        assert target_term in coefs
        assert coefs[target_term] > 0.0

    def test_summary_diagnostics(self, processed_data) -> None:
        """Verify model deviance, AIC, and feature weights are formatted in summary."""
        train_df, _ = processed_data
        model = GLMPredictor(family="gamma", alpha=0.1)
        model.fit(train_df, train_df["daily_liters"])

        summary_text = model.summary()
        assert "deviance" in summary_text.lower()
        assert "aic" in summary_text.lower()
        assert "feature weights" in summary_text.lower()
        assert model.deviance_ is not None and model.deviance_ > 0.0
        assert model.aic_ is not None and model.aic_ > 0.0

    def test_serialization(self, processed_data) -> None:
        """Assert saving and reloading preserves GLM weights and predictions."""
        train_df, test_df = processed_data
        model = GLMPredictor(family="gamma", alpha=0.1)
        model.fit(train_df, train_df["daily_liters"])

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "glm_model.joblib"
            model.save(path)
            assert path.exists()

            loaded = GLMPredictor.load(path)
            orig_preds = model.predict(test_df)
            loaded_preds = loaded.predict(test_df)
            np.testing.assert_allclose(orig_preds, loaded_preds)

    def test_evaluate_mae(self, processed_data) -> None:
        """Verify evaluate_mae computes standard positive MAE against test targets."""
        train_df, test_df = processed_data
        model = GLMPredictor(family="gamma", alpha=0.1)
        model.fit(train_df, train_df["daily_liters"])

        mae = model.evaluate_mae(test_df, test_df["daily_liters"])
        assert isinstance(mae, float)
        assert mae > 0.0
        assert mae < 20.0
