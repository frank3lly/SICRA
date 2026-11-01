"""End-to-end integration test suite verifying the complete Stage 300 backend lifecycle."""

from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from src.database.seed import (
    ADMIN_PASSWORD,
    COLLECTOR_PASSWORD,
    OWNER_PASSWORD,
    seed_database,
)
from src.database.session import get_db, get_db_context, get_engine, init_db
from src.main import app
from src.models.entities import Alert, Business, Container, Telemetry, User
from src.models.enums import AlertType, BusinessType, RouteStatus, TelemetryFlag, UserRole


@pytest.fixture(scope="module")
def e2e_client(tmp_path_factory):
    """Provide a TestClient with a fresh temporary database seeded with Dominican businesses."""
    test_dir = tmp_path_factory.mktemp("stage_300_e2e")
    test_db_url = f"sqlite:///{test_dir}/sicra_e2e.db"
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
# Full End-to-End Operational Lifecycle Test
# ==============================================================================

def test_full_stage_300_lifecycle_e2e(e2e_client):
    """Certify the end-to-end backend flow:

    Step 1: Auth & Role Enforcement
    Step 2: IoT Telemetry Batch Ingestion
    Step 3: Alert Triggering (Requirement R-05)
    Step 4: Dynamic Route Generation
    Step 5: Pickup Confirmation & Drain Event Resolution
    """
    client, test_engine = e2e_client

    # --------------------------------------------------------------------------
    # Step 1: Auth & Role Enforcement
    # --------------------------------------------------------------------------
    # Login Admin
    resp_admin = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sicra.do", "password": ADMIN_PASSWORD},
    )
    assert resp_admin.status_code == 200
    admin_token = resp_admin.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    assert resp_admin.json()["user"]["role"] == UserRole.ADMIN.value

    # Login Collector
    resp_collector = client.post(
        "/api/v1/auth/login",
        json={"email": "operaciones@reoil.do", "password": COLLECTOR_PASSWORD},
    )
    assert resp_collector.status_code == 200
    collector_token = resp_collector.json()["access_token"]
    collector_headers = {"Authorization": f"Bearer {collector_token}"}
    assert resp_collector.json()["user"]["role"] == UserRole.COLLECTOR.value

    # Login Business Owner (Pica Pollo Expreso)
    resp_owner = client.post(
        "/api/v1/auth/login",
        json={"email": "picapollo.expreso@sicra.do", "password": OWNER_PASSWORD},
    )
    assert resp_owner.status_code == 200
    owner_token = resp_owner.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    assert resp_owner.json()["user"]["role"] == UserRole.BUSINESS_OWNER.value
    biz_id = resp_owner.json()["user"]["business_id"]
    assert biz_id is not None

    # Identify Pica Pollo container
    with get_db_context(test_engine) as session:
        pica_container = (
            session.query(Container)
            .filter(Container.business_id == biz_id)
            .first()
        )
        assert pica_container is not None
        device_token = pica_container.device_token
        container_id = str(pica_container.id)

    # --------------------------------------------------------------------------
    # Step 2: IoT Telemetry Batch Ingestion
    # --------------------------------------------------------------------------
    base_time = datetime(2026, 10, 31, 6, 0, 0, tzinfo=timezone.utc)
    batch_readings = [
        {
            "timestamp": (base_time + timedelta(hours=i)).isoformat(),
            "raw_weight_kg": round(15.0 + (i * 1.2), 2),
            "battery_mv": 3950 - (i * 2),
            "is_synthetic": False,
        }
        for i in range(20)
    ]

    resp_batch = client.post(
        "/api/v1/telemetry/ingest",
        json={"readings": batch_readings},
        headers={"X-Device-Token": device_token},
    )
    assert resp_batch.status_code == 200
    batch_data = resp_batch.json()
    assert batch_data["accepted_count"] == 20
    assert batch_data["duplicate_count"] == 0

    # --------------------------------------------------------------------------
    # Step 3: Alert Triggering (Requirement R-05)
    # --------------------------------------------------------------------------
    # Pica Pollo has capacity 100L, tare 6.5kg, density 0.92
    # 84% capacity = 84 liters -> weight = 6.5 + (84 * 0.92) = 83.78 kg
    alert_time = base_time + timedelta(hours=21)
    payload_high = {
        "readings": [
            {
                "timestamp": alert_time.isoformat(),
                "raw_weight_kg": 84.0,
                "battery_mv": 3900,
            }
        ]
    }
    resp_high = client.post(
        "/api/v1/telemetry/ingest",
        json=payload_high,
        headers={"X-Device-Token": device_token},
    )
    assert resp_high.status_code == 200
    assert resp_high.json()["current_fill_percentage"] >= 80.0

    # Verify active alert is immediately visible to Collector
    resp_alerts = client.get("/api/v1/alerts/active", headers=collector_headers)
    assert resp_alerts.status_code == 200
    active_alerts = resp_alerts.json()
    pica_alert = next((a for a in active_alerts if a["container_id"] == container_id), None)
    assert pica_alert is not None
    assert pica_alert["alert_type"] == AlertType.CAPACITY_80_PERCENT.value
    assert pica_alert["triggered_percentage"] >= 80.0

    # Record baseline environmental counters before collection
    resp_stats_initial = client.get("/api/v1/stats/environmental", headers=collector_headers)
    assert resp_stats_initial.status_code == 200
    initial_stats = resp_stats_initial.json()
    initial_oil = initial_stats["total_oil_diverted_liters"]
    initial_water = initial_stats["water_preserved_liters"]

    # --------------------------------------------------------------------------
    # Step 4: Dynamic Route Generation
    # --------------------------------------------------------------------------
    resp_route = client.post("/api/v1/routes/generate-today", headers=collector_headers)
    assert resp_route.status_code == 200
    route_data = resp_route.json()
    route_id = route_data["route_id"]
    itinerary = route_data["itinerary"]

    # Verify route starts and ends at Depot
    assert itinerary[0]["is_depot"] is True
    assert itinerary[-1]["is_depot"] is True

    # Verify Pica Pollo Expreso is included in route
    pica_stop = next((s for s in itinerary if s["business_id"] == biz_id), None)
    assert pica_stop is not None
    assert pica_stop["visited"] is False

    # --------------------------------------------------------------------------
    # Step 5: Pickup Confirmation & Drain Event Resolution
    # --------------------------------------------------------------------------
    # Confirm stop pickup by driver
    resp_confirm = client.post(
        f"/api/v1/routes/{route_id}/confirm-stop/{biz_id}",
        headers=collector_headers,
    )
    assert resp_confirm.status_code == 200
    assert resp_confirm.json()["status"] == "stop_confirmed"

    # Post low reading (near tare: 7.0 kg) simulating container emptied
    drain_time = alert_time + timedelta(hours=1)
    payload_drain = {
        "readings": [
            {
                "timestamp": drain_time.isoformat(),
                "raw_weight_kg": 7.0,
                "battery_mv": 3900,
            }
        ]
    }
    resp_drain = client.post(
        "/api/v1/telemetry/ingest",
        json=payload_drain,
        headers={"X-Device-Token": device_token},
    )
    assert resp_drain.status_code == 200
    drain_res = resp_drain.json()
    assert drain_res["drain_events_detected"] >= 1

    # Verify alert is resolved
    with get_db_context(test_engine) as session:
        alert_db = (
            session.query(Alert)
            .filter(Alert.container_id == container_id)
            .order_by(Alert.created_at.desc())
            .first()
        )
        assert alert_db is not None
        assert alert_db.is_resolved is True
        assert alert_db.resolved_at is not None

    # Verify environmental metrics incremented
    resp_stats_final = client.get("/api/v1/stats/environmental", headers=collector_headers)
    assert resp_stats_final.status_code == 200
    final_stats = resp_stats_final.json()
    assert final_stats["total_oil_diverted_liters"] > initial_oil
    assert final_stats["water_preserved_liters"] > initial_water
    assert final_stats["compliance_framework"] == "Trazabilidad y Recoleccion Certificada"

    # Verify publication-grade PDF report download
    resp_pdf = client.get("/api/v1/stats/report-pdf", headers=collector_headers)
    assert resp_pdf.status_code == 200
    assert resp_pdf.headers["content-type"] == "application/pdf"
    assert resp_pdf.content.startswith(b"%PDF")
    assert len(resp_pdf.content) > 1000


# ==============================================================================
# Business and Container CRUD Endpoint Tests
# ==============================================================================

def test_businesses_and_containers_endpoints(e2e_client):
    """Verify REST operations for businesses, containers, and RBAC visibility."""
    client, _ = e2e_client

    # Authenticate as Admin
    resp_admin = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sicra.do", "password": ADMIN_PASSWORD},
    )
    admin_headers = {"Authorization": f"Bearer {resp_admin.json()['access_token']}"}

    # 1. List businesses
    resp_biz = client.get("/api/v1/businesses/", headers=admin_headers)
    assert resp_biz.status_code == 200
    businesses = resp_biz.json()
    assert len(businesses) >= 3
    first_biz = businesses[0]

    # 2. Get business detail
    resp_biz_det = client.get(f"/api/v1/businesses/{first_biz['id']}", headers=admin_headers)
    assert resp_biz_det.status_code == 200
    assert resp_biz_det.json()["name"] == first_biz["name"]

    # 3. Create new business (Admin only)
    new_biz_payload = {
        "name": "Comedor Doña Rosa",
        "business_type": BusinessType.CAFETERIA.value,
        "num_fryers": 2,
        "avg_daily_customers": 120,
        "latitude": 18.459,
        "longitude": -69.305,
        "address": "Calle Sánchez #45",
        "city": "San Pedro de Macorís",
        "contact_name": "Rosa Martínez",
        "phone": "809-529-4444",
        "is_active": True,
    }
    resp_create = client.post("/api/v1/businesses/", json=new_biz_payload, headers=admin_headers)
    assert resp_create.status_code == 201
    assert resp_create.json()["name"] == "Comedor Doña Rosa"

    # 4. List containers
    resp_containers = client.get("/api/v1/containers/", headers=admin_headers)
    assert resp_containers.status_code == 200
    containers = resp_containers.json()
    assert len(containers) >= 3

    first_container = containers[0]
    resp_c_det = client.get(f"/api/v1/containers/{first_container['id']}", headers=admin_headers)
    assert resp_c_det.status_code == 200
    assert resp_c_det.json()["id"] == first_container["id"]

    # 5. Authenticate as Business Owner and query /my-container
    resp_owner = client.post(
        "/api/v1/auth/login",
        json={"email": "picapollo.expreso@sicra.do", "password": OWNER_PASSWORD},
    )
    owner_headers = {"Authorization": f"Bearer {resp_owner.json()['access_token']}"}

    resp_my_c = client.get("/api/v1/containers/my-container", headers=owner_headers)
    assert resp_my_c.status_code == 200
    assert resp_my_c.json()["business_id"] == resp_owner.json()["user"]["business_id"]


# ==============================================================================
# Predictive Analytics Endpoint Tests
# ==============================================================================

def test_predictions_endpoints(e2e_client):
    """Verify predictive forecasting endpoints for single containers and fleet batches."""
    client, _ = e2e_client

    # Authenticate Admin
    resp_admin = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sicra.do", "password": ADMIN_PASSWORD},
    )
    admin_headers = {"Authorization": f"Bearer {resp_admin.json()['access_token']}"}

    # Get a container ID
    containers_resp = client.get("/api/v1/containers/", headers=admin_headers)
    container_id = containers_resp.json()[0]["id"]

    # 1. Query prediction for container: GET /api/v1/predictions/container/{id}
    resp_pred = client.get(f"/api/v1/predictions/container/{container_id}", headers=admin_headers)
    assert resp_pred.status_code == 200
    pred_data = resp_pred.json()
    assert "predicted_daily_liters" in pred_data
    assert pred_data["predicted_daily_liters"] >= 0.0

    # 2. Run fleet-wide batch forecast: POST /api/v1/predictions/run-forecast
    resp_batch_pred = client.post("/api/v1/predictions/run-forecast", headers=admin_headers)
    assert resp_batch_pred.status_code == 200
    batch_res = resp_batch_pred.json()
    assert batch_res["status"] == "forecast_completed"
    assert batch_res["containers_processed"] >= 1
