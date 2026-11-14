"""Tests for Complete Administrative CRUD operations on Users, Businesses, and Containers."""

import pytest
from fastapi.testclient import TestClient

from src.database.seed import ADMIN_PASSWORD, COLLECTOR_PASSWORD, seed_database
from src.database.session import get_db, get_db_context, get_engine, init_db
from src.main import app


@pytest.fixture(scope="module")
def client_and_engine(tmp_path_factory):
    """Provide a TestClient with a freshly initialized and seeded SQLite database."""
    test_dir = tmp_path_factory.mktemp("crud_test")
    test_db_url = f"sqlite:///{test_dir}/test_crud.db"
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


@pytest.fixture(scope="module")
def admin_headers(client_and_engine) -> dict:
    """Generate authorization headers for seeded Admin user."""
    client, _ = client_and_engine
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sicra.do", "password": ADMIN_PASSWORD},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def collector_headers(client_and_engine) -> dict:
    """Generate authorization headers for seeded Collector user."""
    client, _ = client_and_engine
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "operaciones@reoil.do", "password": COLLECTOR_PASSWORD},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_business_crud(client_and_engine, admin_headers: dict, collector_headers: dict):
    """Test full CRUD on businesses including Admin authorization."""
    client, _ = client_and_engine

    # 1. Create Business
    payload = {
        "name": "Comedor CRUD Test",
        "business_type": "RESTAURANTE",
        "num_fryers": 3,
        "avg_daily_customers": 180,
        "latitude": 18.45,
        "longitude": -69.30,
        "address": "Calle Principal #12",
        "city": "San Pedro de Macorís",
        "contact_name": "Carlos Gomez",
        "phone": "809-555-0101",
        "is_active": True,
    }
    create_res = client.post("/api/v1/businesses/", json=payload, headers=admin_headers)
    assert create_res.status_code == 201
    biz_id = create_res.json()["id"]

    # 2. Get Detail
    detail_res = client.get(f"/api/v1/businesses/{biz_id}", headers=admin_headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["name"] == "Comedor CRUD Test"

    # 3. Update Business (PUT)
    update_payload = {
        "name": "Comedor CRUD Actualizado",
        "num_fryers": 5,
        "phone": "809-555-9999",
        "is_active": False,
    }
    update_res = client.put(f"/api/v1/businesses/{biz_id}", json=update_payload, headers=admin_headers)
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Comedor CRUD Actualizado"
    assert update_res.json()["num_fryers"] == 5
    assert update_res.json()["is_active"] is False

    # Non-admin cannot update
    forbidden_res = client.put(f"/api/v1/businesses/{biz_id}", json=update_payload, headers=collector_headers)
    assert forbidden_res.status_code == 403

    # 4. Delete Business (DELETE)
    del_res = client.delete(f"/api/v1/businesses/{biz_id}", headers=admin_headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # Verify deleted
    verify_res = client.get(f"/api/v1/businesses/{biz_id}", headers=admin_headers)
    assert verify_res.status_code == 404


def test_container_crud(client_and_engine, admin_headers: dict, collector_headers: dict):
    """Test full CRUD on smart containers."""
    client, _ = client_and_engine

    # Setup parent business first
    biz_payload = {
        "name": "Pollo Container Test",
        "business_type": "PICA_POLLO",
        "num_fryers": 2,
        "avg_daily_customers": 200,
        "latitude": 18.46,
        "longitude": -69.31,
        "address": "Av. Duarte #45",
    }
    biz_res = client.post("/api/v1/businesses/", json=biz_payload, headers=admin_headers)
    assert biz_res.status_code == 201
    biz_id = biz_res.json()["id"]

    # 1. Create Container
    payload = {
        "business_id": biz_id,
        "capacity_liters": 50.0,
        "tare_weight_kg": 3.8,
        "oil_density_kg_l": 0.92,
    }
    create_res = client.post("/api/v1/containers/", json=payload, headers=admin_headers)
    assert create_res.status_code == 201
    container_id = create_res.json()["id"]

    # 2. Get Detail
    detail_res = client.get(f"/api/v1/containers/{container_id}", headers=admin_headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["capacity_liters"] == 50.0

    # 3. Update Container (PUT)
    update_payload = {
        "capacity_liters": 100.0,
        "tare_weight_kg": 6.5,
        "status": "MAINTENANCE",
    }
    update_res = client.put(f"/api/v1/containers/{container_id}", json=update_payload, headers=admin_headers)
    assert update_res.status_code == 200
    assert update_res.json()["capacity_liters"] == 100.0
    assert update_res.json()["tare_weight_kg"] == 6.5
    assert update_res.json()["status"] == "MAINTENANCE"

    # Non-admin cannot update
    forbidden_res = client.put(f"/api/v1/containers/{container_id}", json=update_payload, headers=collector_headers)
    assert forbidden_res.status_code == 403

    # 4. Delete Container (DELETE)
    del_res = client.delete(f"/api/v1/containers/{container_id}", headers=admin_headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # Verify deleted
    verify_res = client.get(f"/api/v1/containers/{container_id}", headers=admin_headers)
    assert verify_res.status_code == 404


def test_user_crud(client_and_engine, admin_headers: dict, collector_headers: dict):
    """Test full CRUD on users."""
    client, _ = client_and_engine

    # 1. Create User
    payload = {
        "full_name": "Usuario Para Modificar",
        "email": "user_modificar@sicra.do",
        "password": "Password123!",
        "role": "COLLECTOR",
    }
    create_res = client.post("/api/v1/users/", json=payload, headers=admin_headers)
    assert create_res.status_code == 201
    user_id = create_res.json()["id"]

    # 2. Get User Detail
    detail_res = client.get(f"/api/v1/users/{user_id}", headers=admin_headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["email"] == "user_modificar@sicra.do"

    # 3. Update User (PUT)
    update_payload = {
        "full_name": "Usuario Modificado Exitosamente",
        "email": "user_actualizado@sicra.do",
        "is_active": False,
    }
    update_res = client.put(f"/api/v1/users/{user_id}", json=update_payload, headers=admin_headers)
    assert update_res.status_code == 200
    assert update_res.json()["full_name"] == "Usuario Modificado Exitosamente"
    assert update_res.json()["email"] == "user_actualizado@sicra.do"
    assert update_res.json()["is_active"] is False

    # Non-admin cannot update
    forbidden_res = client.put(f"/api/v1/users/{user_id}", json=update_payload, headers=collector_headers)
    assert forbidden_res.status_code == 403

    # 4. Delete User (DELETE)
    del_res = client.delete(f"/api/v1/users/{user_id}", headers=admin_headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # Verify deleted
    verify_res = client.get(f"/api/v1/users/{user_id}", headers=admin_headers)
    assert verify_res.status_code == 404

    # Admin cannot delete their own account
    me_res = client.get("/api/v1/auth/me", headers=admin_headers)
    my_id = me_res.json()["id"]
    self_del = client.delete(f"/api/v1/users/{my_id}", headers=admin_headers)
    assert self_del.status_code == 400


def test_alert_delete(client_and_engine, admin_headers: dict, collector_headers: dict):
    """Test admin deletion of alerts."""
    client, _ = client_and_engine

    # Fetch alerts
    alerts_res = client.get("/api/v1/alerts/active", headers=admin_headers)
    assert alerts_res.status_code == 200
    alerts = alerts_res.json()
    if alerts:
        target_id = alerts[0]["id"]
        # Non-admin cannot delete
        col_res = client.delete(f"/api/v1/alerts/{target_id}", headers=collector_headers)
        assert col_res.status_code == 403

        # Admin can delete
        del_res = client.delete(f"/api/v1/alerts/{target_id}", headers=admin_headers)
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "deleted"

