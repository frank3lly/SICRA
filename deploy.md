# SICRA Cloud Deployment Guide (100% Free Production Tier)

> **Target Architecture:** Render Web Service (FastAPI + ML Engine) + Neon Serverless PostgreSQL (Managed DB) + Render Static Site (Frontend SPA)  
> **Cost:** \$0.00 / month (Perpetual Free Tiers, Zero Data Wipe)  
> **Repository:** `sicra`  

---

## 1. Cloud Architecture Overview

```
                          100% FREE PRODUCTION TOPOLOGY

    ┌─────────────────────────────────┐
    │     ESP32 IoT Smart Nodes       │
    └────────────────┬────────────────┘
                     │ HTTPS (POST /api/v1/telemetry/ingest)
                     ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │  RENDER WEB SERVICE (Backend API & Predictive ML Engine)        │
    │  - Multi-stage Docker container (python:3.12-slim)              │
    │  - Memory footprint: < 512 MB RAM (Free plan compatible)        │
    │  - Automatic DB tables creation & auto-seeding on first launch  │
    └───────────────┬─────────────────────────────────▲───────────────┘
                    │                                 │
     SQLAlchemy     │ SSL Connection                  │ HTTPS REST API
     Connection     │ Pool (-pooler)                  │ (JWT Auth / RBAC)
                    ▼                                 │
    ┌─────────────────────────────────┐   ┌───────────┴─────────────────┐
    │  NEON SERVERLESS POSTGRESQL     │   │  RENDER STATIC SITE         │
    │  (Database Layer)               │   │  (Web Dashboard & Route Map)│
    │  - PostgreSQL 16 Managed DB     │   │  - Single Page App (SPA)    │
    │  - Never wiped (unlike Render)  │   │  - Global CDN Distribution  │
    │  - 0.5 GB storage + pooling     │   │  - ZERO sleep / Instant load│
    └─────────────────────────────────┘   └─────────────────────────────┘
```

---

## 2. Prerequisites

1. A **GitHub** or **GitLab** account containing the `sicra` codebase.
2. A free account on **Neon** ([https://neon.tech](https://neon.tech)).
3. A free account on **Render** ([https://render.com](https://render.com)).

---

## 3. Step 1: Provision Managed PostgreSQL on Neon

Render's free PostgreSQL tier automatically wipes and deletes all data after 30 days. Neon provides a **perpetual free PostgreSQL tier** that never expires and includes automated connection pooling.

1. Log into your [Neon Console](https://console.neon.tech).
2. Click **Create Project**:
   * **Project Name:** `sicra-db-production`
   * **Postgres Version:** `16`
   * **Region:** `US East (Ohio)` *(matches Render's Ohio region for minimal network latency)*
3. In the project dashboard under **Connection Details**:
   * Select **Connection pooling** (`-pooler`).
   * Copy the connection string. It will look like:
     ```text
     postgresql://sicrauser:MySecretPassword@ep-cool-cloud-123456-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require
     ```
   *(Save this string securely; you will use it as `DATABASE_URL` in Render).*

---

## 4. Step 2: Deploy Backend Web Service on Render

### Option A: Automated Infrastructure-as-Code Deployment via Blueprint (Recommended)

1. Ensure `render.yaml` is in the root of your repository.
2. In the [Render Dashboard](https://dashboard.render.com), click **New +** and select **Blueprint**.
3. Connect your Git repository.
4. Render will detect `render.yaml` and prompt you for the un-synced variables:
   * **`DATABASE_URL`**: Paste your Neon PostgreSQL connection string.
   * Render will automatically generate a cryptographically strong `JWT_SECRET_KEY`.
5. Click **Apply**. Render will automatically build the multi-stage Docker container and provision the web service.

---

### Option B: Manual Web Service Setup via Docker

If you prefer deploying manually through the UI:

1. Click **New +** $\to$ **Web Service**.
2. Connect your repository.
3. Configure settings:
   * **Name:** `sicra-api`
   * **Region:** `Ohio (US East)`
   * **Environment:** `Docker`
   * **Branch:** `main` (or your active release branch)
   * **Dockerfile Path:** `Dockerfile`
   * **Instance Type:** `Free`
4. Expand **Advanced Settings** and set **Health Check Path** to `/health`.
5. Under **Environment Variables**, add:

| Key | Value / Description |
| :--- | :--- |
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | Your Neon connection string (e.g. `postgresql://...@...-pooler.neon.tech/neondb?sslmode=require`) |
| `JWT_SECRET_KEY` | Long random secret string (e.g. `openssl rand -hex 32`) |
| `JWT_ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` (24 hours) |
| `AUTO_SEED_IF_EMPTY` | `true` |
| `PORT` | `10000` *(Render injects this dynamically)* |

6. Click **Create Web Service**.

---

## 5. Step 3: Database Initialization and Pilot Data Seeding

The application handles schema creation and pilot data population automatically:

1. When the container starts on Render, the application lifespan (`src/main.py`) executes:
   * `init_db()`: Automatically creates all relational tables (`businesses`, `containers`, `telemetries`, `predictions`, `alerts`, `collection_routes`, `users`).
   * If `AUTO_SEED_IF_EMPTY=true` and the database is unpopulated, it executes the Dominican Republic food business seeds (`src/database/seed.py`).
2. Pre-seeded Accounts:
   * **Administrator:** `admin@sicra.do` / `AdminSecure2026!`
   * **Collector Logistics:** `operaciones@reoil.do` / `CollectorSecure2026!`
   * **Business Owners:** `picapollo.expreso@sicra.do` / `OwnerSecure2026!` (and remaining pilot food establishments)

---

## 6. Step 4: Verification and Smoke Testing

Once Render shows your service as **Live**, perform the following smoke tests using `curl`:

### 1. Healthcheck Verification
```bash
curl -i https://sicra-api.onrender.com/health
```
**Expected Response (HTTP 200 OK):**
```json
{
  "status": "healthy",
  "service": "sicra-api",
  "version": "1.0.0",
  "database": "connected"
}
```

### 2. Admin Authentication & Token Issuance
```bash
curl -X POST https://sicra-api.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@sicra.do", "password": "AdminSecure2026!"}'
```
**Expected Response (HTTP 200 OK):**
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "user": {
    "email": "admin@sicra.do",
    "role": "ADMIN",
    "is_active": true
  }
}
```

### 3. IoT Telemetry Ingestion Ping
```bash
curl -X POST https://sicra-api.onrender.com/api/v1/telemetry/ingest \
  -H "Content-Type: application/json" \
  -H "X-Device-Token: sicra_live_tok_spm_biz_001_8b3a7dc92e104f5a" \
  -d '{
    "readings": [
      {
        "timestamp": "2026-11-01T10:00:00Z",
        "raw_weight_kg": 25.5,
        "battery_mv": 3950,
        "is_synthetic": false
      }
    ]
  }'
```
**Expected Response (HTTP 200 OK):**
```json
{
  "status": "success",
  "accepted_count": 1,
  "duplicate_count": 0,
  "current_fill_percentage": 20.65
}
```

### 4. Environmental Compliance Stats (Ley 225-20)
```bash
curl https://sicra-api.onrender.com/api/v1/stats/environmental \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

---

## 7. Step 5: Deploy Frontend Web Application on Render Static Site

Unlike backend services, **Render Static Sites never spin down or sleep**, ensuring instant loading on a global CDN.

1. In Render Dashboard, click **New +** $\to$ **Static Site**.
2. Connect your Git repository.
3. Configure settings:
   * **Name:** `sicra-web`
   * **Build Command:** `npm install && npm run build`
   * **Publish Directory:** `dist`
4. Add Environment Variable:
   * `VITE_API_URL`: `https://sicra-api.onrender.com`
5. Click **Create Static Site**.

---

## 8. Free-Tier Optimizations & Troubleshooting

### Handling Render Free-Tier Cold Starts (Spin Down)
* On Render's free tier, web services spin down after 15 minutes of inactivity. When a new request arrives, a cold start takes approximately 30–45 seconds.
* **Keep-Alive Tip (Optional):** You can set up a free uptime monitor (e.g., [UptimeRobot](https://uptimerobot.com) or [cron-job.org](https://cron-job.org)) that pings `GET https://sicra-api.onrender.com/health` every 10 minutes to keep the container permanently warm.

### ESP32 Firmware Network Drops
* Smart containers running in disconnected environments will automatically buffer up to 1,000 readings in SPIFFS/LittleFS flash.
* When connection recovers, the firmware posts the buffered batch array to `POST /api/v1/telemetry/ingest`. The backend deduplicates timestamps and commits only new readings.

### Database Connection Drops on Neon
* Neon serverless compute branches pause after 5 minutes of zero queries.
* Our engine includes `pool_pre_ping=True` and `pool_recycle=300` in `src/database/session.py`. SQLAlchemy will automatically test and re-establish the connection without throwing application-level 500 errors.
