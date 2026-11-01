"""Verification tests for container provisioning and ESP32 device token issuance."""

import pytest
from fastapi.testclient import TestClient

from src.database.seed import ADMIN_PASSWORD, COLLECTOR_PASSWORD, seed_database
from src.database.session import get_db, get_db_context, get_engine, init_db
from src.main import app
from src.models.entities import Business, Container


@pytest.fixture(scope="module")
def client_and_engine(tmp_path_factory):
    """Provide a TestClient with a freshly initialized and seeded SQLite database."""
    test_dir = tmp_path_factory.mktemp("container_test")
    test_db_url = f"sqlite:///{test_dir}/test_containers.db"
    test_engine = get_engine(test_db_url)

    init_db(test_engine)
    seed_database(target_engine=test_engine, quiet=True)

    def override_get_db():
        with get_db_context(test_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)

    yield test_client, test_engine

    app.dependency_overrides.clear()


def test_create_container_as_admin_generates_token(client_and_engine):
    """Verify that an Admin can provision a new container and obtain an ESP32 device token."""
    client, engine = client_and_engine

    # 1. Login as Admin
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sicra.do", "password": ADMIN_PASSWORD},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get an existing business
    with get_db_context(engine) as db:
        biz = db.query(Business).first()
        assert biz is not None
        biz_id = str(biz.id)

    # 3. Provision new container
    payload = {
        "business_id": biz_id,
        "capacity_liters": 50.0,
        "tare_weight_kg": 3.80,
        "oil_density_kg_l": 0.92,
    }
    create_res = client.post("/api/v1/containers/", json=payload, headers=headers)
    assert create_res.status_code == 201
    data = create_res.json()

    assert data["business_id"] == biz_id
    assert data["capacity_liters"] == 50.0
    assert data["tare_weight_kg"] == 3.80
    assert "device_token" in data
    assert data["device_token"].startswith("sicra_live_tok_")


def test_create_container_forbidden_for_non_admin(client_and_engine):
    """Verify that collectors cannot provision containers."""
    client, engine = client_and_engine

    # Login as Collector
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "operaciones@reoil.do", "password": COLLECTOR_PASSWORD},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with get_db_context(engine) as db:
        biz = db.query(Business).first()
        biz_id = str(biz.id)

    payload = {
        "business_id": biz_id,
        "capacity_liters": 20.0,
        "tare_weight_kg": 2.20,
        "oil_density_kg_l": 0.92,
    }
    create_res = client.post("/api/v1/containers/", json=payload, headers=headers)
    assert create_res.status_code == 403


def test_create_container_nonexistent_business_returns_404(client_and_engine):
    """Verify that attempting to provision for a missing business UUID returns 404."""
    client, _ = client_and_engine

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sicra.do", "password": ADMIN_PASSWORD},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "business_id": "00000000-0000-0000-0000-000000000000",
        "capacity_liters": 50.0,
        "tare_weight_kg": 3.80,
        "oil_density_kg_l": 0.92,
    }
    create_res = client.post("/api/v1/containers/", json=payload, headers=headers)
    assert create_res.status_code == 404


def test_create_small_3_liter_container(client_and_engine):
    """Verify that a small 3-liter container can be provisioned properly."""
    client, engine = client_and_engine

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sicra.do", "password": ADMIN_PASSWORD},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with get_db_context(engine) as db:
        biz = db.query(Business).first()
        assert biz is not None
        biz_id = str(biz.id)

    payload = {
        "business_id": biz_id,
        "capacity_liters": 3.0,
        "tare_weight_kg": 0.35,
        "oil_density_kg_l": 0.92,
    }
    create_res = client.post("/api/v1/containers/", json=payload, headers=headers)
    assert create_res.status_code == 201
    data = create_res.json()
    assert data["capacity_liters"] == 3.0
    assert data["tare_weight_kg"] == 0.35
    assert data["device_token"].startswith("sicra_live_tok_")
