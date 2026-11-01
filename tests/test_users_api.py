"""Unit and integration tests for user management API endpoints."""

import pytest
from fastapi.testclient import TestClient

from src.database.seed import ADMIN_PASSWORD, COLLECTOR_PASSWORD, seed_database
from src.database.session import get_db, get_db_context, get_engine, init_db
from src.main import app
from src.models.entities import Business, User
from src.models.enums import UserRole


@pytest.fixture(scope="module")
def client_and_engine(tmp_path_factory):
    """Provide a TestClient with a freshly initialized and seeded SQLite database."""
    test_dir = tmp_path_factory.mktemp("users_test")
    test_db_url = f"sqlite:///{test_dir}/test_users.db"
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


def test_admin_create_admin_and_collector_users(client_and_engine):
    """Admin can create new ADMIN and COLLECTOR user accounts."""
    client, _ = client_and_engine

    # 1. Login as Admin
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sicra.do", "password": ADMIN_PASSWORD},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create an ADMIN user
    admin_payload = {
        "full_name": "Supervisor Técnico",
        "email": "supervisor.tech@sicra.do",
        "password": "SecurePassword123!",
        "role": "ADMIN",
    }
    res = client.post("/api/v1/users/", json=admin_payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "supervisor.tech@sicra.do"
    assert data["full_name"] == "Supervisor Técnico"
    assert data["role"] == "ADMIN"
    assert "hashed_password" not in data
    assert "password" not in data

    # 3. Create a COLLECTOR user
    collector_payload = {
        "full_name": "Chofer Ruta Norte",
        "email": "chofer.norte@reoil.do",
        "password": "CollectorSecure123!",
        "role": "COLLECTOR",
    }
    res2 = client.post("/api/v1/users/", json=collector_payload, headers=headers)
    assert res2.status_code == 201
    data2 = res2.json()
    assert data2["email"] == "chofer.norte@reoil.do"
    assert data2["role"] == "COLLECTOR"


def test_admin_create_business_owner_user(client_and_engine):
    """Admin can create a BUSINESS_OWNER user bound to an existing establishment."""
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
        biz_name = biz.name

    payload = {
        "full_name": "Gerente Cocina Central",
        "email": "gerente.cocina@restaurante.do",
        "password": "KitchenOwner123!",
        "role": "BUSINESS_OWNER",
        "business_id": biz_id,
    }
    res = client.post("/api/v1/users/", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "gerente.cocina@restaurante.do"
    assert data["role"] == "BUSINESS_OWNER"
    assert data["business_id"] == biz_id
    assert data["business_name"] == biz_name


def test_create_user_duplicate_email_fails(client_and_engine):
    """Attempting to create a user with an existing email returns 400."""
    client, _ = client_and_engine

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sicra.do", "password": ADMIN_PASSWORD},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "full_name": "Duplicado Intencional",
        "email": "admin@sicra.do",  # already exists from seed
        "password": "AnyPassword123!",
        "role": "ADMIN",
    }
    res = client.post("/api/v1/users/", json=payload, headers=headers)
    assert res.status_code == 400
    assert "ya se encuentra registrado" in res.json()["detail"]


def test_create_business_owner_missing_business_id_fails(client_and_engine):
    """Role BUSINESS_OWNER requires business_id; returns 422 if missing."""
    client, _ = client_and_engine

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sicra.do", "password": ADMIN_PASSWORD},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "full_name": "Dueño Sin Negocio",
        "email": "owner.missing@restaurante.do",
        "password": "Password123!",
        "role": "BUSINESS_OWNER",
        "business_id": None,
    }
    res = client.post("/api/v1/users/", json=payload, headers=headers)
    assert res.status_code == 422


def test_create_user_forbidden_for_collector(client_and_engine):
    """Non-admin users cannot create accounts (403 Forbidden)."""
    client, _ = client_and_engine

    # Login as Collector
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "operaciones@reoil.do", "password": COLLECTOR_PASSWORD},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "full_name": "Intento Ilícito",
        "email": "intento@reoil.do",
        "password": "Password123!",
        "role": "COLLECTOR",
    }
    res = client.post("/api/v1/users/", json=payload, headers=headers)
    assert res.status_code == 403


def test_list_users_as_admin(client_and_engine):
    """Admin can list all platform users."""
    client, _ = client_and_engine

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sicra.do", "password": ADMIN_PASSWORD},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/users/", headers=headers)
    assert res.status_code == 200
    users = res.json()
    assert isinstance(users, list)
    assert len(users) > 0
    # Every user item should have essential fields and no password hash
    first = users[0]
    assert "email" in first
    assert "full_name" in first
    assert "role" in first
    assert "hashed_password" not in first
