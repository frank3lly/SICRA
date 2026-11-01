"""Verification and test suite for FastAPI architecture, security, RBAC, and cloud packaging."""

from datetime import datetime, timedelta, timezone
import os
import yaml
import pytest
from fastapi.testclient import TestClient
from jose import jwt

from src.database.seed import (
    ADMIN_PASSWORD,
    COLLECTOR_PASSWORD,
    OWNER_PASSWORD,
    seed_database,
)
from src.database.session import get_db_context, get_engine, init_db
from src.main import app
from src.models.entities import Business, Container, User
from src.models.enums import UserRole
from src.security.tokens import (
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
    create_access_token,
    hash_password,
    verify_password,
)


@pytest.fixture(scope="module")
def seeded_client(tmp_path_factory):
    """Provide a TestClient with a fully populated test database."""
    test_dir = tmp_path_factory.mktemp("cloud_auth_test")
    test_db_url = f"sqlite:///{test_dir}/sicra_auth_test.db"
    test_engine = get_engine(test_db_url)

    # Initialize and seed tables
    init_db(test_engine)
    seed_database(target_engine=test_engine, quiet=True)

    # Override database dependency
    from src.database.session import get_db

    def override_get_db():
        with get_db_context(test_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    yield client, test_engine

    app.dependency_overrides.clear()


# ==============================================================================
# 1. Healthcheck Endpoint Verification
# ==============================================================================

def test_healthcheck_endpoint(seeded_client):
    """Verify GET /health returns HTTP 200 with service metadata and database status."""
    client, _ = seeded_client
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["service"] == "sicra-api"
    assert payload["version"] == "1.0.0"
    assert payload["database"] == "connected"


# ==============================================================================
# 2. Authentication and Token Issuance
# ==============================================================================

def test_admin_authentication_and_profile(seeded_client):
    """Verify admin login produces a valid JWT and /me returns admin profile."""
    client, _ = seeded_client
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sicra.do", "password": ADMIN_PASSWORD},
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["user"]["email"] == "admin@sicra.do"
    assert token_data["user"]["role"] == UserRole.ADMIN.value

    # Query /me with token
    token = token_data["access_token"]
    me_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == "admin@sicra.do"
    assert me_data["role"] == UserRole.ADMIN.value
    assert me_data["is_active"] is True


def test_collector_authentication_and_access(seeded_client):
    """Verify collector login and role claims."""
    client, _ = seeded_client
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "operaciones@reoil.do", "password": COLLECTOR_PASSWORD},
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert token_data["user"]["role"] == UserRole.COLLECTOR.value

    token = token_data["access_token"]

    # Collector can access collector-only route
    col_resp = client.get(
        "/api/v1/auth/collector-only",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert col_resp.status_code == 200
    assert col_resp.json()["status"] == "ok"

    # Collector cannot access admin-only route
    adm_resp = client.get(
        "/api/v1/auth/admin-only",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert adm_resp.status_code == 403


def test_business_owner_authentication(seeded_client):
    """Verify business owner login produces correct business_id and role."""
    client, test_engine = seeded_client

    with get_db_context(test_engine) as session:
        owner = session.query(User).filter(User.role == UserRole.BUSINESS_OWNER).first()
        assert owner is not None
        owner_email = owner.email
        owner_business_id = owner.business_id

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": owner_email, "password": OWNER_PASSWORD},
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert token_data["user"]["role"] == UserRole.BUSINESS_OWNER.value
    assert token_data["user"]["business_id"] == owner_business_id


def test_invalid_credentials_rejected(seeded_client):
    """Verify authentication fails for wrong passwords or non-existent emails."""
    client, _ = seeded_client

    # Wrong password
    resp1 = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sicra.do", "password": "WrongPassword123!"},
    )
    assert resp1.status_code == 401

    # Non-existent user
    resp2 = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@sicra.do", "password": "SomePassword123!"},
    )
    assert resp2.status_code == 401

    # Empty payload
    resp3 = client.post("/api/v1/auth/login", json={})
    assert resp3.status_code == 400


# ==============================================================================
# 3. RBAC & Data Isolation Enforcement
# ==============================================================================

def test_rbac_business_owner_rejected_from_admin_and_collector_routes(seeded_client):
    """Verify business owner receives HTTP 403 when accessing administrative endpoints."""
    client, test_engine = seeded_client

    with get_db_context(test_engine) as session:
        owner = session.query(User).filter(User.role == UserRole.BUSINESS_OWNER).first()
        owner_email = owner.email

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": owner_email, "password": OWNER_PASSWORD},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt admin-only endpoint
    resp_adm = client.get("/api/v1/auth/admin-only", headers=headers)
    assert resp_adm.status_code == 403
    assert "detail" in resp_adm.json()

    # Attempt collector-only endpoint
    resp_col = client.get("/api/v1/auth/collector-only", headers=headers)
    assert resp_col.status_code == 403


def test_business_data_isolation_safeguard(seeded_client):
    """Verify business owner can only query data matching their own business_id."""
    client, test_engine = seeded_client

    with get_db_context(test_engine) as session:
        owners = session.query(User).filter(User.role == UserRole.BUSINESS_OWNER).limit(2).all()
        assert len(owners) >= 2
        owner_a = owners[0]
        owner_b = owners[1]

        owner_a_email = owner_a.email
        owner_a_biz = owner_a.business_id
        owner_b_biz = owner_b.business_id

    # Login as Owner A
    login_a = client.post(
        "/api/v1/auth/login",
        json={"email": owner_a_email, "password": OWNER_PASSWORD},
    )
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Owner A requests their own business data -> Allowed (200)
    resp_own = client.get(f"/api/v1/auth/business-data/{owner_a_biz}", headers=headers_a)
    assert resp_own.status_code == 200
    assert resp_own.json()["status"] == "access_granted"

    # Owner A requests Owner B's business data -> Forbidden (403)
    resp_comp = client.get(f"/api/v1/auth/business-data/{owner_b_biz}", headers=headers_a)
    assert resp_comp.status_code == 403
    assert "Data isolation prevents access" in resp_comp.json()["detail"]


def test_container_telemetry_isolation(seeded_client):
    """Verify business owner cannot inspect container telemetry belonging to another business."""
    client, test_engine = seeded_client

    with get_db_context(test_engine) as session:
        owners = session.query(User).filter(User.role == UserRole.BUSINESS_OWNER).limit(2).all()
        owner_a = owners[0]
        owner_b = owners[1]

        # Get container for Business A and Business B
        container_a = session.query(Container).filter(Container.business_id == owner_a.business_id).first()
        container_b = session.query(Container).filter(Container.business_id == owner_b.business_id).first()

        assert container_a is not None
        assert container_b is not None

        owner_a_email = owner_a.email
        container_a_id = container_a.id
        container_b_id = container_b.id

    # Login as Owner A
    login_a = client.post(
        "/api/v1/auth/login",
        json={"email": owner_a_email, "password": OWNER_PASSWORD},
    )
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Owner A inspects own container -> Allowed (200)
    res_a = client.get(f"/api/v1/auth/container-telemetry-check/{container_a_id}", headers=headers_a)
    assert res_a.status_code == 200
    assert res_a.json()["status"] == "access_granted"

    # Owner A inspects container of Business B -> Forbidden (403)
    res_b = client.get(f"/api/v1/auth/container-telemetry-check/{container_b_id}", headers=headers_a)
    assert res_b.status_code == 403
    assert "Data isolation prevents access" in res_b.json()["detail"]


# ==============================================================================
# 4. Token Cryptography, Expiration, and Tampering
# ==============================================================================

def test_tampered_and_expired_token(seeded_client):
    """Verify invalid or expired tokens are rejected with HTTP 401."""
    client, _ = seeded_client

    # Tampered signature
    tampered_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbkBzaWNyYS5kbyJ9.invalid_signature"
    resp_tampered = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )
    assert resp_tampered.status_code == 401

    # Expired token
    expired_payload = {
        "sub": "admin@sicra.do",
        "role": UserRole.ADMIN.value,
        "exp": datetime.now(timezone.utc) - timedelta(minutes=10),
    }
    expired_token = jwt.encode(expired_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    resp_expired = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert resp_expired.status_code == 401


def test_cors_middleware(seeded_client):
    """Verify CORS preflight and allowed origins respond appropriately."""
    client, _ = seeded_client

    response = client.get(
        "/health",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


# ==============================================================================
# 5. Cloud Platform Blueprint and Packaging Integrity
# ==============================================================================

def test_render_blueprint_integrity():
    """Verify render.yaml contains the required web service and static site topology."""
    blueprint_path = "render.yaml"
    assert os.path.exists(blueprint_path), "render.yaml must exist at project root"

    with open(blueprint_path, "r", encoding="utf-8") as f:
        blueprint = yaml.safe_load(f)

    assert "services" in blueprint
    services = {s["name"]: s for s in blueprint["services"]}

    # 1. Backend Web Service
    assert "sicra-api" in services
    api = services["sicra-api"]
    assert api["type"] == "web"
    assert api["env"] == "docker"
    assert api["healthCheckPath"] == "/health"
    env_vars = {v["key"]: v for v in api["envVars"]}
    assert "DATABASE_URL" in env_vars
    assert "JWT_SECRET_KEY" in env_vars
    assert "JWT_ALGORITHM" in env_vars
    assert "ACCESS_TOKEN_EXPIRE_MINUTES" in env_vars
    assert "AUTO_SEED_IF_EMPTY" in env_vars

    # 2. Frontend Static Site
    assert "sicra-web" in services
    web = services["sicra-web"]
    assert web["type"] == "static"
    assert web["env"] == "static"


def test_dockerfile_multi_stage_structure():
    """Verify Dockerfile contains builder and lean runner stages with security constraints."""
    dockerfile_path = "Dockerfile"
    assert os.path.exists(dockerfile_path), "Dockerfile must exist at project root"

    with open(dockerfile_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Multi-stage check
    assert "FROM python:3.12-slim AS builder" in content
    assert "FROM python:3.12-slim AS runner" in content
    # Non-root user check
    assert "sicrauser" in content
    assert "USER sicrauser" in content
    # Port configuration
    assert "EXPOSE ${PORT}" in content or "EXPOSE 10000" in content
    # CMD entrypoint
    assert "CMD" in content
    assert "uvicorn src.main:app" in content
