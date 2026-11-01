# Subspec 101: Relational Database Schema and ORM Entity Models

> **Stage:** `100_etapa_db_y_simulacion_de_datos`  
> **Subspec ID:** `101`  
> **Deliverable:** Database ORM Entities, Enums, Type Schemas, and Engine Factory  
> **Target Path:** `src/models/` and `src/database/`  
> **Status:** Executable Implementation Prompt  

---

## 1. Objective and Scope

Implement the complete relational database architecture for the SICRA software platform using **SQLAlchemy 2.0** (with declarative mapped columns) and **Pydantic V2**. The schema must define the entities required to manage food businesses, smart waste oil collection containers, raw IoT telemetry events, prediction logs, critical capacity alerts, dynamic logistics routes, and user authentication with role-based access control (RBAC).

This subspec defines the structural foundation. It must be database-agnostic, supporting **SQLite** for development and unit testing, and **PostgreSQL** for staging and production deployments.

---

## 2. Technical Stack and Dependencies

* **Language:** Python $\ge 3.10$
* **ORM:** SQLAlchemy $\ge 2.0.0$ (Declarative Base, Mapped type annotations)
* **Data Validation:** Pydantic $\ge 2.5.0$
* **Database Drivers:** `sqlite3` (built-in standard library) and `asyncpg` / `psycopg2-binary` (PostgreSQL)
* **UUID & Time:** Python `uuid` and `datetime` (UTC-enforced timestamps)

---

## 3. Entity Specifications and Data Dictionary

All entity models must inherit from a common `Base` declarative class and include an abstract audit mixin (`id`, `created_at`, `updated_at`).

### 3.1. Enums (`src/models/enums.py`)

* **`BusinessType` (String Enum):**
  * `FRITURA`: Street-food deep frying stalls (empanadas, yaniqueques, batata, chicharrón).
  * `PICA_POLLO`: Dominican fast-food chicken establishments with commercial multi-basket fryers.
  * `CAFETERIA`: Snack bars, breakfast cafeterias, school/university stands.
  * `RESTAURANTE`: Formal sit-down dining restaurants.
* **`ContainerStatus` (String Enum):**
  * `ACTIVE`: Deployed and transmitting.
  * `MAINTENANCE`: Under calibration, battery replacement, or physical repair.
  * `INACTIVE`: Decommissioned or offline.
* **`TelemetryFlag` (String Enum):**
  * `NORMAL`: Regular steady periodic reading.
  * `DRAIN_EVENT`: Weight drop detected (emptied by collector).
  * `OUTLIER_REJECTED`: Transient shock or vibration rejected by statistical filter.
  * `BATTERY_LOW`: Voltage below operating threshold ($< 3.4\text{ V}$).
* **`AlertType` (String Enum):**
  * `CAPACITY_80_PERCENT`: Volume has reached or exceeded $80\%$ of nominal capacity.
  * `CAPACITY_95_CRITICAL`: Imminent overflow risk ($> 95\%$).
  * `BATTERY_LOW`: Critical battery level requiring recharge.
  * `COMMUNICATION_TIMEOUT`: Node failed to check in within expected interval.
* **`RouteStatus` (String Enum):**
  * `SUGGESTED`: Computed by routing optimization algorithm.
  * `IN_PROGRESS`: Assigned to collector vehicle driver.
  * `COMPLETED`: All stops visited and emptied.
  * `CANCELLED`: Aborted or rescheduled.
* **`UserRole` (String Enum):**
  * `ADMIN`: Full system configuration and developer access.
  * `COLLECTOR`: Driver / logistics operator for waste management companies (Reoil / Mevosa).
  * `BUSINESS_OWNER`: Restaurant or fry shop manager (read-only view of own container).

---

### 3.2. ORM Entity Schemas (`src/models/entities.py`)

#### Table: `businesses` (`negocios`)
Represents the oil-producing gastronomic establishments.
* `id` (`VARCHAR(36)`, Primary Key, UUID4 as string).
* `name` (`VARCHAR(150)`, Not Null, Index): Legal or commercial name.
* `business_type` (`Enum(BusinessType)`, Not Null, Index).
* `num_fryers` (`INTEGER`, Not Null, Default 1): Number of active fryers/cauldrons (*calderos*).
* `avg_daily_customers` (`INTEGER`, Not Null, Default 100): Foot traffic estimate.
* `latitude` (`FLOAT`, Not Null): Decimal latitude (WGS 84).
* `longitude` (`FLOAT`, Not Null): Decimal longitude (WGS 84).
* `address` (`VARCHAR(255)`, Not Null): Street address and municipal sector.
* `city` (`VARCHAR(100)`, Not Null, Default `'San Pedro de Macorís'`): Dominican municipality.
* `contact_name` (`VARCHAR(120)`, Nullable): Manager or owner name.
* `phone` (`VARCHAR(30)`, Nullable): Dominican format contact number.
* `is_active` (`BOOLEAN`, Not Null, Default `True`).
* *Relationships:* One-to-many with `Container`, One-to-many with `User`.

#### Table: `containers` (`recipientes`)
Represents the smart HDPE waste oil collection bins installed at businesses.
* `id` (`VARCHAR(36)`, Primary Key, UUID4 as string).
* `business_id` (`VARCHAR(36)`, Foreign Key to `businesses.id`, Not Null, Index).
* `device_token` (`VARCHAR(64)`, Not Null, Unique, Index): Secure hash/API key for IoT ingest authentication.
* `capacity_liters` (`FLOAT`, Not Null): Max capacity (e.g., $20.0$, $50.0$, $100.0\text{ L}$).
* `tare_weight_kg` (`FLOAT`, Not Null, Default $2.5$): Empty bin and plate tare weight.
* `oil_density_kg_l` (`FLOAT`, Not Null, Default $0.92$): Physical conversion factor ($\text{kg} \to \text{L}$).
* `status` (`Enum(ContainerStatus)`, Not Null, Default `ACTIVE`).
* `current_volume_liters` (`FLOAT`, Not Null, Default $0.0$): Denormalized cached current volume.
* `current_fill_percentage` (`FLOAT`, Not Null, Default $0.0$): Denormalized fill percentage ($0 - 100\%$).
* `last_telemetry_at` (`DATETIME(timezone=True)`, Nullable): Timestamp of latest received ping.
* *Relationships:* Belongs to `Business`, One-to-many with `Telemetry`, One-to-many with `Prediction`, One-to-many with `Alert`.

#### Table: `telemetries` (`telemetrias`)
Time-series table holding every weight sensor transmission.
* `id` (`BIGINT`, Primary Key, Autoincrement): High-volume transaction identifier.
* `container_id` (`VARCHAR(36)`, Foreign Key to `containers.id`, Not Null, Index).
* `measurement_timestamp` (`DATETIME(timezone=True)`, Not Null, Index): Exact time recorded on device RTC.
* `received_at` (`DATETIME(timezone=True)`, Not Null, Default UTC `now`): Ingest server arrival time.
* `raw_weight_kg` (`FLOAT`, Not Null): Gross weight reading from the load cell + HX711.
* `calculated_liters` (`FLOAT`, Not Null): Net calculated volume: $(\text{raw\_weight} - \text{tare}) / \text{density}$.
* `fill_percentage` (`FLOAT`, Not Null): Percentage of nominal container capacity.
* `battery_voltage_mv` (`INTEGER`, Nullable): Battery voltage in millivolts (e.g. $4150\text{ mV}$).
* `battery_percentage` (`FLOAT`, Nullable): Approximate battery health ($0 - 100\%$).
* `is_synthetic` (`BOOLEAN`, Not Null, Default `True`, Index): Strict discriminator between Monte Carlo data and physical sensor pings.
* `flag` (`Enum(TelemetryFlag)`, Not Null, Default `NORMAL`).
* *Indices:* Composite Index on `(container_id, measurement_timestamp DESC)`.

#### Table: `predictions` (`predicciones`)
Log of daily predictive model estimations and time-to-critical thresholds.
* `id` (`VARCHAR(36)`, Primary Key, UUID4).
* `container_id` (`VARCHAR(36)`, Foreign Key to `containers.id`, Not Null, Index).
* `calculation_timestamp` (`DATETIME(timezone=True)`, Not Null, Index).
* `target_date` (`DATE`, Not Null, Index): The forecast day being predicted.
* `predicted_daily_liters` (`FLOAT`, Not Null): Model estimate for that day.
* `projected_hours_to_80_percent` (`FLOAT`, Nullable): Estimated hours until container hits $80\%$.
* `model_identifier` (`VARCHAR(64)`, Not Null): Name/version of model (e.g., `glm_gamma_v1`, `seasonal_naive`, `random_forest_v1`).
* `is_synthetic` (`BOOLEAN`, Not Null, Default `True`).
* `historical_mae` (`FLOAT`, Nullable): Stored cross-validation MAE metric at prediction time.

#### Table: `alerts` (`alertas`)
Operational notifications for collection triggers.
* `id` (`VARCHAR(36)`, Primary Key, UUID4).
* `container_id` (`VARCHAR(36)`, Foreign Key to `containers.id`, Not Null, Index).
* `alert_type` (`Enum(AlertType)`, Not Null, Index).
* `triggered_percentage` (`FLOAT`, Not Null): Volume level when triggered.
* `is_resolved` (`BOOLEAN`, Not Null, Default `False`, Index).
* `resolved_at` (`DATETIME(timezone=True)`, Nullable).
* `created_at` (`DATETIME(timezone=True)`, Not Null, Default UTC `now`).

#### Table: `collection_routes` (`rutas_recoleccion`)
Daily scheduled and optimized dispatch itineraries for collection trucks.
* `id` (`VARCHAR(36)`, Primary Key, UUID4).
* `scheduled_date` (`DATE`, Not Null, Index).
* `status` (`Enum(RouteStatus)`, Not Null, Default `SUGGESTED`, Index).
* `total_distance_km` (`FLOAT`, Not Null, Default $0.0$).
* `total_estimated_volume_liters` (`FLOAT`, Not Null, Default $0.0$).
* `stops_order_json` (`JSON` / `TEXT`, Not Null): Serialized ordered array of stops containing `{sequence, business_id, business_name, latitude, longitude, estimated_liters}`.
* `collector_user_id` (`VARCHAR(36)`, Foreign Key to `users.id`, Nullable).
* `completed_at` (`DATETIME(timezone=True)`, Nullable).

#### Table: `users` (`usuarios`)
Authentication and RBAC profiles.
* `id` (`VARCHAR(36)`, Primary Key, UUID4).
* `email` (`VARCHAR(150)`, Not Null, Unique, Index).
* `hashed_password` (`VARCHAR(255)`, Not Null).
* `full_name` (`VARCHAR(150)`, Not Null).
* `role` (`Enum(UserRole)`, Not Null, Default `BUSINESS_OWNER`, Index).
* `business_id` (`VARCHAR(36)`, Foreign Key to `businesses.id`, Nullable): Bound to business if `BUSINESS_OWNER`.
* `is_active` (`BOOLEAN`, Not Null, Default `True`).

---

## 4. Database Engine and Session Management (`src/database/session.py`)

1. Implement an engine factory that parses `DATABASE_URL` from environment variables (defaulting to `sqlite:///./data/sicra.db`).
2. Implement a context-managed `get_db()` dependency yielding thread-safe sessions (`sessionmaker(autocommit=False, autoflush=False, bind=engine)`).
3. Ensure proper foreign key enforcement in SQLite:
   ```python
   @event.listens_for(Engine, "connect")
   def set_sqlite_pragma(dbapi_connection, connection_record):
       if "sqlite" in str(connection_record._engine.url):
           cursor = dbapi_connection.cursor()
           cursor.execute("PRAGMA foreign_keys=ON")
           cursor.close()
   ```

---

## 5. Verification and Test Criteria

1. **Unit Test (`tests/test_models.py`):**
   * Create an in-memory SQLite database (`sqlite:///:memory:`).
   * Instantiate all models and assert table generation without schema conflicts.
   * Verify foreign key cascade constraints and enum validation errors on invalid strings.
   * Verify `is_synthetic` defaults to `True` on Telemetry and Prediction records.
