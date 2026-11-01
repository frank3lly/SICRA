### `GET /health`
* **Input:** None
* **Output (200):**
```json
{
  "status": "healthy",
  "service": "sicra-api",
  "version": "1.0.0",
  "database": "connected"
}
```

---

### `POST /api/v1/auth/login`
* **Input (Header):** `Content-Type: application/json` or `application/x-www-form-urlencoded`
* **Input (Body):**
```json
{
  "email": "user@sicra.do",
  "password": "SecurePassword!"
}
```
* **Output (200):**
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@sicra.do",
    "full_name": "Full Name",
    "role": "ADMIN | COLLECTOR | BUSINESS_OWNER",
    "business_id": "uuid | null",
    "is_active": true
  }
}
```

---

### `GET /api/v1/auth/me`
* **Input (Header):** `Authorization: Bearer <token>`
* **Output (200):**
```json
{
  "id": "uuid",
  "email": "user@sicra.do",
  "full_name": "Full Name",
  "role": "ADMIN | COLLECTOR | BUSINESS_OWNER",
  "business_id": "uuid | null",
  "is_active": true
}
```

---

### `POST /api/v1/telemetry/ingest`
* **Input (Header):** `X-Device-Token: sicra_live_tok_...` *(optional if sent in body)*
* **Input (Body):**
```json
{
  "device_token": "sicra_live_tok_...",
  "readings": [
    {
      "timestamp": "2026-10-31T14:30:00Z",
      "raw_weight_kg": 42.0,
      "battery_mv": 3950,
      "is_synthetic": false
    }
  ]
}
```
* **Output (200):**
```json
{
  "status": "success",
  "container_id": "uuid",
  "accepted_count": 1,
  "duplicate_count": 0,
  "current_volume_liters": 41.52,
  "current_fill_percentage": 83.04,
  "drain_events_detected": 0,
  "alerts_triggered": 1,
  "alerts_resolved": 0
}
```

---

### `GET /api/v1/telemetry/container/{container_id}`
* **Input (Header):** `Authorization: Bearer <token>`
* **Input (Path/Query):** `container_id` (UUID), `limit=100`
* **Output (200):**
```json
[
  {
    "id": 1,
    "container_id": "uuid",
    "measurement_timestamp": "2026-10-31T14:30:00Z",
    "raw_weight_kg": 42.0,
    "calculated_liters": 41.52,
    "fill_percentage": 83.04,
    "battery_voltage_mv": 3950,
    "battery_percentage": 68.8,
    "is_synthetic": false,
    "flag": "NORMAL | DRAIN_EVENT | BATTERY_LOW"
  }
]
```

---

### `GET /api/v1/businesses/`
* **Input (Header):** `Authorization: Bearer <token>`
* **Output (200):**
```json
[
  {
    "id": "uuid",
    "name": "Pica Pollo Expreso",
    "business_type": "PICA_POLLO",
    "num_fryers": 4,
    "avg_daily_customers": 380,
    "latitude": 18.4552,
    "longitude": -69.3087,
    "address": "Av. Francisco Alberto Caamaño Deñó",
    "city": "San Pedro de Macorís",
    "contact_name": "Ramón Castillo",
    "phone": "809-529-1001",
    "is_active": true
  }
]
```

---

### `GET /api/v1/businesses/{id}`
* **Input (Header):** `Authorization: Bearer <token>`
* **Input (Path):** `id` (UUID)
* **Output (200):**
```json
{
  "id": "uuid",
  "name": "Pica Pollo Expreso",
  "business_type": "PICA_POLLO",
  "latitude": 18.4552,
  "longitude": -69.3087,
  "containers": [
    {
      "id": "uuid",
      "capacity_liters": 100.0,
      "current_volume_liters": 82.5,
      "current_fill_percentage": 82.5,
      "status": "ACTIVE"
    }
  ]
}
```

---

### `POST /api/v1/businesses/`
* **Input (Header):** `Authorization: Bearer <admin_token>`
* **Input (Body):**
```json
{
  "name": "Nuevo Comedor",
  "business_type": "CAFETERIA",
  "num_fryers": 2,
  "avg_daily_customers": 150,
  "latitude": 18.459,
  "longitude": -69.305,
  "address": "Calle Central #12",
  "city": "San Pedro de Macorís",
  "contact_name": "Juan Perez",
  "phone": "809-555-1234"
}
```
* **Output (201):**
```json
{
  "id": "uuid",
  "name": "Nuevo Comedor",
  "is_active": true
}
```

---

### `GET /api/v1/containers/`
* **Input (Header):** `Authorization: Bearer <token>`
* **Output (200):**
```json
[
  {
    "id": "uuid",
    "business_id": "uuid",
    "device_token": "sicra_live_tok_...",
    "capacity_liters": 50.0,
    "tare_weight_kg": 3.8,
    "oil_density_kg_l": 0.92,
    "status": "ACTIVE",
    "current_volume_liters": 41.52,
    "current_fill_percentage": 83.04,
    "last_telemetry_at": "2026-10-31T14:30:00Z"
  }
]
```

---

### `GET /api/v1/containers/my-container`
* **Input (Header):** `Authorization: Bearer <business_owner_token>`
* **Output (200):**
```json
{
  "id": "uuid",
  "business_id": "my_business_uuid",
  "capacity_liters": 50.0,
  "current_volume_liters": 41.52,
  "current_fill_percentage": 83.04,
  "last_telemetry_at": "2026-10-31T14:30:00Z"
}
```

---

### `GET /api/v1/containers/{id}`
* **Input (Header):** `Authorization: Bearer <token>`
* **Input (Path):** `id` (UUID)
* **Output (200):**
```json
{
  "id": "uuid",
  "business_id": "uuid",
  "capacity_liters": 50.0,
  "tare_weight_kg": 3.8,
  "oil_density_kg_l": 0.92,
  "status": "ACTIVE",
  "current_volume_liters": 41.52,
  "current_fill_percentage": 83.04,
  "last_telemetry_at": "2026-10-31T14:30:00Z"
}
```

---

### `GET /api/v1/alerts/active`
* **Input (Header):** `Authorization: Bearer <token>`
* **Output (200):**
```json
[
  {
    "id": "uuid",
    "container_id": "uuid",
    "alert_type": "CAPACITY_80_PERCENT | CAPACITY_95_CRITICAL | BATTERY_LOW",
    "triggered_percentage": 83.04,
    "is_resolved": false,
    "created_at": "2026-10-31T14:30:00Z"
  }
]
```

---

### `POST /api/v1/alerts/{id}/resolve`
* **Input (Header):** `Authorization: Bearer <token>`
* **Input (Path):** `id` (UUID)
* **Output (200):**
```json
{
  "id": "uuid",
  "is_resolved": true,
  "resolved_at": "2026-10-31T15:00:00Z"
}
```

---

### `POST /api/v1/routes/generate-today`
* **Input (Header):** `Authorization: Bearer <collector_or_admin_token>`
* **Output (200):**
```json
{
  "route_id": "uuid",
  "scheduled_date": "2026-10-31",
  "total_stops": 5,
  "total_distance_km": 14.8,
  "total_estimated_liters": 285.0,
  "status": "SUGGESTED",
  "itinerary": [
    {
      "sequence": 1,
      "business_id": "uuid",
      "business_name": "Pica Pollo Expreso",
      "latitude": 18.4552,
      "longitude": -69.3087,
      "estimated_liters": 82.5
    }
  ]
}
```

---

### `GET /api/v1/routes/today`
* **Input (Header):** `Authorization: Bearer <token>`
* **Output (200):**
```json
{
  "route_id": "uuid",
  "scheduled_date": "2026-10-31",
  "status": "SUGGESTED | IN_PROGRESS | COMPLETED",
  "total_stops": 5,
  "itinerary": []
}
```

---

### `POST /api/v1/routes/{id}/confirm-stop/{business_id}`
* **Input (Header):** `Authorization: Bearer <collector_token>`
* **Input (Path):** `id` (UUID route), `business_id` (UUID)
* **Output (200):**
```json
{
  "status": "stop_confirmed",
  "route_id": "uuid",
  "business_id": "uuid",
  "confirmed_at": "2026-10-31T16:00:00Z"
}
```

---

### `GET /api/v1/predictions/container/{id}`
* **Input (Header):** `Authorization: Bearer <token>`
* **Input (Path):** `id` (UUID container)
* **Output (200):**
```json
{
  "container_id": "uuid",
  "calculation_timestamp": "2026-10-31T06:00:00Z",
  "target_date": "2026-10-31",
  "predicted_daily_liters": 14.2,
  "projected_hours_to_80_percent": 18.5,
  "model_identifier": "RidgeDailyPredictor"
}
```

---

### `POST /api/v1/predictions/run-forecast`
* **Input (Header):** `Authorization: Bearer <admin_token>`
* **Output (200):**
```json
{
  "status": "forecast_completed",
  "containers_processed": 10,
  "predictions_generated": 10
}
```

---

### `GET /api/v1/stats/environmental`
* **Input (Header):** `Authorization: Bearer <token>`
* **Output (200):**
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
