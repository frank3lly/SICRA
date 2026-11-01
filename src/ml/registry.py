"""Model registry for versioning, metadata serialization, and production deployment."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import joblib

from src.ml.base import BasePredictor


class ModelRegistry:
    """Manages persistence, metadata auditing, and loading of production models."""

    def __init__(self, registry_dir: Union[str, Path] = "models/production") -> None:
        """Initializes model registry.

        Args:
            registry_dir: Path to directory where production models and manifests reside.
        """
        self.registry_dir = Path(registry_dir)

    @property
    def model_path(self) -> Path:
        """Path to primary production model binary."""
        return self.registry_dir / "model.joblib"

    @property
    def fallback_model_path(self) -> Path:
        """Path to secondary baseline fallback model binary."""
        return self.registry_dir / "fallback_model.joblib"

    @property
    def metadata_path(self) -> Path:
        """Path to production metadata JSON manifest."""
        return self.registry_dir / "metadata.json"

    def is_production_ready(self) -> bool:
        """Checks if registry contains a deployed model and valid metadata manifest."""
        return self.model_path.exists() and self.metadata_path.exists()

    def register_model(
        self,
        model: BasePredictor,
        metadata: Dict[str, Any],
        fallback_model: Optional[BasePredictor] = None,
    ) -> Path:
        """Serializes model binary, optional fallback, and metadata manifest to disk.

        Args:
            model: Fitted active predictor instance.
            metadata: Metadata dictionary including algorithm, performance, and features.
            fallback_model: Optional baseline predictor for operational safety fallback.

        Returns:
            Path to registry directory.
        """
        self.registry_dir.mkdir(parents=True, exist_ok=True)

        # 1. Save primary model binary
        joblib.dump(model, self.model_path)

        # 2. Save optional fallback model binary
        if fallback_model is not None:
            joblib.dump(fallback_model, self.fallback_model_path)

        # 3. Enrich and save metadata manifest
        meta = dict(metadata)
        if "created_at" not in meta:
            meta["created_at"] = datetime.now(timezone.utc).isoformat()

        with open(self.metadata_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        return self.registry_dir

    def load_production_model(self) -> Tuple[BasePredictor, Dict[str, Any]]:
        """Loads active production model and corresponding metadata manifest.

        Returns:
            Tuple of (model_instance, metadata_dict).

        Raises:
            FileNotFoundError: If model.joblib or metadata.json are missing.
        """
        if not self.model_path.exists():
            raise FileNotFoundError(f"Production model not found at: {self.model_path}")
        if not self.metadata_path.exists():
            raise FileNotFoundError(f"Metadata manifest not found at: {self.metadata_path}")

        model = joblib.load(self.model_path)
        with open(self.metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        return model, metadata

    def load_fallback_model(self) -> Optional[BasePredictor]:
        """Loads fallback baseline model if available.

        Returns:
            Fallback BasePredictor or None.
        """
        if self.fallback_model_path.exists():
            return joblib.load(self.fallback_model_path)
        return None

    def load_metadata(self) -> Dict[str, Any]:
        """Loads and returns metadata manifest.

        Returns:
            Metadata dictionary.
        """
        if not self.metadata_path.exists():
            raise FileNotFoundError(f"Metadata manifest not found at: {self.metadata_path}")
        with open(self.metadata_path, "r", encoding="utf-8") as f:
            return json.load(f)
