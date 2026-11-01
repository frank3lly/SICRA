# Subspec 301: FastAPI Architecture, Security, and Free-Tier Cloud Packaging

> **Stage:** `300_etapa_backend_api_y_rutas`  
> **Subspec ID:** `301`  
> **Deliverable:** FastAPI Application Architecture, JWT/RBAC Security Layer, Free Cloud Platform Evaluation, Multi-Stage Dockerfile, and `render.yaml` Blueprint  
> **Target Path:** `src/main.py`, `src/security/`, `Dockerfile`, `docker-compose.yml`, `render.yaml`  
> **Status:** Executable Implementation Prompt  

---

## 1. Definitive Cloud Architecture Decision

To ensure high availability, zero maintenance costs, and persistent storage without data loss, the deployment architecture is officially decided as follows:

```
                      SICRA 100% FREE PRODUCTION TOPOLOGY

    ┌─────────────────────────────────┐
    │   ESP32 IoT Physical Nodes      │
    └────────────────┬────────────────┘
                     │ HTTPS Telemetry (POST /api/v1/telemetry/ingest)
                     ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │  RENDER WEB SERVICE (Backend API & ML Engine)                   │
    │  - Multi-stage Docker container (python:3.12-slim)              │
    │  - FastAPI ASGI application (Uvicorn single worker)             │
    │  - IoT Ingest, 80% Capacity Alert Service, 2-Opt Route Engine   │
    │  - Lazy-loaded ML Inference Engine (< 512 MB RAM footprint)     │
    └───────────────┬─────────────────────────────────▲───────────────┘
                    │                                 │
     SQLAlchemy     │ SSL Connection                  │ HTTPS REST API
     Connection     │ Pool                            │ (JWT Auth / RBAC)
                    ▼                                 │
    ┌─────────────────────────────────┐   ┌───────────┴─────────────────┐
    │  NEON SERVERLESS POSTGRESQL     │   │  RENDER STATIC SITE         │
    │  (Database Layer)               │   │  (Frontend Web Dashboard)   │
    │  - PostgreSQL 16 Managed DB     │   │  - Single Page App (SPA)    │
    │  - Perpetual Free Tier (No Wipe)│   │  - Global CDN Distribution  │
    │  - Stores all entities & logs   │   │  - ZERO sleep / Instant load│
    └─────────────────────────────────┘   └─────────────────────────────┘
```


---

## 2. Containerization and Render Deployment Blueprint

### 2.1. Multi-Stage Dockerfile (`Dockerfile`)

```dockerfile
# Stage 1: Build & Dependency Wheel Cache
FROM python:3.12-slim AS builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# Stage 2: Lean Production Runtime (< 512 MB RAM Footprint)
FROM python:3.12-slim AS runner

WORKDIR /app

# Install wheels from builder
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Create non-privileged user for security
RUN addgroup --system sicragroup && adduser --system --group sicrauser

# Copy application source and models
COPY src/ /app/src/
COPY data/ /app/data/
COPY alembic/ /app/alembic/
COPY alembic.ini /app/alembic.ini

# Grant execution permissions
RUN chown -R sicrauser:sicragroup /app

USER sicrauser

# Render dynamically injects $PORT (default 10000)
ENV PORT=10000
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE ${PORT}

# Startup command: Run lightweight single-worker uvicorn
CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT} --workers 1
```

### 2.2. Render Blueprint Specification (`render.yaml`)

```yaml
services:
  # 1. Backend Web Service (FastAPI + ML Engine)
  - type: web
    name: sicra-api
    env: docker
    plan: free
    region: ohio
    dockerfilePath: Dockerfile
    healthCheckPath: /health
    envVars:
      - key: ENVIRONMENT
        value: production
      - key: DATABASE_URL
        sync: false # User pastes their free Neon PostgreSQL connection string here
      - key: JWT_SECRET_KEY
        generateValue: true
      - key: JWT_ALGORITHM
        value: HS256
      - key: ACCESS_TOKEN_EXPIRE_MINUTES
        value: 1440
      - key: AUTO_SEED_IF_EMPTY
        value: "true"

  # 2. Frontend Web Application (Dashboard & Map)
  - type: static
    name: sicra-web
    env: static
    plan: free
    region: ohio
    buildCommand: npm install && npm run build # Or static build command
    staticPublishPath: ./dist
    envVars:
      - key: VITE_API_URL
        fromService:
          type: web
          name: sicra-api
          property: host
```

---

## 3. Core Application Architecture (`src/main.py`)

* **FastAPI Application Factory:**
  * Configures application lifespan (`@asynccontextmanager`) to:
    1. Initialize database tables via SQLAlchemy / Alembic.
    2. Check if the database is unpopulated; if `AUTO_SEED_IF_EMPTY=true`, execute the Dominican Republic food business seeds (Subspec 102).
    3. Warm up the Stage 200 ML Inference Engine in a background thread to prevent cold-start request latency.
* **CORS Middleware:**
  * Whitelists localhost, staging ports, and cloud web client origins (Stage 400).
* **Global Health Check (`GET /health`):**
  * Returns JSON status: `{"status": "healthy", "service": "sicra-api", "version": "1.0.0", "database": "connected"}`.

---

## 4. Security, JWT Authentication, and RBAC (`src/security/`)

### 4.1. Password Hashing and Token Engine (`src/security/tokens.py`)

* Password hashing using `passlib.context.CryptContext(schemes=["bcrypt"])`.
* JWT Generation using `python-jose`:
  * Claims: `{"sub": user.email, "role": user.role, "business_id": user.business_id, "exp": ...}`.

### 4.2. Dependency Injection and Role Guard (`src/security/dependencies.py`)

* `get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User`:
  * Validates token signature, expiration, and user active status.
* `require_role(required_roles: List[UserRole])`:
  * Enforces Role-Based Access Control:
    * Rejects requests with HTTP 403 Forbidden if user role is insufficient.
* **Data Isolation Safeguard:**
  * If `role == UserRole.BUSINESS_OWNER`, intercept requests to ensure the user can **only query data where `business_id == current_user.business_id`** (strictly preventing access to neighboring competitors' telemetry).

---

## 5. Verification and Test Criteria (`tests/test_cloud_and_auth.py`)

1. **Docker Build Test:**
   * Run `docker build -t sicra-backend:test .` and verify the image size remains under **600 MB** and builds without compilation errors.
2. **Healthcheck Verification:**
   * Request `GET /health` and assert HTTP 200 OK with database connection confirmed.
3. **Authentication & RBAC Enforcement:**
   * Test `/api/v1/auth/login` with seeded admin and business owner credentials.
   * Verify that a `BUSINESS_OWNER` user is rejected with HTTP 403 when trying to access admin-only or collector-only routes.
   * Verify that a `BUSINESS_OWNER` cannot inspect container telemetries belonging to a different `business_id`.
