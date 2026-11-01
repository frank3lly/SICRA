"""Data validation, feature aggregation, and dataset export package."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.data.aggregator import DailyFeatureAggregator
    from src.data.exporter import ChronologicalDatasetExporter
    from src.data.validator import DataIntegrityAuditor, DataIntegrityError

__all__ = [
    "DataIntegrityAuditor",
    "DataIntegrityError",
    "DailyFeatureAggregator",
    "ChronologicalDatasetExporter",
]


def __getattr__(name: str):
    if name in ("DataIntegrityAuditor", "DataIntegrityError"):
        from src.data import validator
        return getattr(validator, name)
    if name == "DailyFeatureAggregator":
        from src.data import aggregator
        return getattr(aggregator, name)
    if name == "ChronologicalDatasetExporter":
        from src.data import exporter
        return getattr(exporter, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
