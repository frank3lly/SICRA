"""Chronological cross-validation, temporal split evaluation, and Golden Rule decision engine."""

from dataclasses import asdict, dataclass
import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

from src.ml.base import BasePredictor
from src.ml.baselines import SeasonalNaivePredictor

logger = logging.getLogger(__name__)


@dataclass
class GoldenRuleResult:
    """Represents outcome of Golden Rule comparison (Requirement R-04)."""

    passed: bool
    candidate_mae: float
    baseline_mae: float
    improvement_pct: float
    active_model_type: str  # 'CANDIDATE' or 'SEASONAL_NAIVE_FALLBACK'

    def to_dict(self) -> Dict[str, Any]:
        """Converts result to serializable dictionary."""
        return asdict(self)


def evaluate_golden_rule(
    candidate_mae: float, baseline_mae: float
) -> GoldenRuleResult:
    """Evaluates whether candidate model outperforms baseline (Requirement R-04).

    Rule: Candidate model is accepted for production if and only if:
        MAE_candidate < MAE_baseline

    If rejected, triggers automatic fallback to Seasonal Naive baseline.

    Args:
        candidate_mae: Mean Absolute Error of candidate model.
        baseline_mae: Mean Absolute Error of benchmark baseline model.

    Returns:
        GoldenRuleResult detailing verification outcome.
    """
    r04_passed = bool(candidate_mae < baseline_mae)
    if baseline_mae > 0.0:
        improvement_pct = float(((baseline_mae - candidate_mae) / baseline_mae) * 100.0)
    else:
        improvement_pct = 0.0

    if not r04_passed:
        logger.warning(
            "[ALERT-RT01] Candidate model MAE (%.3f) >= Baseline (%.3f). Reverting to Seasonal Naive fallback.",
            candidate_mae,
            baseline_mae,
        )

    return GoldenRuleResult(
        passed=r04_passed,
        candidate_mae=float(candidate_mae),
        baseline_mae=float(baseline_mae),
        improvement_pct=float(improvement_pct),
        active_model_type="CANDIDATE" if r04_passed else "SEASONAL_NAIVE_FALLBACK",
    )


class ChronologicalEvaluator:
    """Evaluates predictive models using strict chronological validation without data leakage."""

    def __init__(self, time_col: str = "date", target_col: str = "daily_liters") -> None:
        """Initializes evaluator.

        Args:
            time_col: Name of chronological date/timestamp column.
            target_col: Name of target daily volume column.
        """
        self.time_col = time_col
        self.target_col = target_col

    def get_chronological_splits(
        self, df: pd.DataFrame, n_splits: int = 5
    ) -> List[Tuple[np.ndarray, np.ndarray]]:
        """Generates expanding chronological splits ensuring train timestamps strictly precede validation.

        Args:
            df: Input DataFrame.
            n_splits: Number of rolling origin splits.

        Returns:
            List of (train_indices, val_indices) index arrays.
        """
        sorted_df = df.sort_values(self.time_col).reset_index(drop=True)
        unique_dates = sorted_df[self.time_col].drop_duplicates().sort_values().to_numpy()

        if len(unique_dates) < n_splits + 1:
            # Fallback to standard row-level TimeSeriesSplit
            tscv = TimeSeriesSplit(n_splits=n_splits)
            return list(tscv.split(sorted_df))

        tscv = TimeSeriesSplit(n_splits=n_splits)
        splits = []
        for train_date_idx, val_date_idx in tscv.split(unique_dates):
            train_dates = set(unique_dates[train_date_idx])
            val_dates = set(unique_dates[val_date_idx])

            train_mask = sorted_df[self.time_col].isin(train_dates)
            val_mask = sorted_df[self.time_col].isin(val_dates)

            train_indices = sorted_df.index[train_mask].to_numpy()
            val_indices = sorted_df.index[val_mask].to_numpy()
            splits.append((train_indices, val_indices))

        return splits

    def evaluate_metrics(
        self, y_true: np.ndarray, y_pred: np.ndarray
    ) -> Dict[str, float]:
        """Computes MAE, RMSE, and R-squared.

        Args:
            y_true: Ground truth target array.
            y_pred: Predicted target array.

        Returns:
            Dictionary with 'mae', 'rmse', and 'r2'.
        """
        y_t = np.asarray(y_true, dtype=float)
        y_p = np.asarray(y_pred, dtype=float)

        mae = float(np.mean(np.abs(y_t - y_p)))
        mse = float(np.mean((y_t - y_p) ** 2))
        rmse = float(np.sqrt(mse))

        ss_tot = float(np.sum((y_t - np.mean(y_t)) ** 2))
        ss_res = float(np.sum((y_t - y_p) ** 2))
        r2 = float(1.0 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0

        return {"mae": mae, "rmse": rmse, "r2": r2}

    def evaluate_split(
        self,
        model: BasePredictor,
        train_df: pd.DataFrame,
        test_df: pd.DataFrame,
    ) -> Dict[str, float]:
        """Fits model on training set and computes metrics on held-out test set.

        Args:
            model: Predictive model implementing BasePredictor.
            train_df: Chronological training partition.
            test_df: Chronological test partition.

        Returns:
            Dictionary of test metrics.
        """
        y_train = train_df[self.target_col]
        y_test = test_df[self.target_col]

        model.fit(train_df, y_train)
        preds = model.predict(test_df)
        return self.evaluate_metrics(y_test.to_numpy(), preds)

    def cross_validate(
        self,
        model: BasePredictor,
        df: pd.DataFrame,
        n_splits: int = 5,
    ) -> Dict[str, Any]:
        """Performs chronological rolling-origin cross-validation without future leakage.

        Args:
            model: Predictive model instance to evaluate.
            df: Historical dataset.
            n_splits: Number of time series splits.

        Returns:
            Dictionary containing fold metrics and aggregated means.
        """
        sorted_df = df.sort_values(self.time_col).reset_index(drop=True)
        splits = self.get_chronological_splits(sorted_df, n_splits=n_splits)

        fold_maes: List[float] = []
        fold_rmses: List[float] = []
        fold_r2s: List[float] = []

        for fold_idx, (train_idx, val_idx) in enumerate(splits):
            train_split = sorted_df.iloc[train_idx]
            val_split = sorted_df.iloc[val_idx]

            # Fit model on training window
            model.fit(train_split, train_split[self.target_col])
            val_preds = model.predict(val_split)
            metrics = self.evaluate_metrics(
                val_split[self.target_col].to_numpy(), val_preds
            )

            fold_maes.append(metrics["mae"])
            fold_rmses.append(metrics["rmse"])
            fold_r2s.append(metrics["r2"])

        return {
            "n_splits": n_splits,
            "mean_mae": float(np.mean(fold_maes)),
            "std_mae": float(np.std(fold_maes)),
            "mean_rmse": float(np.mean(fold_rmses)),
            "mean_r2": float(np.mean(fold_r2s)),
            "fold_maes": fold_maes,
            "fold_rmses": fold_rmses,
            "fold_r2s": fold_r2s,
        }

    def compare_models(
        self,
        candidate_model: BasePredictor,
        baseline_model: BasePredictor,
        train_df: pd.DataFrame,
        test_df: pd.DataFrame,
    ) -> Tuple[GoldenRuleResult, Dict[str, float], Dict[str, float]]:
        """Fits and compares candidate against baseline on held-out test data.

        Args:
            candidate_model: Model candidate being evaluated.
            baseline_model: Baseline reference model (e.g. SeasonalNaivePredictor).
            train_df: Chronological training partition.
            test_df: Chronological test partition.

        Returns:
            Tuple of (GoldenRuleResult, candidate_metrics, baseline_metrics).
        """
        cand_metrics = self.evaluate_split(candidate_model, train_df, test_df)
        base_metrics = self.evaluate_split(baseline_model, train_df, test_df)

        golden_rule = evaluate_golden_rule(
            candidate_mae=cand_metrics["mae"],
            baseline_mae=base_metrics["mae"],
        )

        return golden_rule, cand_metrics, base_metrics
