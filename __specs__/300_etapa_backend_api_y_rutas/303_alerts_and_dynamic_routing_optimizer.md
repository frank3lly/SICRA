# Subspec 303: 80% Capacity Alert Engine and Dynamic Routing Optimizer

> **Stage:** `300_etapa_backend_api_y_rutas`  
> **Subspec ID:** `303`  
> **Deliverable:** 80% Predictive Alert Service (R-05), Geodesic Distance Matrix, Nearest-Neighbor + 2-Opt Vehicle Routing Optimizer  
> **Target Path:** `src/services/alert_service.py`, `src/services/routing_service.py`, `src/api/v1/routes.py`, `src/api/v1/alerts.py`  
> **Status:** Executable Implementation Prompt  

---

## 1. Objective and Scope

Implement the operational core of SICRA: the automated **80% Capacity Alert Engine** and the **Dynamic Route Optimizer**.

This subspec satisfies two core system objectives:
1. **Early Alerting (Requirement R-05):** Detect when a container physically reaches $\ge 80\%$ capacity or when the predictive inference engine estimates overflow within 24 hours, automatically opening an operational alert.
2. **Dynamic Route Synthesis:** Consolidate all businesses with active alerts into an optimized vehicle route starting and ending at the authorized collector depot (Reoil Dominicana / Mevosa in San Pedro de Macorís), minimizing truck mileage and fuel consumption via Nearest Neighbor and 2-opt heuristic optimization.

---

## 2. Architecture and Algorithmic Flow

```
                      ALERT & ROUTE OPTIMIZATION PIPELINE

  ┌─────────────────────────────────┐
  │   Telemetry Ingestion / ML Ping │
  └────────────────┬────────────────┘
                   │
                   ▼
  ┌────────────────────────────────────────────────────────┐
  │                 ALERT EVALUATION SERVICE (R-05)        │
  │  Condition A: Fill% >= 80%                             │
  │  Condition B: Projected hours to 80% <= 24 hours       │
  │  - If YES & No active alert ──► Create Alert record    │
  └──────────────────────────┬─────────────────────────────┘
                             │
                             ▼
  ┌────────────────────────────────────────────────────────┐
  │                 DYNAMIC ROUTE OPTIMIZER                │
  │  1. Collect all businesses with active 80% alerts      │
  │  2. Anchor Depot: Reoil SPM (18.4650, -69.2950)        │
  │  3. Calculate Haversine Geodesic Distance Matrix       │
  │  4. Construct tour: Nearest Neighbor                   │
  │  5. Refine tour: 2-Opt Edge Swaps (eliminate crossings)│
  │  6. Compute total km and cumulative liters             │
  └──────────────────────────┬─────────────────────────────┘
                             │
                             ▼
  ┌────────────────────────────────────────────────────────┐
  │                   DISPATCH ITINERARY                   │
  │  Persist in 'collection_routes' table                  │
  │  Expose ordered stop sequence to Collector Dashboard   │
  └────────────────────────────────────────────────────────┘
```

---

## 3. Mathematical and Algorithmic Specifications

### 3.1. Dual-Condition Alert Logic (Requirement R-05)

When telemetry arrives or a background scheduled job executes:
* **Physical Trigger:** $\text{fill\_percentage} \ge 80.0\%$.
* **Predictive Trigger:** $\text{hours\_to\_80\_percent} \le 24.0\text{ hours}$ (calculated using `InferenceEngine.predict_hours_to_80_percent`).
* **Deduplication Check:**
  If an alert with `alert_type == AlertType.CAPACITY_80_PERCENT` and `is_resolved == False` already exists for this `container_id`, update `triggered_percentage` without creating duplicate records.

---

### 3.2. Geodesic Distance Calculation (Haversine Formula)

Between any two geographic locations $P_1(\phi_1, \lambda_1)$ and $P_2(\phi_2, \lambda_2)$:
$$a = \sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_1) \cdot \cos(\phi_2) \cdot \sin^2\left(\frac{\Delta \lambda}{2}\right)$$
$$d(P_1, P_2) = 2 \cdot R \cdot \arctan2\left(\sqrt{a}, \, \sqrt{1-a}\right) \quad (\text{where } R = 6371.0\text{ km})$$

---

### 3.3. Route Optimization Heuristic: Nearest Neighbor + 2-Opt

1. **Origin / Return Depot:**
   * Reoil Dominicana SPM Logistics Hub: Latitude $18.4650$, Longitude $-69.2950$.
2. **Tour Construction (Nearest Neighbor):**
   * Start at Depot ($S_0$).
   * Greedily select the unvisited alert node $S_{i+1}$ that minimizes $d(S_i, S_{i+1})$.
   * Repeat until all alert stops are visited, then return to Depot ($S_0$).
3. **Tour Refinement (2-Opt Local Search):**
   * Iteratively test edge swaps $(i, i+1)$ and $(j, j+1)$ for $i < j$.
   * If reversing the intermediate sub-route $[i+1, \dots, j]$ reduces total tour distance:
     $$d(S_i, S_j) + d(S_{i+1}, S_{j+1}) < d(S_i, S_{i+1}) + d(S_j, S_{j+1})$$
     execute the 2-opt swap:
     $$\text{Tour} \leftarrow \text{Tour}[0 \dots i] + \text{reversed}(\text{Tour}[i+1 \dots j]) + \text{Tour}[j+1 \dots N]$$
   * Terminate when no 2-opt swap achieves improvement $\ge 0.01\text{ km}$ (local optimum reached).

---

## 4. API Endpoints Specification

### 4.1. Alerts Router (`src/api/v1/alerts.py`)

* `GET /api/v1/alerts/active`
  * Security: Requires `UserRole.ADMIN` or `UserRole.COLLECTOR`.
  * Response: List of active alerts with business names, coordinates, and current fill percentages.
* `POST /api/v1/alerts/{id}/resolve`
  * Marks alert as resolved manually if needed.

### 4.2. Routes Router (`src/api/v1/routes.py`)

* `POST /api/v1/routes/generate-today`
  * Security: Requires `UserRole.ADMIN` or `UserRole.COLLECTOR`.
  * Queries all containers with unresolved 80% alerts.
  * Runs the Nearest Neighbor + 2-Opt algorithm.
  * Persists and returns the `CollectionRoute` record with the serialized `stops_order_json`.
* `GET /api/v1/routes/today`
  * Returns the latest suggested/active collection route for the current date.
* `POST /api/v1/routes/{id}/confirm-stop/{business_id}`
  * Driver clicks upon arrival and emptying; updates the stop status and triggers container tare reset.

---

## 5. Verification and Test Criteria (`tests/test_routing_and_alerts.py`)

1. **Alert Generation Verification:**
   * Ingest a reading of $41.0\text{ kg}$ on a $50\text{L}$ container ($82\%$).
   * Assert an alert record is created with `alert_type == AlertType.CAPACITY_80_PERCENT` and `is_resolved == False`.
   * Re-send the reading and verify no duplicate alert is generated.
2. **2-Opt Optimization Benchmark:**
   * Feed a set of 10 pilot businesses in San Pedro de Macorís with intentional path crossings.
   * Verify that 2-opt eliminates crossings, reducing total tour distance by at least $15\%$ compared to a naive random sequence.
3. **Roundtrip Depot Constraint:**
   * Assert the first waypoint is the Depot and the final waypoint returns to the Depot.
4. **Execution Time:**
   * For up to 50 stops, route optimization must complete in under **100 ms**.
