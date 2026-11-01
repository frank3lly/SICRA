# Subspec 304: REST API Endpoints, Environmental Stats, and E2E Integration Suite

> **Stage:** `300_etapa_backend_api_y_rutas`  
> **Subspec ID:** `304`  
> **Deliverable:** Business/Container/Stats CRUD Endpoints, Environmental Impact Metrics (Ley 225-20), and End-to-End Test Suite  
> **Target Path:** `src/api/v1/`, `src/services/stats_service.py`, `tests/test_stage_300_e2e.py`  
> **Status:** Executable Implementation Prompt  

---

## 1. Objective and Scope

Complete the REST API layer of SICRA, providing the administrative, operational, and business endpoints consumed by the Stage 400 Frontend dashboard:

1. **Entities & Telemetry CRUD APIs:** Full REST endpoints for managing businesses, smart containers, telemetry query histories, and predictive model forecasts.
2. **Environmental & Compliance Stats Engine (Ley 225-20):** Computes aggregate environmental metrics, converting recycled waste oil into potable water volume preserved ($1\text{L oil} = 1,000\text{L water}$), and tracking custody manifests for Reoil / Mevosa.
3. **End-to-End Integration Suite (`tests/test_stage_300_e2e.py`):** An end-to-end integration test certifying the entire backend flow: authentication $\to$ batch ingestion $\to$ 80% alert firing $\to$ route generation $\to$ collection confirmation $\to$ tare reset $\to$ environmental counter update.

---

## 2. API Endpoints Specification

```
                         REST API ROUTING TOPOLOGY
                         
  /api/v1
  ├── /auth
  │   ├── POST /login                 (JWT token issuance)
  │   └── GET  /me                    (Current user profile & role)
  ├── /telemetry
  │   ├── POST /ingest                (IoT hardware intake, batch support)
  │   └── GET  /container/{id}        (Historical telemetry series)
  ├── /businesses
  │   ├── GET  /                      (List businesses with geo coordinates)
  │   ├── GET  /{id}                  (Detail view with container status)
  │   └── POST /                      (Onboard new business - Admin only)
  ├── /containers
  │   ├── GET  /                      (Fleet container overview)
  │   ├── GET  /my-container          (Business Owner isolated container view)
  │   └── GET  /{id}                  (Container calibration & hardware state)
  ├── /alerts
  │   ├── GET  /active                (Unresolved 80% alerts for Collector)
  │   └── POST /{id}/resolve          (Manual resolution override)
  ├── /routes
  │   ├── POST /generate-today        (Nearest-Neighbor + 2-Opt optimizer)
  │   ├── GET  /today                 (Latest active dispatch route)
  │   └── POST /{id}/confirm-stop/{b} (Driver pickup confirmation & tare reset)
  ├── /predictions
  │   ├── GET  /container/{id}        (Latest ML forecast & hours to 80%)
  │   └── POST /run-forecast          (Batch inference trigger across fleet)
  └── /stats
      └── GET  /environmental         (Water preserved, Ley 225-20 compliance)
```

---

## 3. Environmental Impact and Legal Compliance Engine (`src/services/stats_service.py`)

To satisfy Dominican environmental legislation (**Ley 225-20** on Solid Waste and **Ley 64-00** on Water Resources), the backend exposes an automated environmental impact aggregator:

* **Calculation Rules:**
  1. $\text{Total Oil Diverted (Liters)} = \sum \text{Volume of all confirmed DRAIN\_EVENTS}$.
  2. $\text{Water Resources Preserved (Liters)} = \text{Total Oil Diverted} \times 1,000$.
  3. $\text{Carbon Offsetting Estimate (kg CO}_2\text{e)} = \text{Total Oil Diverted} \times 2.85\text{ kg CO}_2\text{e/L}$ (representing bio-diesel substitution savings over virgin fossil diesel).
* **Endpoint: `GET /api/v1/stats/environmental`:**
  * Returns JSON summary:
    ```json
    {
      "total_oil_diverted_liters": 14250.0,
      "water_preserved_liters": 14250000.0,
      "co2_avoided_kg": 40612.5,
      "total_collections_count": 312,
      "active_containers_count": 10,
      "compliance_framework": "Ley No. 225-20 de Gestion Integral y Coprocesamiento de Residuos"
    }
    ```

---

## 4. End-to-End Integration Test Suite (`tests/test_stage_300_e2e.py`)

Implement an end-to-end integration test utilizing `pytest` and `httpx.AsyncClient`:

1. **Step 1: Auth & Role Enforcement:**
   * Login as `admin@sicra.do`, `operaciones@reoil.do` (`COLLECTOR`), and a `BUSINESS_OWNER`.
   * Assert tokens are received with correct claims.
2. **Step 2: IoT Telemetry Batch Ingestion:**
   * Post a 20-reading batch to `/api/v1/telemetry/ingest` using the device token of *Pica Pollo Expreso*.
   * Verify HTTP 200 and database persistence.
3. **Step 3: Alert Triggering (Requirement R-05):**
   * Post a reading with weight indicating $84\%$ capacity.
   * Verify that `GET /api/v1/alerts/active` immediately lists this container with `alert_type == CAPACITY_80_PERCENT`.
4. **Step 4: Dynamic Route Generation:**
   * Call `POST /api/v1/routes/generate-today` as Collector.
   * Verify that an optimized route is returned, starting and ending at the Reoil SPM depot, including the alerted business.
5. **Step 5: Pickup Confirmation & Drain Event Resolution:**
   * Call `POST /api/v1/routes/{id}/confirm-stop/{biz_id}`.
   * Post a low-weight telemetry reading ($4.0\text{ kg}$, near tare).
   * Verify the alert is automatically resolved (`is_resolved == True`).
   * Verify `GET /api/v1/stats/environmental` increments the total oil diverted and water preserved counters.

---

## 5. Definition of Done for Stage 300

Stage 300 is officially complete when:
1. Multi-stage `Dockerfile` and `render.yaml` are validated and ready for free-tier deployment.
2. Ingestion endpoint `/api/v1/telemetry/ingest` successfully processes single and batch payloads, performing tare and density conversions.
3. Drain event detector automatically recognizes weight drops and resolves pending alerts.
4. Route optimizer runs 2-opt swaps on alert clusters in $< 100\text{ ms}$.
5. Role-Based Access Control (RBAC) securely isolates business owners to their own container metrics.
6. `pytest tests/test_stage_300_e2e.py` passes with $100\%$ green status.
