# Subspec 301: FastAPI Architecture, Security, and Free-Tier Cloud Packaging

> **Stage:** `300_etapa_backend_api_y_rutas`  
> **Subspec ID:** `301`  
> **Deliverable:** FastAPI Application Architecture, JWT/RBAC Security Layer, Free Cloud Platform Evaluation, Multi-Stage Dockerfile, and `render.yaml` Blueprint  
> **Target Path:** `src/main.py`, `src/security/`, `Dockerfile`, `docker-compose.yml`, `render.yaml`  
> **Status:** Executable Implementation Prompt  

---

## 1. Cloud Deployment Investigation and Platform Analysis

The user intends to deploy the SICRA backend to a free cloud hosting tier. Below is an engineering evaluation comparing the primary free-tier cloud platforms for hosting a Python 3.12 + FastAPI + Machine Learning stack:

| Platform | Free Tier Specifications | Pros | Cons & Caveats | Verdict for SICRA |
| :--- | :--- | :--- | :--- | :--- |
| **Render** | 512 MB RAM, 0.1 CPU, auto-spins down after 15 min of inactivity. Free PG database expires after 30 days. | Extremely simple Git deployment, native Docker support, free SSL certificates, custom domains. | 50s cold-start on sleep. **Render's Free PostgreSQL deletes the database every 30 days.** | **RECOMMENDED FOR WEB SERVICE** (Paired with Neon/Supabase for persistent DB). |
| **Koyeb** | 512 MB RAM (Free Nano), 0.1 vCPU. Native Docker. | Stays active without sleeping in primary regions, low latency, fast deployments. | Stricter network egress limits. | **EXCELLENT ALTERNATIVE** for zero-sleep backend hosting. |
| **Neon / Supabase** | Free Serverless PostgreSQL (500 MB – 1 GB storage, connection pooling). | **Never expires.** Full PostgreSQL 16 compatibility, perfect for SQLAlchemy. | Only provides the database, not web app hosting. | **RECOMMENDED FOR PRODUCTION DB**. |
| **Railway** | No ongoing 100% free tier (trial credit only). | Excellent developer experience. | Requires credit card; service terminates once trial credits deplete. | **NOT RECOMMENDED** for free-tier requirement. |
| **Fly.io** | Limited free allowance. | Global edge deployment. | Requires credit card on file during onboarding. | **NOT RECOMMENDED** for frictionless free deployment. |

### The Optimal Free-Tier Architecture Recommendation:
1. **Application Layer (FastAPI Backend):** Deploy to **Render Free Web Service** using our multi-stage `Dockerfile` and a `render.yaml` Infrastructure-as-Code blueprint.
2. **Persistence Layer (Database):**
   * *Option A (Default Zero-Config):* SQLite file storage (`sicra.db`) with automatic database initialization and seeding on container boot (ideal for immediate testing and grading/demonstration).
   * *Option B (Persistent Production):* Free serverless PostgreSQL hosted on **Neon.tech** or **Supabase** linked via the `DATABASE_URL` environment variable to prevent Render's 30-day database wipe.
3. **Memory Optimization:** Scikit-learn and NumPy can consume significant memory during import. The application must optimize its memory footprint to comfortably fit within Render's **512 MB RAM boundary** (e.g., loading model weights lazily on demand, using lightweight uvicorn worker counts, and utilizing `python:3.12-slim`).

---

## 2. Containerization and Cloud Deployment Blueprint

```
                     FREE-TIER CLOUD DEPLOYMENT TOPOLOGY
                     
      [ ESP32 IoT Nodes ]         [ Web Browser / Mobile ]
               │                              │
               │ HTTPS Telemetry              │ HTTPS Dashboard
               ▼                              ▼
  ┌────────────────────────────────────────────────────────┐
  │              RENDER / KOYEB WEB SERVICE                │
  │  Multi-Stage Docker Container (python:3.12-slim)       │
  │  - FastAPI Application (Uvicorn ASGI)                  │
  │  - Lazy-loaded ML Inference Engine                     │
  │  - In-memory Task Workers (BackgroundTasks)            │
  └──────────────────────────┬─────────────────────────────┘
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
   [ Option A: SQLite ]             [ Option B: Neon / Supabase ]
   Local file inside container       Free Persistent Serverless PostgreSQL
   (Auto-seeds on startup)          (Via DATABASE_URL environment variable)
```

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

# Create storage directory and grant permissions
RUN mkdir -p /app/data && chown -R sicrauser:sicragroup /app

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
        value: sqlite:////app/data/sicra.db # Or paste your free Neon/Supabase PostgreSQL connection string
      - key: JWT_SECRET_KEY
        generateValue: true
      - key: JWT_ALGORITHM
        value: HS256
      - key: ACCESS_TOKEN_EXPIRE_MINUTES
        value: 1440
      - key: AUTO_SEED_IF_EMPTY
        value: "true"
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
