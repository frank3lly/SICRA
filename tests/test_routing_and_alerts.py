"""Verification and test suite for 80% capacity alert engine and dynamic route optimization."""

from datetime import date, datetime, timedelta, timezone
import json
import time
import pytest
from fastapi.testclient import TestClient

from src.database.seed import ADMIN_PASSWORD, COLLECTOR_PASSWORD, OWNER_PASSWORD, seed_database
from src.database.session import get_db, get_db_context, get_engine, init_db
from src.main import app
from src.models.entities import Alert, Business, CollectionRoute, Container, User
from src.models.enums import AlertType, ContainerStatus, RouteStatus, UserRole
from src.services.alert_service import AlertService
from src.services.routing_service import (
    DEPOT_SPEC,
    RoutingService,
    calculate_tour_distance,
    haversine_distance,
)


@pytest.fixture(scope="module")
def seeded_client(tmp_path_factory):
    """Provide a TestClient with a fully initialized test database."""
    test_dir = tmp_path_factory.mktemp("routing_alerts_test")
    test_db_url = f"sqlite:///{test_dir}/sicra_routing_test.db"
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
# 1. Alert Generation Verification (Requirement R-05)
# ==============================================================================

def test_alert_generation_and_deduplication(seeded_client):
    """Verify 80% capacity alert creation upon high reading and assert no duplicates created upon re-transmission."""
    client, test_engine = seeded_client

    with get_db_context(test_engine) as session:
        # Find 50L container (Tare: 3.80 kg, Density: 0.92)
        container = session.query(Container).filter(Container.capacity_liters == 50.0).first()
        assert container is not None
        device_token = container.device_token
        container_id = container.id

        # Clean any prior alerts for clean test state
        session.query(Alert).filter(Alert.container_id == container_id).delete()
        session.commit()

    # 41.0 kg on 50L container:
    # Net: (41.0 - 3.80) / 0.92 = 37.20 / 0.92 = 40.43 L -> 80.87%
    ts = datetime(2026, 10, 31, 10, 0, 0, tzinfo=timezone.utc).isoformat()
    payload = {
        "readings": [
            {
                "timestamp": ts,
                "raw_weight_kg": 41.0,
                "battery_mv": 3950,
            }
        ]
    }

    # 1. Ingest reading
    resp1 = client.post(
        "/api/v1/telemetry/ingest",
        json=payload,
        headers={"X-Device-Token": device_token},
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["alerts_triggered"] == 1
    assert data1["current_fill_percentage"] >= 80.0

    # Assert alert record exists in database
    with get_db_context(test_engine) as session:
        alerts = (
            session.query(Alert)
            .filter(
                Alert.container_id == container_id,
                Alert.alert_type == AlertType.CAPACITY_80_PERCENT,
                Alert.is_resolved == False,
            )
            .all()
        )
        assert len(alerts) == 1
        assert alerts[0].triggered_percentage >= 80.0
        assert alerts[0].is_resolved is False

    # 2. Re-send another reading at 41.5 kg -> Assert no duplicate alert record is created
    ts2 = datetime(2026, 10, 31, 11, 0, 0, tzinfo=timezone.utc).isoformat()
    payload2 = {
        "readings": [
            {
                "timestamp": ts2,
                "raw_weight_kg": 41.5,
                "battery_mv": 3950,
            }
        ]
    }
    resp2 = client.post(
        "/api/v1/telemetry/ingest",
        json=payload2,
        headers={"X-Device-Token": device_token},
    )
    assert resp2.status_code == 200

    with get_db_context(test_engine) as session:
        alerts_after = (
            session.query(Alert)
            .filter(
                Alert.container_id == container_id,
                Alert.alert_type == AlertType.CAPACITY_80_PERCENT,
                Alert.is_resolved == False,
            )
            .all()
        )
        assert len(alerts_after) == 1


def test_predictive_alert_trigger(seeded_client):
    """Verify AlertService generates alert when projected hours to 80% is <= 24.0."""
    _, test_engine = seeded_client

    with get_db_context(test_engine) as session:
        container = session.query(Container).filter(Container.capacity_liters == 100.0).first()
        container.current_fill_percentage = 72.0  # Under 80% physically
        session.commit()

        # Clean alerts
        session.query(Alert).filter(Alert.container_id == container.id).delete()
        session.commit()

        # Trigger with hours_to_80_percent = 14.5 hours (<= 24.0h)
        alert = AlertService.evaluate_container_alert(
            container=container,
            db=session,
            hours_to_80_percent=14.5,
        )
        assert alert is not None
        assert alert.alert_type == AlertType.CAPACITY_80_PERCENT
        assert alert.is_resolved is False


# ==============================================================================
# 2. 2-Opt Optimization Benchmark & Roundtrip Constraint
# ==============================================================================

def test_2opt_untangling_benchmark():
    """Verify 2-opt untangles a crossed tour and achieves >= 15% distance reduction."""
    with open("src/database/seed_data/dominican_businesses.json", "r", encoding="utf-8") as f:
        pilot_data = json.load(f)[:10]

    # Create an intentionally crossed, interleaved tour
    interleaved_indices = [0, 9, 1, 8, 2, 7, 3, 6, 4, 5]
    crossed_stops = [
        {
            "business_id": pilot_data[i]["key"],
            "business_name": pilot_data[i]["name"],
            "latitude": pilot_data[i]["latitude"],
            "longitude": pilot_data[i]["longitude"],
            "estimated_liters": 35.0,
            "is_depot": False,
        }
        for i in interleaved_indices
    ]

    naive_tour = [dict(DEPOT_SPEC)] + crossed_stops + [dict(DEPOT_SPEC)]
    naive_distance = calculate_tour_distance(naive_tour)

    # Apply 2-opt refinement
    optimized_tour = RoutingService.refine_tour_2opt(naive_tour)
    optimized_distance = calculate_tour_distance(optimized_tour)

    distance_reduction_pct = (
        (naive_distance - optimized_distance) / naive_distance * 100.0
    )

    assert distance_reduction_pct >= 15.0, (
        f"Expected >= 15% improvement, got {distance_reduction_pct:.2f}% "
        f"(Naive: {naive_distance:.2f} km -> Optimized: {optimized_distance:.2f} km)"
    )


def test_roundtrip_depot_constraint():
    """Verify that both Nearest-Neighbor and full optimization start and end at the Depot."""
    stops = [
        {
            "business_id": f"BIZ_{i}",
            "business_name": f"Business {i}",
            "latitude": 18.455 + (i * 0.002),
            "longitude": -69.305 - (i * 0.002),
            "estimated_liters": 40.0,
            "is_depot": False,
        }
        for i in range(5)
    ]

    result = RoutingService.optimize_itinerary(stops)
    itinerary = result["itinerary"]

    # First waypoint must be depot
    assert itinerary[0]["is_depot"] is True
    assert itinerary[0]["latitude"] == DEPOT_SPEC["latitude"]
    assert itinerary[0]["longitude"] == DEPOT_SPEC["longitude"]

    # Final waypoint must be depot return
    assert itinerary[-1]["is_depot"] is True
    assert itinerary[-1]["latitude"] == DEPOT_SPEC["latitude"]
    assert itinerary[-1]["longitude"] == DEPOT_SPEC["longitude"]

    # Intermediate waypoints must be collection stops
    assert len(itinerary) == len(stops) + 2
    for s in itinerary[1:-1]:
        assert s["is_depot"] is False


def test_optimization_execution_time_under_100ms():
    """Verify that route optimization for 50 stops executes in under 100 ms."""
    import random
    random.seed(12345)

    stops_50 = [
        {
            "business_id": f"TEST_BIZ_{i}",
            "business_name": f"Establishment {i}",
            "latitude": 18.460 + random.uniform(-0.02, 0.02),
            "longitude": -69.300 + random.uniform(-0.02, 0.02),
            "estimated_liters": random.uniform(10.0, 80.0),
            "is_depot": False,
        }
        for i in range(50)
    ]

    t_start = time.perf_counter()
    res = RoutingService.optimize_itinerary(stops_50)
    elapsed_ms = (time.perf_counter() - t_start) * 1000.0

    assert elapsed_ms < 100.0, f"Expected < 100 ms, took {elapsed_ms:.2f} ms"
    assert len(res["itinerary"]) == 52  # 50 stops + 2 depot points


# ==============================================================================
# 3. Route Generation and Stop Confirmation REST API Endpoints
# ==============================================================================

def test_routes_api_lifecycle_and_pickup_confirmation(seeded_client):
    """Verify full operational flow: alerts present -> route generated -> driver confirms stop -> container reset."""
    client, test_engine = seeded_client

    # 1. Authenticate as Collector
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "operaciones@reoil.do", "password": COLLECTOR_PASSWORD},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Ensure at least two businesses have active 80% alerts
    with get_db_context(test_engine) as session:
        containers = session.query(Container).limit(2).all()
        biz_ids = []
        for c in containers:
            c.current_fill_percentage = 85.0
            c.current_volume_liters = 42.5
            biz_ids.append(c.business_id)

            # Create or update active alert
            alert = session.query(Alert).filter(Alert.container_id == c.id, Alert.is_resolved == False).first()
            if not alert:
                alert = Alert(
                    container_id=c.id,
                    alert_type=AlertType.CAPACITY_80_PERCENT,
                    triggered_percentage=85.0,
                    is_resolved=False,
                )
                session.add(alert)
        session.commit()

    # 3. Request route generation: POST /api/v1/routes/generate-today
    resp_gen = client.post("/api/v1/routes/generate-today", headers=headers)
    assert resp_gen.status_code == 200
    route_data = resp_gen.json()
    assert "route_id" in route_data
    assert route_data["status"] == RouteStatus.SUGGESTED.value
    assert route_data["total_stops"] >= 2
    assert len(route_data["itinerary"]) >= 4  # 2 depot terminals + at least 2 stops

    route_id = route_data["route_id"]

    # 4. Query current route: GET /api/v1/routes/today
    resp_today = client.get("/api/v1/routes/today", headers=headers)
    assert resp_today.status_code == 200
    assert resp_today.json()["route_id"] == route_id

    # 5. Confirm driver pickup at first stop: POST /api/v1/routes/{id}/confirm-stop/{business_id}
    first_biz_id = biz_ids[0]
    resp_confirm = client.post(
        f"/api/v1/routes/{route_id}/confirm-stop/{first_biz_id}",
        headers=headers,
    )
    assert resp_confirm.status_code == 200
    confirm_data = resp_confirm.json()
    assert confirm_data["status"] == "stop_confirmed"
    assert confirm_data["business_id"] == first_biz_id

    # Verify that container volume is reset to 0.0 and alert is resolved
    with get_db_context(test_engine) as session:
        c1 = session.query(Container).filter(Container.business_id == first_biz_id).first()
        assert c1.current_volume_liters == 0.0
        assert c1.current_fill_percentage == 0.0

        open_alerts = session.query(Alert).filter(Alert.container_id == c1.id, Alert.is_resolved == False).all()
        assert len(open_alerts) == 0


def test_alerts_api_active_and_manual_resolve(seeded_client):
    """Verify GET /api/v1/alerts/active and POST /api/v1/alerts/{id}/resolve."""
    client, test_engine = seeded_client

    # Authenticate as Admin
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sicra.do", "password": ADMIN_PASSWORD},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Ensure an alert exists
    with get_db_context(test_engine) as session:
        container = session.query(Container).first()
        test_alert = Alert(
            container_id=container.id,
            alert_type=AlertType.CAPACITY_80_PERCENT,
            triggered_percentage=88.0,
            is_resolved=False,
        )
        session.add(test_alert)
        session.commit()
        test_alert_id = str(test_alert.id)

    # 1. Query active alerts
    resp_active = client.get("/api/v1/alerts/active", headers=headers)
    assert resp_active.status_code == 200
    alerts_list = resp_active.json()
    assert any(a["alert_id"] == test_alert_id for a in alerts_list)

    # 2. Manually resolve alert
    resp_resolve = client.post(f"/api/v1/alerts/{test_alert_id}/resolve", headers=headers)
    assert resp_resolve.status_code == 200
    res_data = resp_resolve.json()
    assert res_data["is_resolved"] is True
    assert res_data["resolved_at"] is not None

    # Verify in DB
    with get_db_context(test_engine) as session:
        db_alert = session.query(Alert).filter(Alert.id == test_alert_id).first()
        assert db_alert.is_resolved is True


def test_business_owner_rejected_from_route_and_alert_management(seeded_client):
    """Verify that a BUSINESS_OWNER cannot access route generation or fleet-wide alerts."""
    client, test_engine = seeded_client

    with get_db_context(test_engine) as session:
        owner = session.query(User).filter(User.role == UserRole.BUSINESS_OWNER).first()
        owner_email = owner.email

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": owner_email, "password": OWNER_PASSWORD},
    )
    owner_token = login_resp.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    resp_routes = client.post("/api/v1/routes/generate-today", headers=owner_headers)
    assert resp_routes.status_code == 403

    resp_alerts = client.get("/api/v1/alerts/active", headers=owner_headers)
    assert resp_alerts.status_code == 403
