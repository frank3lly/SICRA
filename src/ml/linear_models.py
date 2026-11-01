"""Regularized linear regression (Ridge, Lasso) and Generalized Linear Models (Gamma, Poisson)."""

from typing import Any, Dict, Optional, Union
import numpy as np
import pandas as pd
from sklearn.linear_model import GammaRegressor, Lasso, PoissonRegressor, Ridge

from src.ml.base import BasePredictor
from src.ml.preprocessor import FeaturePipeline


class RegularizedLinearPredictor(BasePredictor):
    """Linear regression model with L1 (Lasso) or L2 (Ridge) penalty.

    Boundary Safeguard: All volume predictions pass through a zero-floor threshold:
    y_clipped = max(0.0, y_hat).
    """

    def __init__(self, method: str = "ridge", alpha: float = 1.0) -> None:
        """Initializes regularized linear predictor.

        Args:
            method: Regularization penalty type ('ridge' or 'lasso').
            alpha: Regularization strength parameter (must be positive).
        """
        self.method = method.lower().strip()
        self.alpha = float(alpha)
        self.pipeline_: FeaturePipeline = FeaturePipeline()
        self.model_: Optional[Union[Ridge, Lasso]] = None
        self.feature_names_: list[str] = []

    def fit(
        self, X: pd.DataFrame, y: pd.Series
    ) -> "RegularizedLinearPredictor":
        """Fits preprocessing pipeline and regularized linear model.

        Args:
            X: Input features DataFrame.
            y: Target daily volumes in liters.

        Returns:
            Fitted RegularizedLinearPredictor instance.
        """
        X_mat = self.pipeline_.fit_transform(X)
        self.feature_names_ = self.pipeline_.get_feature_names_out()
        y_arr = np.asarray(y, dtype=float)

        if self.method == "lasso":
            self.model_ = Lasso(
                alpha=self.alpha,
                random_state=42,
                max_iter=10000,
            )
        elif self.method == "ridge":
            self.model_ = Ridge(
                alpha=self.alpha,
                random_state=42,
            )
        else:
            raise ValueError(
                f"Unsupported regularization method '{self.method}'. Must be 'ridge' or 'lasso'."
            )

        self.model_.fit(X_mat, y_arr)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predicts non-negative daily volumes in liters/day.

        Args:
            X: Input features DataFrame.

        Returns:
            1D numpy array of clipped predictions (strictly >= 0.0).
        """
        if self.model_ is None:
            raise RuntimeError("Model must be fitted before calling predict.")

        X_mat = self.pipeline_.transform(X)
        raw_preds = self.model_.predict(X_mat)
        return np.maximum(0.0, raw_preds)

    def get_coefficients(self) -> Dict[str, float]:
        """Returns mapping of feature names to estimated regression weights.

        Returns:
            Dictionary containing coefficients for each feature and the intercept.
        """
        if self.model_ is None:
            raise RuntimeError("Model must be fitted before accessing coefficients.")

        coef_dict = {
            name: float(coef)
            for name, coef in zip(self.feature_names_, self.model_.coef_)
        }
        coef_dict["intercept"] = float(self.model_.intercept_)
        return coef_dict


class GLMPredictor(BasePredictor):
    """Generalized Linear Model with log-link and Gamma or Poisson dispersion families.

    Assures physical non-negativity: y_hat = exp(X beta) > 0.
    """

    def __init__(self, family: str = "gamma", alpha: float = 0.1) -> None:
        """Initializes GLM predictor.

        Args:
            family: Distribution family ('gamma' or 'poisson').
            alpha: L2 regularization strength parameter.
        """
        self.family = family.lower().strip()
        self.alpha = float(alpha)
        self.pipeline_: FeaturePipeline = FeaturePipeline()
        self.model_: Optional[Union[GammaRegressor, PoissonRegressor]] = None
        self.feature_names_: list[str] = []
        self.deviance_: Optional[float] = None
        self.aic_: Optional[float] = None
        self.feature_weights_: Dict[str, float] = {}

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "GLMPredictor":
        """Fits preprocessing pipeline and GLM estimator.

        Args:
            X: Input features DataFrame.
            y: Target daily volumes in liters.

        Returns:
            Fitted GLMPredictor instance.
        """
        X_mat = self.pipeline_.fit_transform(X)
        self.feature_names_ = self.pipeline_.get_feature_names_out()

        # Non-negative target safeguard: Gamma requires strictly positive y (> 0)
        y_arr = np.clip(np.asarray(y, dtype=float), 1e-4, None)

        if self.family == "gamma":
            self.model_ = GammaRegressor(
                alpha=self.alpha,
                max_iter=3000,
            )
        elif self.family == "poisson":
            self.model_ = PoissonRegressor(
                alpha=self.alpha,
                max_iter=3000,
            )
        else:
            raise ValueError(
                f"Unsupported GLM family '{self.family}'. Must be 'gamma' or 'poisson'."
            )

        self.model_.fit(X_mat, y_arr)

        # Compute in-sample deviance and AIC
        mu = np.clip(self.model_.predict(X_mat), 1e-6, None)
        n = len(y_arr)
        k = len(self.model_.coef_) + 1

        if self.family == "gamma":
            # Unit deviance for Gamma: 2 * (-ln(y/mu) + (y - mu)/mu)
            dev_i = 2.0 * (-np.log(y_arr / mu) + (y_arr - mu) / mu)
        else:
            # Unit deviance for Poisson: 2 * (y * ln(y/mu) - (y - mu))
            dev_i = 2.0 * (y_arr * np.log(y_arr / mu) - (y_arr - mu))

        self.deviance_ = float(np.sum(dev_i))
        self.aic_ = float(self.deviance_ + 2.0 * k)

        self.feature_weights_ = {
            name: float(coef)
            for name, coef in zip(self.feature_names_, self.model_.coef_)
        }
        self.feature_weights_["intercept"] = float(self.model_.intercept_)

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Returns strictly positive predicted daily volumes in liters/day (y > 0).

        Args:
            X: Input features DataFrame.

        Returns:
            1D numpy array of predicted daily volumes, strictly > 0.0.
        """
        if self.model_ is None:
            raise RuntimeError("Model must be fitted before calling predict.")

        X_mat = self.pipeline_.transform(X)
        preds = self.model_.predict(X_mat)
        return np.maximum(1e-6, preds)

    def get_coefficients(self) -> Dict[str, float]:
        """Returns mapping of feature names to estimated GLM weights."""
        if not self.feature_weights_:
            raise RuntimeError("Model must be fitted before accessing coefficients.")
        return dict(self.feature_weights_)

    def summary(self) -> str:
        """Returns model deviance, AIC, and feature weights report.

        Returns:
            Formatted diagnostic text summary.
        """
        if self.deviance_ is None or self.aic_ is None:
            raise RuntimeError("Model must be fitted before generating summary.")

        lines = [
            "=" * 78,
            "Generalized Linear Model (GLM) Summary",
            "=" * 78,
            f"Family:                  {self.family.capitalize()} (Log Link)",
            f"Regularization Alpha:    {self.alpha}",
            f"Model Deviance:          {self.deviance_:.4f}",
            f"Akaike Criterion (AIC):  {self.aic_:.4f}",
            "-" * 78,
            "Feature Weights (Log Scale):",
        ]

        lines.append(f"  {'intercept':<45} : {self.feature_weights_['intercept']:>10.4f}")
        for name in self.feature_names_:
            w = self.feature_weights_.get(name, 0.0)
            lines.append(f"  {name:<45} : {w:>10.4f}")

        lines.append("=" * 78)
        return "\n".join(lines)
