"""Machine Learning module for SICRA predictive models."""

from src.ml.base import BasePredictor
from src.ml.baselines import SeasonalNaivePredictor
from src.ml.ensemble_models import TreeEnsemblePredictor
from src.ml.evaluator import (
    ChronologicalEvaluator,
    GoldenRuleResult,
    evaluate_golden_rule,
)
from src.ml.inference import InferenceEngine
from src.ml.linear_models import GLMPredictor, RegularizedLinearPredictor
from src.ml.preprocessor import FeaturePipeline
from src.ml.rate_estimator import LoadCellRateEstimator
from src.ml.registry import ModelRegistry

__all__ = [
    "BasePredictor",
    "SeasonalNaivePredictor",
    "LoadCellRateEstimator",
    "FeaturePipeline",
    "RegularizedLinearPredictor",
    "GLMPredictor",
    "TreeEnsemblePredictor",
    "ChronologicalEvaluator",
    "GoldenRuleResult",
    "evaluate_golden_rule",
    "ModelRegistry",
    "InferenceEngine",
]
