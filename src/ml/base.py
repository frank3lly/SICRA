"""Abstract base predictor class for SICRA ML models."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union
import joblib
import numpy as np
import pandas as pd


class BasePredictor(ABC):
    """Abstract base class standardizing prediction and evaluation interfaces."""

    @abstractmethod
    def fit(self, X: pd.DataFrame, y: pd.Series) -> "BasePredictor":
        """Fits model parameters on historical features and daily volumes.

        Args:
            X: Feature matrix or historical records DataFrame.
            y: Target daily volumes in liters.

        Returns:
            Fitted predictor instance.
        """
        pass

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Returns non-negative predicted volumes in liters/day.

        Args:
            X: Input features DataFrame.

        Returns:
            1D numpy array of predicted volumes (liters/day), strictly >= 0.0.
        """
        pass

    def evaluate_mae(self, X: pd.DataFrame, y: pd.Series) -> float:
        """Computes Mean Absolute Error against ground truth.

        Args:
            X: Input features DataFrame.
            y: Ground truth daily volumes.

        Returns:
            Mean Absolute Error in liters/day.
        """
        preds = self.predict(X)
        y_true = np.asarray(y, dtype=float)
        return float(np.mean(np.abs(y_true - preds)))

    def save(self, path: Union[str, Path]) -> None:
        """Serializes the predictor instance to disk via joblib.

        Args:
            path: Destination file path.
        """
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, dest)

    @classmethod
    def load(cls, path: Union[str, Path]) -> "BasePredictor":
        """Loads a serialized predictor instance from disk via joblib.

        Args:
            path: Path to serialized model file.

        Returns:
            Deserialized predictor instance.
        """
        src = Path(path)
        if not src.exists():
            raise FileNotFoundError(f"Model file not found at: {src}")
        loaded = joblib.load(src)
        return loaded
