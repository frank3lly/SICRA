"""Unit and integration tests for the Monte Carlo telemetry simulation engine."""

from datetime import datetime, timezone
import time
import numpy as np
import pytest
from scipy import stats
from sqlalchemy import insert

from src.database.session import get_engine, get_session_factory
from src.models import (
    Base,
    Business,
    BusinessType,
    Container,
    ContainerStatus,
    Telemetry,
    TelemetryFlag,
)
from src.simulation.cli import run_simulation
from src.simulation.engine import MonteCarloSimulator


@pytest.fixture
def mock_container():
    """Create a realistic mock Container linked to a Pica Pollo business."""
    biz = Business(
        id="mock_biz_spm_001",
        name="Pica Pollo Test",
        business_type=BusinessType.PICA_POLLO,
        num_fryers=4,
        avg_daily_customers=380,
        latitude=18.455,
        longitude=-69.308,
        address="Test Address",
        city="San Pedro de Macorís",
    )
    container = Container(
        id="mock_container_001",
        business_id=biz.id,
        device_token="sicra_live_tok_test_001",
        capacity_liters=100.0,
        tare_weight_kg=6.50,
        oil_density_kg_l=0.92,
        status=ContainerStatus.ACTIVE,
    )
    container.business = biz
    return container


@pytest.fixture
def test_db_engine():
    """In-memory SQLite database engine for simulation tests."""
    engine = get_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


def test_deterministic_reproducibility(mock_container):
    """Verify running the simulation twice with seed=42 yields identical results down to 4 decimal places."""
    start_date = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    days = 60
    interval_hours = 2

    sim1 = MonteCarloSimulator(seed=42)
    records1 = sim1.simulate_business_timeline(
        container=mock_container,
        start_date=start_date,
        days=days,
        interval_hours=interval_hours,
    )

    sim2 = MonteCarloSimulator(seed=42)
    records2 = sim2.simulate_business_timeline(
        container=mock_container,
        start_date=start_date,
        days=days,
        interval_hours=interval_hours,
    )

    assert len(records1) == len(records2)
    assert len(records1) > 0

    for r1, r2 in zip(records1, records2):
        assert r1["measurement_timestamp"] == r2["measurement_timestamp"]
        assert r1["flag"] == r2["flag"]
        assert r1["is_synthetic"] is True and r2["is_synthetic"] is True
        assert r1["battery_voltage_mv"] == r2["battery_voltage_mv"]
        np.testing.assert_almost_equal(r1["raw_weight_kg"], r2["raw_weight_kg"], decimal=4)
        np.testing.assert_almost_equal(r1["calculated_liters"], r2["calculated_liters"], decimal=4)
        np.testing.assert_almost_equal(r1["fill_percentage"], r2["fill_percentage"], decimal=4)
        np.testing.assert_almost_equal(r1["battery_percentage"], r2["battery_percentage"], decimal=4)


def test_performance_benchmark(test_db_engine, mock_container):
    """Verify generating and inserting 50,000 telemetry rows completes in under 10 seconds."""
    sim = MonteCarloSimulator(seed=42)
    start_date = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)

    start_time = time.perf_counter()

    # Generate records across multiple containers to reach 50,000
    containers = []
    for i in range(10):
        c = Container(
            id=f"perf_container_{i}",
            business_id=mock_container.business.id,
            device_token=f"token_{i}",
            capacity_liters=100.0,
            tare_weight_kg=6.50,
            oil_density_kg_l=0.92,
            status=ContainerStatus.ACTIVE,
        )
        c.business = mock_container.business
        containers.append(c)

    # 10 containers * 210 days * 24 readings/day = 50,400 records
    all_records = []
    for c in containers:
        records = sim.simulate_business_timeline(
            container=c,
            start_date=start_date,
            days=210,
            interval_hours=1,
        )
        all_records.extend(records)

    records_to_insert = all_records[:50000]
    assert len(records_to_insert) == 50000

    # Bulk insert in chunks of 5,000
    session_factory = get_session_factory(test_db_engine)
    with session_factory() as session:
        # Persist parent business and containers to satisfy foreign key constraints
        session.add(mock_container.business)
        for c in containers:
            session.add(c)
        session.commit()

        for i in range(0, len(records_to_insert), 5000):
            session.execute(insert(Telemetry), records_to_insert[i : i + 5000])
        session.commit()

    total_time = time.perf_counter() - start_time
    print(f"\nBenchmark: 50,000 records generated and persisted in {total_time:.2f}s")
    assert total_time < 10.0, f"Benchmark exceeded 10.0s threshold: took {total_time:.2f}s"


def test_physical_law_assertions(mock_container):
    """Verify physical constraints: no negative volumes, raw_weight >= tare - 0.1, is_synthetic=True, and weekend statistical surge."""
    sim = MonteCarloSimulator(seed=42)
    start_date = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    records = sim.simulate_business_timeline(
        container=mock_container,
        start_date=start_date,
        days=90,
        interval_hours=2,
    )

    tare = mock_container.tare_weight_kg

    weekday_liters = []
    weekend_liters = []

    for r in records:
        # 1. Scale tare physical lower bound
        assert r["raw_weight_kg"] >= tare - 0.1, f"Raw weight {r['raw_weight_kg']} < tare {tare} - 0.1"

        # 2. Calculated liters non-negative
        assert r["calculated_liters"] >= 0.0

        # 3. Fill percentage valid range
        assert 0.0 <= r["fill_percentage"] <= 100.0

        # 4. Mandatory is_synthetic flag
        assert r["is_synthetic"] is True

        # Group daily volumes by weekday vs weekend
        dow = r["measurement_timestamp"].weekday()
        if dow in [0, 1, 2]:  # Mon, Tue, Wed
            weekday_liters.append(r["calculated_liters"])
        elif dow in [4, 5, 6]:  # Fri, Sat, Sun
            weekend_liters.append(r["calculated_liters"])

    # 5. Weekend generation statistically significantly higher (p < 0.01)
    t_stat, p_value = stats.ttest_ind(weekend_liters, weekday_liters, alternative="greater")
    assert p_value < 0.01, f"Weekend surge p-value {p_value} is not < 0.01"


def test_drain_events_and_battery(mock_container):
    """Verify drain events and battery voltage cycles occur across a 90-day simulation."""
    sim = MonteCarloSimulator(seed=42)
    start_date = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    records = sim.simulate_business_timeline(
        container=mock_container,
        start_date=start_date,
        days=90,
        interval_hours=2,
    )

    drain_events = [r for r in records if r["flag"] == TelemetryFlag.DRAIN_EVENT.value]
    assert len(drain_events) >= 1, "Expected at least one collection drain event in 90 days"

    # Verify battery levels are tracked and within valid operating range
    voltages = [r["battery_voltage_mv"] for r in records]
    assert min(voltages) >= 3350
    assert max(voltages) <= 4200


def test_cli_execution(tmp_path):
    """Verify CLI runner executes without errors and generates optional CSV export."""
    csv_file = tmp_path / "sim_output.csv"
    count = run_simulation(
        days=10,
        interval_hours=2,
        seed=42,
        to_db=False,
        output_csv=str(csv_file),
    )
    assert count > 0
    assert csv_file.exists()
    assert csv_file.stat().st_size > 0
