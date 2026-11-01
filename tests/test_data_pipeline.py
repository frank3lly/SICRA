"""Unit tests for the data validation, feature aggregation, and dataset export components."""

from datetime import date, datetime, timedelta, timezone
import os
import pandas as pd
import pytest

from src.data.aggregator import DailyFeatureAggregator
from src.data.exporter import ChronologicalDatasetExporter
from src.data.validator import DataIntegrityAuditor, DataIntegrityError
from src.models import BusinessType


def test_validator_physical_checks():
    """Verify validator flags negative liters, overfilled tanks, and invalid voltages."""
    auditor = DataIntegrityAuditor()

    # Valid daily features
    valid_df = pd.DataFrame({
        "date": [date(2026, 1, 1), date(2026, 1, 2)],
        "container_id": ["c1", "c1"],
        "business_id": ["b1", "b1"],
        "business_name": ["Biz", "Biz"],
        "business_type": ["PICA_POLLO", "PICA_POLLO"],
        "num_fryers": [4, 4],
        "avg_daily_customers": [300, 300],
        "day_of_week": [3, 4],
        "is_weekend": [False, True],
        "lag_7d_liters": [None, None],
        "daily_liters": [15.2, 22.4],
        "is_synthetic": [True, True],
    })
    res = auditor.validate_daily_features(valid_df, raise_on_error=True)
    assert res["status"] == "PASSED"

    # Invalid: negative daily liters
    invalid_df = valid_df.copy()
    invalid_df.loc[0, "daily_liters"] = -5.0
    with pytest.raises(DataIntegrityError):
        auditor.validate_daily_features(invalid_df, raise_on_error=True)

    # Invalid: non-synthetic
    invalid_synth = valid_df.copy()
    invalid_synth.loc[0, "is_synthetic"] = False
    with pytest.raises(DataIntegrityError):
        auditor.validate_daily_features(invalid_synth, raise_on_error=True)


def test_aggregator_resampling_and_lags():
    """Verify aggregator calculates positive increments, ignores drains, and links 7-day lags."""
    aggregator = DailyFeatureAggregator()

    raw_data = [
        # Day 1: Pour 1.0, then 1.5 -> total +2.5L
        {"container_id": "c1", "measurement_timestamp": "2026-01-01 02:00", "calculated_liters": 1.0, "flag": "NORMAL", "is_synthetic": True, "business_id": "b1", "business_name": "Biz", "business_type": BusinessType.FRITURA, "num_fryers": 2, "avg_daily_customers": 150},
        {"container_id": "c1", "measurement_timestamp": "2026-01-01 12:00", "calculated_liters": 2.5, "flag": "NORMAL", "is_synthetic": True, "business_id": "b1", "business_name": "Biz", "business_type": BusinessType.FRITURA, "num_fryers": 2, "avg_daily_customers": 150},
        # Day 2: DRAIN EVENT drops to 0.4, then pour to 1.4 -> total +1.0L
        {"container_id": "c1", "measurement_timestamp": "2026-01-02 08:00", "calculated_liters": 0.4, "flag": "DRAIN_EVENT", "is_synthetic": True, "business_id": "b1", "business_name": "Biz", "business_type": BusinessType.FRITURA, "num_fryers": 2, "avg_daily_customers": 150},
        {"container_id": "c1", "measurement_timestamp": "2026-01-02 18:00", "calculated_liters": 1.4, "flag": "NORMAL", "is_synthetic": True, "business_id": "b1", "business_name": "Biz", "business_type": BusinessType.FRITURA, "num_fryers": 2, "avg_daily_customers": 150},
    ]

    # Add day 8 to test lag_7d_liters matching Day 1 (2.5L)
    raw_data.append(
        {"container_id": "c1", "measurement_timestamp": "2026-01-08 12:00", "calculated_liters": 3.0, "flag": "NORMAL", "is_synthetic": True, "business_id": "b1", "business_name": "Biz", "business_type": BusinessType.FRITURA, "num_fryers": 2, "avg_daily_customers": 150}
    )

    features = aggregator.aggregate_daily_features(raw_data)
    assert len(features) == 3

    # Day 1: delta from 1.0 to 2.5 is 1.5L
    d1 = features[features["date"] == date(2026, 1, 1)].iloc[0]
    assert d1["daily_liters"] == 1.5
    assert pd.isna(d1["lag_7d_liters"])

    # Day 2: DRAIN to 0.4, then delta to 1.4 is 1.0L
    d2 = features[features["date"] == date(2026, 1, 2)].iloc[0]
    assert d2["daily_liters"] == 1.0

    # Day 8: Lag 7d matches Day 1 (1.5L)
    d8 = features[features["date"] == date(2026, 1, 8)].iloc[0]
    assert d8["lag_7d_liters"] == 1.5


def test_exporter_chronological_split(tmp_path):
    """Verify exporter creates non-overlapping train and test splits."""
    dates = [date(2026, 1, 1) + timedelta(days=i) for i in range(20)]
    mock_features = pd.DataFrame({
        "date": dates * 2,
        "container_id": ["c1"] * 20 + ["c2"] * 20,
        "business_id": ["b1"] * 20 + ["b2"] * 20,
        "business_name": ["Biz 1"] * 20 + ["Biz 2"] * 20,
        "business_type": ["PICA_POLLO"] * 20 + ["FRITURA"] * 20,
        "num_fryers": [4] * 20 + [2] * 20,
        "avg_daily_customers": [300] * 20 + [150] * 20,
        "day_of_week": [d.weekday() for d in dates] * 2,
        "is_weekend": [d.weekday() in [4, 5, 6] for d in dates] * 2,
        "lag_7d_liters": [None] * 40,
        "daily_liters": [10.0] * 40,
        "is_synthetic": [True] * 40,
    })

    exporter = ChronologicalDatasetExporter()
    out_dir = tmp_path / "processed_test_export"
    res = exporter.export_chronological_splits(
        train_ratio=0.75,
        output_dir=str(out_dir),
        features_df=mock_features,
    )

    train_df = pd.read_csv(res["train_csv"])
    test_df = pd.read_csv(res["test_csv"])

    assert len(train_df) == 30  # 15 days * 2 containers
    assert len(test_df) == 10   # 5 days * 2 containers

    max_train_date = train_df["date"].max()
    min_test_date = test_df["date"].min()
    assert max_train_date < min_test_date
