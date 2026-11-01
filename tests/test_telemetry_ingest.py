"""Verification and test suite for IoT telemetry intake, batch processing, and drain detection."""

from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from src.database.seed import ADMIN_PASSWORD, OWNER_PASSWORD, seed_database
from src.database.session import get_db, get_db_context, get_engine, init_db
from src.main import app
from src.models.entities import Alert, Container, Telemetry, User
from src.models.enums import AlertType, ContainerStatus, TelemetryFlag, UserRole
from src.services.telemetry_service import TelemetryService


@pytest.fixture(scope="module")
def seeded_client(tmp_path_factory):
    """Provide a TestClient with a fully initialized and seeded test database."""
    test_dir = tmp_path_factory.mktemp("telemetry_test")
    test_db_url = f"sqlite:///{test_dir}/sicra_telemetry_test.db"
    test_engine = get_engine(test_db_url)

    init_db(test_engine)
    seed_database(target_engine=test_engine, quiet=True)

    def override_get_db():
        with get_db_context(test_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    yield client, test_engine

    app.dependency_overrides.clear()


# ==============================================================================
# 1. Device Authentication Tests
# ==============================================================================

def test_device_authentication_rejection_on_invalid_token(seeded_client):
    """Verify that transmission with an invalid or missing token is rejected with HTTP 401."""
    client, _ = seeded_client

    # Missing token entirely
    payload = {
        "readings": [
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "raw_weight_kg": 15.0,
            }
        ]
    }
    resp_missing = client.post("/api/v1/telemetry/ingest", json=payload)
    assert resp_missing.status_code == 401

    # Invalid token in header
    resp_invalid_header = client.post(
        "/api/v1/telemetry/ingest",
        json=payload,
        headers={"X-Device-Token": "invalid_token_12345"},
    )
    assert resp_invalid_header.status_code == 401
    assert "Invalid device authentication token" in resp_invalid_header.json()["detail"]

    # Invalid token in JSON payload
    payload_with_bad_token = {
        "device_token": "nonexistent_token_99999",
        "readings": [
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "raw_weight_kg": 15.0,
            }
        ],
    }
    resp_invalid_body = client.post(
        "/api/v1/telemetry/ingest", json=payload_with_bad_token
    )
    assert resp_invalid_body.status_code == 401


def test_device_authentication_success_with_valid_token(seeded_client):
    """Verify valid seeded token is accepted via header or body returning HTTP 200."""
    client, test_engine = seeded_client

    with get_db_context(test_engine) as session:
        container = session.query(Container).filter(Container.status == ContainerStatus.ACTIVE).first()
        assert container is not None
        valid_token = container.device_token

    ts = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    payload = {
        "readings": [
            {
                "timestamp": ts,
                "raw_weight_kg": 12.5,
                "battery_mv": 3900,
            }
        ]
    }

    # Transmit via X-Device-Token header
    resp = client.post(
        "/api/v1/telemetry/ingest",
        json=payload,
        headers={"X-Device-Token": valid_token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["accepted_count"] == 1
    assert data["duplicate_count"] == 0


def test_device_authentication_rejection_on_inactive_container(seeded_client):
    """Verify decommissioned/inactive container tokens are rejected with HTTP 401."""
    client, test_engine = seeded_client

    with get_db_context(test_engine) as session:
        # Create an inactive container for testing
        active_container = session.query(Container).first()
        inactive_container = Container(
            business_id=active_container.business_id,
            device_token="sicra_tok_decommissioned_999",
            capacity_liters=50.0,
            status=ContainerStatus.INACTIVE,
        )
        session.add(inactive_container)
        session.commit()
        decommissioned_token = inactive_container.device_token

    payload = {
        "readings": [
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "raw_weight_kg": 10.0,
            }
        ]
    }
    resp = client.post(
        "/api/v1/telemetry/ingest",
        json=payload,
        headers={"X-Device-Token": decommissioned_token},
    )
    assert resp.status_code == 401
    assert "inactive" in resp.json()["detail"].lower()


# ==============================================================================
# 2. Offline Batch Ingestion & Deduplication Tests (Requirement R-09)
# ==============================================================================

def test_batch_offline_ingestion_and_deduplication(seeded_client):
    """Simulate 50 consecutive readings accumulated during a multi-day network outage.

    Validates:
    - All 50 readings are saved chronologically.
    - Subsequent identical transmission results in zero duplicates added.
    """
    client, test_engine = seeded_client

    with get_db_context(test_engine) as session:
        # Select a container
        container = session.query(Container).filter(Container.capacity_liters == 100.0).first()
        if not container:
            container = session.query(Container).first()
        device_token = container.device_token
        container_id = container.id

    base_time = datetime(2026, 10, 20, 8, 0, 0, tzinfo=timezone.utc)
    readings = []
    for i in range(50):
        readings.append(
            {
                "timestamp": (base_time + timedelta(hours=i)).isoformat(),
                "raw_weight_kg": round(10.0 + (i * 0.5), 2),
                "battery_mv": 3950 - i,
                "is_synthetic": False,
            }
        )

    # 1. Transmit the 50-reading batch
    payload = {"readings": readings}
    resp1 = client.post(
        "/api/v1/telemetry/ingest",
        json=payload,
        headers={"X-Device-Token": device_token},
    )
    assert resp1.status_code == 200
    res1_data = resp1.json()
    assert res1_data["accepted_count"] == 50
    assert res1_data["duplicate_count"] == 0

    # Verify chronological persistence in database
    with get_db_context(test_engine) as session:
        records = (
            session.query(Telemetry)
            .filter(Telemetry.container_id == container_id)
            .order_by(Telemetry.measurement_timestamp.asc())
            .all()
        )
        assert len(records) >= 50
        timestamps = [r.measurement_timestamp for r in records[-50:]]
        # Assert strictly increasing
        for idx in range(len(timestamps) - 1):
            assert timestamps[idx] < timestamps[idx + 1]

    # 2. Re-transmit the exact same batch -> Assert 0 accepted, 50 duplicates
    resp2 = client.post(
        "/api/v1/telemetry/ingest",
        json=payload,
        headers={"X-Device-Token": device_token},
    )
    assert resp2.status_code == 200
    res2_data = resp2.json()
    assert res2_data["accepted_count"] == 0
    assert res2_data["duplicate_count"] == 50


# ==============================================================================
# 3. Drain Event Detector and Alert Auto-Resolution
# ==============================================================================

def test_drain_event_detection_and_alert_resolution(seeded_client):
    """Test full cycle: 80% threshold alert firing followed by collection drain event resolution."""
    client, test_engine = seeded_client

    with get_db_context(test_engine) as session:
        # Find or create a specific 50L container for calibrated testing
        container = session.query(Container).filter(Container.capacity_liters == 50.0).first()
        device_token = container.device_token
        container_id = container.id

    now = datetime(2026, 10, 25, 10, 0, 0, tzinfo=timezone.utc)

    # 1. Post a high weight: 42.0 kg on a 50L container
    # Net: (42.0 - 3.80) / 0.92 = ~41.52 L -> 83.0% fill -> triggers 80% alert
    payload_fill = {
        "readings": [
            {
                "timestamp": now.isoformat(),
                "raw_weight_kg": 42.0,
                "battery_mv": 4000,
            }
        ]
    }
    resp_fill = client.post(
        "/api/v1/telemetry/ingest",
        json=payload_fill,
        headers={"X-Device-Token": device_token},
    )
    assert resp_fill.status_code == 200
    fill_data = resp_fill.json()
    assert fill_data["alerts_triggered"] >= 1
    assert fill_data["current_fill_percentage"] >= 80.0

    # Verify open alert exists in database
    with get_db_context(test_engine) as session:
        open_alert = (
            session.query(Alert)
            .filter(
                Alert.container_id == container_id,
                Alert.alert_type == AlertType.CAPACITY_80_PERCENT,
                Alert.is_resolved == False,
            )
            .first()
        )
        assert open_alert is not None
        assert open_alert.is_resolved is False

    # 2. Post a subsequent low reading (4.0 kg, near tare) simulating collection emptying
    payload_drain = {
        "readings": [
            {
                "timestamp": (now + timedelta(hours=2)).isoformat(),
                "raw_weight_kg": 4.0,
                "battery_mv": 3980,
            }
        ]
    }
    resp_drain = client.post(
        "/api/v1/telemetry/ingest",
        json=payload_drain,
        headers={"X-Device-Token": device_token},
    )
    assert resp_drain.status_code == 200
    drain_data = resp_drain.json()
    assert drain_data["drain_events_detected"] == 1
    assert drain_data["alerts_resolved"] >= 1

    # Verify telemetry flag and alert state in database
    with get_db_context(test_engine) as session:
        latest_tel = (
            session.query(Telemetry)
            .filter(Telemetry.container_id == container_id)
            .order_by(Telemetry.measurement_timestamp.desc())
            .first()
        )
        assert latest_tel is not None
        assert latest_tel.flag == TelemetryFlag.DRAIN_EVENT

        # Verify the alert is now marked resolved
        resolved_alert = (
            session.query(Alert)
            .filter(
                Alert.container_id == container_id,
                Alert.alert_type == AlertType.CAPACITY_80_PERCENT,
            )
            .order_by(Alert.created_at.desc())
            .first()
        )
        assert resolved_alert is not None
        assert resolved_alert.is_resolved is True
        assert resolved_alert.resolved_at is not None


# ==============================================================================
# 4. Physical Conversions and Calibration Formulas
# ==============================================================================

def test_physical_conversion_logic(seeded_client):
    """Verify volume liters, fill percentage, and battery health calculations."""
    _, test_engine = seeded_client

    with get_db_context(test_engine) as session:
        container = session.query(Container).filter(Container.capacity_liters == 100.0).first()

    # Tare = 6.5, Density = 0.92, Capacity = 100.0
    # Net: 52.5 - 6.5 = 46.0 kg -> Liters: 46.0 / 0.92 = 50.0 L -> 50.0% fill
    liters = TelemetryService.compute_volume_liters(52.5, container)
    assert pytest.approx(liters, 0.01) == 50.0

    fill_pct = TelemetryService.compute_fill_percentage(liters, container)
    assert pytest.approx(fill_pct, 0.01) == 50.0

    # Battery interpolation between 3400 (0%) and 4200 (100%)
    assert TelemetryService.compute_battery_percentage(None) is None
    assert TelemetryService.compute_battery_percentage(4200) == 100.0
    assert TelemetryService.compute_battery_percentage(3400) == 0.0
    assert TelemetryService.compute_battery_percentage(3800) == 50.0
    assert TelemetryService.compute_battery_percentage(3000) == 0.0
    assert TelemetryService.compute_battery_percentage(4500) == 100.0


# ==============================================================================
# 5. Historical Telemetry Retrieval & Access Isolation
# ==============================================================================

def test_container_telemetry_query_with_rbac(seeded_client):
    """Verify GET /api/v1/telemetry/container/{id} obeys multi-tenant data isolation."""
    client, test_engine = seeded_client

    with get_db_context(test_engine) as session:
        owners = session.query(User).filter(User.role == UserRole.BUSINESS_OWNER).limit(2).all()
        owner_a = owners[0]
        owner_b = owners[1]

        container_a = session.query(Container).filter(Container.business_id == owner_a.business_id).first()
        container_b = session.query(Container).filter(Container.business_id == owner_b.business_id).first()

        owner_a_email = owner_a.email
        container_a_id = container_a.id
        container_b_id = container_b.id

    # Authenticate as Owner A
    login_a = client.post(
        "/api/v1/auth/login",
        json={"email": owner_a_email, "password": OWNER_PASSWORD},
    )
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Owner A queries own container telemetry -> 200 OK
    resp_own = client.get(
        f"/api/v1/telemetry/container/{container_a_id}",
        headers=headers_a,
    )
    assert resp_own.status_code == 200
    assert isinstance(resp_own.json(), list)

    # Owner A queries competitor's container telemetry -> 403 Forbidden
    resp_comp = client.get(
        f"/api/v1/telemetry/container/{container_b_id}",
        headers=headers_a,
    )
    assert resp_comp.status_code == 403
    assert "Data isolation prevents access" in resp_comp.json()["detail"]
