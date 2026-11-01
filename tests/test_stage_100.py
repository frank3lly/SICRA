"""Integration test certifying the complete closure and definition of done for Stage 100."""

import json
import os
import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.data.aggregator import DailyFeatureAggregator
from src.data.exporter import ChronologicalDatasetExporter
from src.data.validator import DataIntegrityAuditor
from src.database.seed import seed_database
from src.database.session import get_engine, get_session_factory
from src.models import (
    Base,
    Business,
    Container,
    ContainerStatus,
    Telemetry,
)
from src.simulation.engine import MonteCarloSimulator


@pytest.fixture
def stage_100_db(tmp_path):
    """File-backed isolated database engine with initial schema for Stage 100 verification."""
    db_file = tmp_path / "stage_100_eval.db"
    eng = get_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)


def test_schema_creation_and_foreign_keys(stage_100_db):
    """Criterion 1: Verifies that tables instantiate correctly with SQLite pragmas enabled."""
    inspector = inspect(stage_100_db)
    tables = set(inspector.get_table_names())
    expected = {
        "businesses",
        "containers",
        "telemetries",
        "predictions",
        "alerts",
        "collection_routes",
        "users",
    }
    assert expected.issubset(tables), f"Missing tables: {expected - tables}"

    # Verify SQLite foreign key pragma
    with stage_100_db.connect() as conn:
        pragma_val = conn.execute(text("PRAGMA foreign_keys")).scalar()
        assert pragma_val == 1

    # Verify foreign key constraint rejects orphaned containers
    session_factory = get_session_factory(stage_100_db)
    with session_factory() as session:
        orphan = Container(
            business_id="non_existent_uuid",
            device_token="tok_orphan_100",
            capacity_liters=50.0,
        )
        session.add(orphan)
        with pytest.raises(IntegrityError):
            session.commit()


def test_dominican_seed_idempotency_and_completeness(stage_100_db):
    """Criterion 2: Runs the seed script twice and asserts all pilot businesses and containers are present."""
    # First execution (reset=True)
    stats1 = seed_database(target_engine=stage_100_db, reset=True, quiet=True)
    assert stats1["businesses_created"] == 11
    assert stats1["containers_created"] == 11

    session_factory = get_session_factory(stage_100_db)
    with session_factory() as session:
        businesses = session.query(Business).all()
        assert len(businesses) == 11
        for biz in businesses:
            assert "San Pedro de Macorís" in biz.city or "San Pedro de Macorís" in biz.address
            assert 18.40 <= biz.latitude <= 18.50
            assert -69.35 <= biz.longitude <= -69.25
            assert len(biz.containers) == 1
            c = biz.containers[0]
            assert c.status == ContainerStatus.ACTIVE
            assert c.capacity_liters in [20.0, 50.0, 100.0]

    # Second execution (idempotency check)
    stats2 = seed_database(target_engine=stage_100_db, reset=False, quiet=True)
    assert stats2["businesses_created"] == 0
    assert stats2["businesses_skipped"] == 11
    assert stats2["containers_created"] == 0
    assert stats2["containers_skipped"] == 11


def test_monte_carlo_generator_reproducibility(stage_100_db):
    """Criterion 3: Asserts that identical seeds yield identical simulation outputs."""
    seed_database(target_engine=stage_100_db, reset=True, quiet=True)
    session_factory = get_session_factory(stage_100_db)

    with session_factory() as session:
        container = session.query(Container).first()
        assert container is not None

        sim1 = MonteCarloSimulator(seed=42)
        records1 = sim1.simulate_business_timeline(container, start_date=container.created_at, days=30, interval_hours=2)

        sim2 = MonteCarloSimulator(seed=42)
        records2 = sim2.simulate_business_timeline(container, start_date=container.created_at, days=30, interval_hours=2)

        assert len(records1) == len(records2)
        for r1, r2 in zip(records1, records2):
            assert r1["measurement_timestamp"] == r2["measurement_timestamp"]
            assert r1["raw_weight_kg"] == r2["raw_weight_kg"]
            assert r1["calculated_liters"] == r2["calculated_liters"]
            assert r1["fill_percentage"] == r2["fill_percentage"]
            assert r1["battery_voltage_mv"] == r2["battery_voltage_mv"]
            assert r1["is_synthetic"] is True and r2["is_synthetic"] is True


def test_no_negative_volumes_or_leaks(stage_100_db):
    """Criterion 4: Inspects generated rows and asserts zero negative volumes and valid physical/statistical checks."""
    seed_database(target_engine=stage_100_db, reset=True, quiet=True)
    session_factory = get_session_factory(stage_100_db)

    with session_factory() as session:
        # Generate 90 days of telemetry across all 11 containers
        sim = MonteCarloSimulator(db_session=session, seed=42)
        sim.generate_synthetic_telemetry(days=90, interval_hours=2, to_db=True)

        telemetry_count = session.query(Telemetry.id).count()
        assert telemetry_count > 10000

        # Run automated DataIntegrityAuditor
        auditor = DataIntegrityAuditor(db_session=session)
        audit_report = auditor.validate_database_integrity(session=session, raise_on_error=True)

        assert audit_report["status"] == "PASSED"
        assert audit_report["physical_checks"]["negative_liters_count"] == 0
        assert audit_report["physical_checks"]["overfilled_count"] == 0
        assert audit_report["physical_checks"]["invalid_voltage_count"] == 0
        assert audit_report["relational_checks"]["orphaned_telemetries"] == 0
        assert audit_report["relational_checks"]["non_synthetic_records"] == 0
        assert audit_report["statistical_checks"]["type_hierarchy_passed"] is True
        assert audit_report["statistical_checks"]["weekend_lift_passed"] is True


def test_chronological_split_integrity(stage_100_db, tmp_path):
    """Criterion 5: Asserts max(Date_train) < min(Date_test) with zero temporal overlap."""
    seed_database(target_engine=stage_100_db, reset=True, quiet=True)
    session_factory = get_session_factory(stage_100_db)

    output_dir = tmp_path / "processed_test"

    with session_factory() as session:
        sim = MonteCarloSimulator(db_session=session, seed=42)
        sim.generate_synthetic_telemetry(days=90, interval_hours=2, to_db=True)

        exporter = ChronologicalDatasetExporter(db_session=session)
        result = exporter.export_chronological_splits(
            train_ratio=0.8,
            output_dir=str(output_dir),
            session=session,
        )

        assert os.path.exists(result["full_csv"])
        assert os.path.exists(result["train_csv"])
        assert os.path.exists(result["test_csv"])
        assert os.path.exists(result["summary_json"])

        summary = result["summary"]
        assert summary["total_records"] > 0
        assert summary["train_records"] > 0
        assert summary["test_records"] > 0

        # Strict chronological separation: max train date < min test date
        train_end = summary["train_date_range"]["end"]
        test_start = summary["test_date_range"]["start"]
        assert train_end < test_start, f"Data leakage: train_end {train_end} is not < test_start {test_start}"

        # Verify summary json content
        with open(result["summary_json"], "r", encoding="utf-8") as f:
            loaded_summary = json.load(f)
            assert loaded_summary["train_records"] == summary["train_records"]
            assert loaded_summary["businesses_count"] == 11
            assert "daily_liters" in loaded_summary["features"]
            assert "lag_7d_liters" in loaded_summary["features"]
