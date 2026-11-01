"""Non-linear tree ensemble predictors with synthetic pre-training and real fine-tuning."""

from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.inspection import permutation_importance

from src.ml.base import BasePredictor
from src.ml.preprocessor import FeaturePipeline


class TreeEnsemblePredictor(BasePredictor):
    """Ensemble predictor utilizing Random Forest or Histogram Gradient Boosting.

    Features two-stage synthetic pre-training and real-data adaptation via
    sample re-weighting, guaranteed non-negative predictions, and interpretability ranking.
    """

    def __init__(
        self,
        algorithm: str = "hist_gradient_boosting",
        n_estimators: int = 150,
        max_depth: int = 10,
        loss: str = "absolute_error",
        random_state: int = 42,
    ) -> None:
        """Initializes ensemble predictor.

        Args:
            algorithm: Tree ensemble algorithm ('hist_gradient_boosting' or 'random_forest').
            n_estimators: Number of boosting iterations or trees in the forest.
            max_depth: Maximum tree depth.
            loss: Loss criterion ('absolute_error', 'squared_error', or 'poisson').
            random_state: Random state seed for reproducibility.
        """
        self.algorithm = algorithm.lower().strip()
        self.n_estimators = int(n_estimators)
        self.max_depth = int(max_depth)
        self.loss = loss.lower().strip()
        self.random_state = int(random_state)

        self.pipeline_: FeaturePipeline = FeaturePipeline()
        self.model_: Optional[
            Union[HistGradientBoostingRegressor, RandomForestRegressor]
        ] = None
        self.feature_names_: List[str] = []

        self._last_X: Optional[np.ndarray] = None
        self._last_y: Optional[np.ndarray] = None

    def _init_estimator(
        self,
    ) -> Union[HistGradientBoostingRegressor, RandomForestRegressor]:
        """Creates an unfitted estimator instance according to configuration."""
        if self.algorithm in ["random_forest", "rf"]:
            criterion = self.loss
            if criterion not in ["squared_error", "absolute_error", "poisson"]:
                criterion = "squared_error"
            return RandomForestRegressor(
                n_estimators=self.n_estimators,
                max_depth=self.max_depth,
                criterion=criterion,
                random_state=self.random_state,
                min_samples_split=5,
            )
        elif self.algorithm in [
            "hist_gradient_boosting",
            "hist_gradient_boost",
            "hgb",
            "gradient_boosting",
        ]:
            hgb_loss = self.loss
            if hgb_loss not in ["squared_error", "absolute_error", "poisson"]:
                hgb_loss = "absolute_error"
            return HistGradientBoostingRegressor(
                loss=hgb_loss,
                max_iter=self.n_estimators,
                max_depth=self.max_depth,
                random_state=self.random_state,
            )
        else:
            raise ValueError(
                f"Unsupported tree ensemble algorithm '{self.algorithm}'. "
                "Must be 'hist_gradient_boosting' or 'random_forest'."
            )

    def fit(
        self,
        X: Union[pd.DataFrame, np.ndarray],
        y: Union[pd.Series, np.ndarray],
        sample_weight: Optional[np.ndarray] = None,
    ) -> "TreeEnsemblePredictor":
        """Fits preprocessing pipeline and tree ensemble on features and daily volumes.

        Args:
            X: Input features DataFrame or numpy array.
            y: Target daily volumes in liters.
            sample_weight: Optional sample weights for training loss.

        Returns:
            Fitted TreeEnsemblePredictor instance.
        """
        if isinstance(X, pd.DataFrame):
            X_mat = self.pipeline_.fit_transform(X)
            self.feature_names_ = self.pipeline_.get_feature_names_out()
        else:
            X_mat = np.asarray(X, dtype=float)
            self.feature_names_ = [f"feature_{i}" for i in range(X_mat.shape[1])]

        y_arr = np.asarray(y, dtype=float)
        if self.loss == "poisson":
            y_arr = np.clip(y_arr, 1e-4, None)

        self.model_ = self._init_estimator()
        self.model_.fit(X_mat, y_arr, sample_weight=sample_weight)

        # Retain subset of data for permutation importance calculation
        sub_size = min(500, len(X_mat))
        rng = np.random.RandomState(self.random_state)
        sub_idx = rng.choice(len(X_mat), size=sub_size, replace=False)
        self._last_X = X_mat[sub_idx]
        self._last_y = y_arr[sub_idx]

        return self

    def pretrain_and_finetune(
        self,
        X_synth: Union[pd.DataFrame, np.ndarray],
        y_synth: Union[pd.Series, np.ndarray],
        X_real: Union[pd.DataFrame, np.ndarray],
        y_real: Union[pd.Series, np.ndarray],
        real_weight_multiplier: float = 10.0,
    ) -> "TreeEnsemblePredictor":
        """Pre-trains on synthetic data and fine-tunes on real field observations.

        Employs differential sample weighting where real empirical rows are
        weighted by real_weight_multiplier (e.g. 10x) relative to synthetic rows.

        Args:
            X_synth: Synthetic training features.
            y_synth: Synthetic target volumes.
            X_real: Real empirical features.
            y_real: Real empirical target volumes.
            real_weight_multiplier: Relative importance weight assigned to real observations.

        Returns:
            Fine-tuned TreeEnsemblePredictor instance.
        """
        n_synth = len(X_synth)
        n_real = len(X_real)

        w_synth = np.ones(n_synth, dtype=float)
        w_real = np.full(n_real, float(real_weight_multiplier), dtype=float)
        weights = np.concatenate([w_synth, w_real])

        if isinstance(X_synth, pd.DataFrame) and isinstance(X_real, pd.DataFrame):
            X_combined = pd.concat([X_synth, X_real], ignore_index=True)
            y_combined = pd.concat(
                [pd.Series(y_synth), pd.Series(y_real)], ignore_index=True
            )
        else:
            X_synth_arr = np.asarray(X_synth, dtype=float)
            X_real_arr = np.asarray(X_real, dtype=float)
            X_combined = np.vstack([X_synth_arr, X_real_arr])
            y_combined = np.concatenate([
                np.asarray(y_synth, dtype=float),
                np.asarray(y_real, dtype=float),
            ])

        return self.fit(X_combined, y_combined, sample_weight=weights)

    def predict(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """Predicts non-negative daily volumes in liters/day (y >= 0.0).

        Args:
            X: Input features DataFrame or numpy array.

        Returns:
            1D numpy array of predicted volumes (liters/day).
        """
        if self.model_ is None:
            raise RuntimeError("Model must be fitted before calling predict.")

        if isinstance(X, pd.DataFrame):
            X_mat = self.pipeline_.transform(X)
        else:
            X_mat = np.asarray(X, dtype=float)

        raw = self.model_.predict(X_mat)
        return np.maximum(0.0, raw)

    def get_feature_importances(
        self, feature_names: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """Computes sorted feature importances using MDI or Permutation Importance.

        Args:
            feature_names: Optional explicit list of feature names. If None,
                retrieved from fitted pipeline or stored feature names.

        Returns:
            DataFrame with columns ['feature', 'importance'] sorted descending.
        """
        if self.model_ is None:
            raise RuntimeError(
                "Model must be fitted before computing feature importances."
            )

        if feature_names is not None:
            names = list(feature_names)
        elif self.feature_names_:
            names = list(self.feature_names_)
        elif self._last_X is not None:
            names = [f"feature_{i}" for i in range(self._last_X.shape[1])]
        else:
            names = []

        if hasattr(self.model_, "feature_importances_"):
            importances = self.model_.feature_importances_
        elif self._last_X is not None and self._last_y is not None:
            perm = permutation_importance(
                self.model_,
                self._last_X,
                self._last_y,
                n_repeats=5,
                random_state=self.random_state,
            )
            importances = perm.importances_mean
        else:
            importances = np.zeros(len(names))

        if len(names) != len(importances):
            names = [f"feature_{i}" for i in range(len(importances))]

        df_imp = pd.DataFrame({"feature": names, "importance": importances})
        return df_imp.sort_values("importance", ascending=False).reset_index(
            drop=True
        )
