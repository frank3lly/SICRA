"""Command-line interface for training, chronological evaluation, and model registry promotion."""

import argparse
from datetime import datetime, timezone
import logging
from pathlib import Path
import sys
from typing import Any, Dict
import pandas as pd

from src.ml.base import BasePredictor
from src.ml.baselines import SeasonalNaivePredictor
from src.ml.ensemble_models import TreeEnsemblePredictor
from src.ml.evaluator import ChronologicalEvaluator, evaluate_golden_rule
from src.ml.linear_models import GLMPredictor, RegularizedLinearPredictor
from src.ml.registry import ModelRegistry

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sicra.ml.cli")


def build_candidate_model(
    model_type: str,
    family: str = "gamma",
    alpha: float = 0.1,
    random_state: int = 42,
) -> BasePredictor:
    """Instantiates candidate predictor according to CLI parameters.

    Args:
        model_type: Model family identifier.
        family: GLM distribution family.
        alpha: Regularization strength.
        random_state: Random state seed.

    Returns:
        Unfitted BasePredictor instance.
    """
    m_type = model_type.lower().strip()
    if m_type == "glm":
        return GLMPredictor(family=family, alpha=alpha)
    elif m_type in ["ridge", "lasso"]:
        return RegularizedLinearPredictor(method=m_type, alpha=alpha)
    elif m_type in ["random_forest", "rf"]:
        return TreeEnsemblePredictor(
            algorithm="random_forest", random_state=random_state
        )
    elif m_type in ["hist_gradient_boosting", "hgb", "gradient_boosting"]:
        return TreeEnsemblePredictor(
            algorithm="hist_gradient_boosting", random_state=random_state
        )
    else:
        raise ValueError(
            f"Unknown model type '{model_type}'. Choose from: "
            "glm, ridge, lasso, random_forest, hist_gradient_boosting."
        )


def main() -> int:
    """CLI execution entrypoint."""
    parser = argparse.ArgumentParser(
        description="SICRA Predictive Model Training and Evaluation Pipeline"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/processed",
        help="Directory containing chronological train and test datasets.",
    )
    parser.add_argument(
        "--model-type",
        type=str,
        default="glm",
        choices=["glm", "ridge", "lasso", "random_forest", "hist_gradient_boosting"],
        help="Machine learning algorithm family.",
    )
    parser.add_argument(
        "--family",
        type=str,
        default="gamma",
        choices=["gamma", "poisson"],
        help="GLM distribution family (applies only to --model-type glm).",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.1,
        help="Regularization strength parameter.",
    )
    parser.add_argument(
        "--enforce-r04",
        action="store_true",
        default=False,
        help="Enforce Golden Rule decision gate before registry promotion.",
    )
    parser.add_argument(
        "--save-dir",
        type=str,
        default="models/production",
        help="Destination directory for model artifacts.",
    )

    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    train_path = data_dir / "train_chronological.csv"
    test_path = data_dir / "test_chronological.csv"

    if not train_path.exists() or not test_path.exists():
        logger.error("Dataset files not found in: %s", data_dir)
        return 1

    logger.info("Loading chronological datasets from %s...", data_dir)
    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)
    logger.info("Train rows: %d | Test rows: %d", len(train_df), len(test_df))

    # Build models
    candidate = build_candidate_model(
        model_type=args.model_type,
        family=args.family,
        alpha=args.alpha,
    )
    baseline = SeasonalNaivePredictor()

    # Chronological evaluation
    evaluator = ChronologicalEvaluator()
    golden_rule, cand_metrics, base_metrics = evaluator.compare_models(
        candidate_model=candidate,
        baseline_model=baseline,
        train_df=train_df,
        test_df=test_df,
    )

    # Print summary report
    print("\n" + "=" * 60)
    print("CHRONOLOGICAL MODEL EVALUATION REPORT")
    print("=" * 60)
    print(f"Candidate Algorithm:   {candidate.__class__.__name__}")
    print(f"Candidate Test MAE:    {cand_metrics['mae']:.4f} L/day")
    print(f"Candidate Test RMSE:   {cand_metrics['rmse']:.4f} L/day")
    print(f"Candidate Test R2:     {cand_metrics['r2']:.4f}")
    print("-" * 60)
    print(f"Baseline Benchmark:    SeasonalNaivePredictor")
    print(f"Baseline Test MAE:     {base_metrics['mae']:.4f} L/day")
    print(f"Baseline Test RMSE:    {base_metrics['rmse']:.4f} L/day")
    print(f"Baseline Test R2:      {base_metrics['r2']:.4f}")
    print("-" * 60)
    print(f"Improvement over Base: {golden_rule.improvement_pct:+.2f}%")
    print(f"Golden Rule (R-04):    {'PASSED' if golden_rule.passed else 'FAILED'}")
    print(f"Active Promotion:      {golden_rule.active_model_type}")
    print("=" * 60 + "\n")

    # Determine promotion model
    registry = ModelRegistry(args.save_dir)
    if args.enforce_r04 and not golden_rule.passed:
        logger.warning(
            "Golden Rule check failed: Promoting Seasonal Naive baseline fallback to %s",
            args.save_dir,
        )
        active_model = baseline
        deployed_name = "SeasonalNaivePredictor"
    else:
        logger.info("Promoting candidate %s to %s", candidate.__class__.__name__, args.save_dir)
        active_model = candidate
        deployed_name = candidate.__class__.__name__

    metadata: Dict[str, Any] = {
        "model_id": f"{args.model_type}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        "algorithm": deployed_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "r04_passed": golden_rule.passed,
        "test_mae": cand_metrics["mae"],
        "baseline_mae": base_metrics["mae"],
        "improvement_pct": golden_rule.improvement_pct,
        "train_records_count": len(train_df),
        "hyperparameters": {
            "model_type": args.model_type,
            "family": args.family if args.model_type == "glm" else None,
            "alpha": args.alpha,
        },
        "features": (
            getattr(candidate, "feature_names_", [])
            if hasattr(candidate, "feature_names_")
            else []
        ),
    }

    registry.register_model(
        model=active_model,
        metadata=metadata,
        fallback_model=baseline,
    )
    logger.info("Successfully registered production artifacts in: %s", args.save_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
