# Subspec 302: IoT Telemetry Ingestion Contract, Offline Batching, and Drain Detection

> **Stage:** `300_etapa_backend_api_y_rutas`  
> **Subspec ID:** `302`  
> **Deliverable:** REST Ingestion Endpoint, Offline Batch Processing (R-09), Physical Conversion Logic, and Drain Event Detector  
> **Target Path:** `src/api/v1/telemetry.py`, `src/services/telemetry_service.py`, `src/schemas/telemetry.py`  
> **Status:** Executable Implementation Prompt  

---

## 1. Objective and Scope

Implement the IoT telemetry intake subsystem. Although the physical ESP32 firmware is developed externally, this subspec defines the strict, production-ready server API contract that the microcontrollers communicate with.

The service must:
1. Authenticate hardware transmissions via container-specific API tokens.
2. Ingest individual real-time pings as well as **large batch arrays** accumulated in local flash memory during network outages (satisfying **Requirement R-09**).
3. Compute calibrated fluid volume and fill percentage server-side.
4. Implement an automatic **Drain Event Detector** that detects when an authorized collector empties the container, resetting volume accumulators and auto-resolving pending alerts.

---

## 2. Ingestion Protocol and API Specification

```
                          TELEMETRY INGESTION PIPELINE

      [ ESP32 IoT Node ]
               │
               │ POST /api/v1/telemetry/ingest
               │ Headers: X-Device-Token: "sicra_tok_..."
               │ Payload: { "readings": [ {...}, {...} ] }
               ▼
  ┌────────────────────────────────────────────────────────┐
  │                 API GATEWAY & AUTHENTICATION           │
  │  1. Validate X-Device-Token against 'containers' table │
  │  2. Reject unknown or decommissioned tokens (HTTP 401) │
  └──────────────────────────┬─────────────────────────────┘
                             │
                             ▼
  ┌────────────────────────────────────────────────────────┐
  │               BATCH RESILIENCE SERVICE (R-09)          │
  │  - Sort incoming readings chronologically              │
  │  - Deduplicate timestamps against existing records     │
  │  - Convert weight to liters: L = (weight - tare) / ρ   │
  │  - Calculate battery percentage from millivolts        │
  └──────────────────────────┬─────────────────────────────┘
                             │
                             ▼
  ┌────────────────────────────────────────────────────────┐
  │                 DRAIN DETECTION ALGORITHM              │
  │  Is ΔWeight < -0.35 · Capacity?                        │
  │  - YES ──► Tag DRAIN_EVENT & Auto-Resolve 80% Alerts   │
  │  - NO  ──► Tag NORMAL reading                          │
  └──────────────────────────┬─────────────────────────────┘
                             │
                             ▼
  ┌────────────────────────────────────────────────────────┐
  │           DATABASE PERSISTENCE & CACHE UPDATE          │
  │  - Bulk insert telemetry records                       │
  │  - Update 'containers.current_volume_liters' & fill %  │
  └────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Technical Specifications

### 3.1. Ingestion Request Schema (`src/schemas/telemetry.py`)

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class TelemetryReadingItem(BaseModel):
    timestamp: datetime = Field(..., description="UTC measurement timestamp recorded on device RTC")
    raw_weight_kg: float = Field(..., ge=0.0, description="Gross load cell weight measurement")
    battery_mv: Optional[int] = Field(None, ge=2500, le=5000, description="Battery millivolts")
    is_synthetic: bool = Field(False, description="Explicit discriminator between hardware and synthetic tests")

class TelemetryIngestPayload(BaseModel):
    device_token: Optional[str] = Field(None, description="Container token if not provided in headers")
    readings: List[TelemetryReadingItem] = Field(..., min_length=1, max_length=1000)
```

---

### 3.2. Physical Conversion and Normalization Logic

For each item in the payload:
1. **Volume Conversion ($\text{Liters}$):**
   $$\text{liters} = \max\left(0.0, \, \frac{\text{raw\_weight\_kg} - \text{container.tare\_weight\_kg}}{\text{container.oil\_density\_kg\_l}}\right)$$
2. **Fill Percentage ($\%$):**
   $$\text{fill\_percentage} = \min\left(100.0, \, \left(\frac{\text{liters}}{\text{container.capacity\_liters}}\right) \times 100.0\right)$$
3. **Battery Percentage Health:**
   Interpolate linearly between $3400\text{ mV}$ ($0\%$) and $4200\text{ mV}$ ($100\%$):
   $$\text{battery\_pct} = \min\left(100.0, \, \max\left(0.0, \, \frac{\text{battery\_mv} - 3400}{4200 - 3400} \times 100.0\right)\right)$$

---

### 3.3. Drain Event Detector and Alert Lifecycle

A drain event occurs when waste oil is emptied by the collection crew:

1. **Detection Rule:**
   $$\Delta W = W_{\text{raw}}(t) - W_{\text{raw}}(t-1)$$
   $$\text{If } \Delta W < -0.35 \times (\text{container.capacity\_liters} \cdot \text{density}) \quad \longrightarrow \quad \text{DRAIN\_EVENT}$$
2. **State Updates on Drain Event:**
   * Mark telemetry flag as `TelemetryFlag.DRAIN_EVENT`.
   * Automatically find all unresolved alerts (`is_resolved == False`) for this container and set `is_resolved = True`, `resolved_at = UTC now`.
   * Log operational audit note: *"Container emptied: volume dropped from $V_{t-1}$ to $V_t$ liters"*.

---

### 3.4. Deduplication and Offline Resilience (Requirement R-09)

When the ESP32 reconnects after an internet drop, it may transmit readings that overlap slightly with previous transmissions:
* The service must perform a query for existing timestamps for that `container_id` within the batch window:
  ```python
  existing_timestamps = set(
      db.query(Telemetry.measurement_timestamp)
      .filter(
          Telemetry.container_id == container.id,
          Telemetry.measurement_timestamp.in_([r.timestamp for r in readings])
      ).all()
  )
  ```
* Discard duplicates cleanly without throwing SQL unique constraint violation errors.
* Insert only fresh historical readings using high-speed bulk insert.

---

## 4. Verification and Test Criteria (`tests/test_telemetry_ingest.py`)

1. **Device Authentication Test:**
   * Post to `/api/v1/telemetry/ingest` with an invalid token. Assert HTTP 401 Unauthorized.
   * Post with a valid seeded token. Assert HTTP 200 OK.
2. **Batch Offline Ingestion Test (R-09):**
   * Transmit an array of 50 consecutive hourly readings simulating 2 days of offline storage.
   * Assert all 50 readings are persisted chronologically in the database.
   * Re-send the same payload and assert zero duplicates are created (`accepted_count == 0`, `duplicate_count == 50`).
3. **Drain Event Trigger Test:**
   * Post a reading at $42.0\text{ kg}$ on a $50\text{L}$ container ($84\%$ capacity, triggering an 80% alert).
   * Post a subsequent reading at $4.0\text{ kg}$ (near tare weight).
   * Assert the second reading is flagged as `TelemetryFlag.DRAIN_EVENT`.
   * Assert the open capacity alert is automatically marked as `is_resolved == True`.
