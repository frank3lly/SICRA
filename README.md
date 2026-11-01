<p align="center">
  <img src="assets/sicra-logo-full.svg" alt="SICRA - Control y Recolección de Aceite" width="360" />
</p>

<p align="center">
  <strong>Intelligent Used Cooking Oil Monitoring and Collection System</strong><br />
  Universidad Central del Este (UCE) &middot; San Pedro de Macorís, Dominican Republic
</p>

---

## Overview

SICRA is an integrated IoT, predictive modeling, and logistics dispatch platform designed to modernize the management and circular recovery of used cooking oil (*Aceite de Cocina Usado* - ACU) across gastronomic businesses. By combining smart load-cell telemetry, machine learning volume forecasting, and dynamic vehicle routing, SICRA prevents urban drainage contamination and supports compliance with Dominican Environmental Law 225-20.

---

## System Architecture

```
                  IoT Load-Cell Nodes (ESP32)
                             │
                             ▼ [X-Device-Token]
        FastAPI REST API (Stage 300 / Python 3.12)
        ├── Neon Serverless PostgreSQL (Storage & Pooling)
        ├── Monte Carlo Simulation Engine (Stage 100)
        ├── GLM / Ensemble ML Engine (Stage 200)
        └── 2-Opt Vehicle Routing Optimization
                             │
                             ▼ [JWT / RBAC]
            React Web Dashboard (Stage 400 / Vite)
        ├── Admin Fleet Overview & Container Provisioning
        ├── Collector Route Map (Leaflet Geospatial)
        └── Business Owner Live Fill Meter & Environmental Impact
```

---

## Core Technologies

* **Backend & API:** FastAPI, SQLAlchemy 2.0, Pydantic v2, Uvicorn, Python-Jose (JWT), ReportLab.
* **Database Layer:** PostgreSQL 16 (Neon Serverless with PgBouncer connection pooling) and local SQLite fallback.
* **Predictive Modeling:** Scikit-Learn, Statsmodels (Gamma & Poisson GLMs, Random Forest Regressors, TimeSeriesSplit).
* **Frontend Web:** React 18, Vite, Leaflet, React-Leaflet, managed strictly with `pnpm`.
* **Deployment:** Render Web Service (Docker multi-stage build) and Render Static Site.

---

## Repository Structure

```
sicra/
├── assets/                Primary logos and vector graphics
├── data/                  Relational database caches and seed definitions
├── frontend/              React 18 + Vite frontend dashboard
│   ├── src/components/    Admin, Collector, and Business views
│   └── src/styles/        Design system tokens and responsive layouts
├── models/production/     Trained machine learning model artifacts
├── src/
│   ├── api/v1/            REST endpoints (auth, businesses, containers, routes, stats)
│   ├── database/          SQLAlchemy engines, sessions, and database seeders
│   ├── ml/                GLM estimators, ensemble predictors, and validation pipelines
│   ├── models/            Declarative ORM entities and Pydantic schemas
│   ├── services/          Business logic for alerts, telemetry, and route generation
│   └── simulation/        Monte Carlo probabilistic generation engine
├── Dockerfile             Multi-stage lean Docker build (< 512 MB footprint)
└── render.yaml            Infrastructure as Code configuration for Render deployment
```

---

## Local Development

### 1. Backend Server

```bash
# Clone the repository
git clone https://github.com/frank3lly/SICRA.git
cd SICRA

# Create and activate Python virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run FastAPI server
uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```

The API documentation will be available at `http://127.0.0.1:8000/docs`.

### 2. Frontend Application

```bash
# Navigate to frontend workspace
cd frontend

# Install dependencies
pnpm install

# Start Vite development server
pnpm dev
```

The dashboard will be available at `http://localhost:5173`.

---

## Default Access Credentials

For local development and testing, the initial seed provides three role-based accounts:

| Role | Email | Password | Access Scope |
| :--- | :--- | :--- | :--- |
| **System Administrator** | `admin@sicra.do` | `AdminSecure2026!` | Full fleet management, container token generation, route dispatch |
| **Logistics Collector** | `operaciones@reoil.do` | `CollectorSecure2026!` | Optimized pickup map, sequential stops, pickup confirmation |
| **Business Owner** | `dona.gladys@sicra.do` | `OwnerSecure2026!` | Real-time container fill gauge, environmental impact, pickup history |

---

## Production Deployment

SICRA is configured for zero-cost deployment using free-tier cloud infrastructure:

* **Web Service (API):** Hosted on **Render** using Docker (`Dockerfile`). Set the environment variable `DATABASE_URL` to your Neon pooled connection string.
* **Database:** Hosted on **Neon Serverless PostgreSQL** with persistent storage and connection pooling (`-pooler`).
* **Frontend:** Hosted on **Render Static Sites** with Root Directory set to `frontend` and Build Command `pnpm run build`.

---

## Academic Context

Developed as part of the Engineering Capstone Initiative under the CDIO standards framework at **Universidad Central del Este (UCE)**, San Pedro de Macorís, Dominican Republic.
