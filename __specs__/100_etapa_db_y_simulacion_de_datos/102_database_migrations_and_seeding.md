# Subspec 102: Migrations, Session Management, and Dominican Seed Data

> **Stage:** `100_etapa_db_y_simulacion_de_datos`  
> **Subspec ID:** `102`  
> **Deliverable:** Database Migrations (Alembic), CLI Seeding Script, Realistic Dominican Republic Gastro-Businesses  
> **Target Path:** `alembic/`, `src/database/seed.py`, `src/database/seed_data/`  
> **Status:** Executable Implementation Prompt  

---

## 1. Objective and Scope

Implement the automated database initialization, migration pipeline (using **Alembic**), and a realistic seed data loader representing authentic food businesses in the **Dominican Republic** (concentrated in **San Pedro de Macorís** around the **Universidad Central del Este - UCE** and the Eastern corridor).

The seed script must populate baseline businesses, install smart containers with specific capacities and calibration parameters, and create administrative and logistics user accounts.

---

## 2. Alembic Migration Setup

1. Initialize Alembic configuration in the repository root:
   * Target directory: `alembic/`
   * Configuration file: `alembic.ini`
   * Target metadata in `alembic/env.py`: Import `Base` from `src.models.entities`.
2. Generate baseline migration:
   * `0001_initial_sicra_schema.py` creating tables: `businesses`, `containers`, `telemetries`, `predictions`, `alerts`, `collection_routes`, and `users`.
3. Provide programmatic database creation helper:
   * `src/database/init_db.py` to create tables directly on lightweight SQLite instances during local testing without executing raw migrations.

---

## 3. Dominican Gastronomic Businesses Seed Specification

The seed data must mirror the authentic ecosystem of Dominican street food, cafeterias, and commercial chicken joints (*pica pollos*). Each record must provide accurate geolocations within San Pedro de Macorís (SPM) or nearby routes, with realistic fryer counts and customer throughput.

### 3.1. Catalogue of Dominican Pilot Businesses

| ID Key | Business Name | Type | Fryers / Cauldrons | Avg Daily Customers | Target Container Capacity | Sector / Coordinates |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| `SPM_BIZ_001` | **Pica Pollo Expreso San Pedro** | `PICA_POLLO` | 4 | 380 | 100 L | Av. Francisco Alberto Caamaño Deñó (prox. UCE) <br> *(18.4552, -69.3087)* |
| `SPM_BIZ_002` | **Fritura Doña Gladys - Sabor Oriental** | `FRITURA` | 2 | 140 | 50 L | Barrio Lindo, San Pedro de Macorís <br> *(18.4610, -69.3012)* |
| `SPM_BIZ_003` | **Cafetería y Comedor La Gran Parada UCE** | `CAFETERIA` | 1 | 160 | 20 L | Frente al Campus Central UCE <br> *(18.4538, -69.3095)* |
| `SPM_BIZ_004` | **Pica Pollo Dragón de Oro SPM** | `PICA_POLLO` | 5 | 450 | 100 L | Av. Independencia, Centro de la Ciudad <br> *(18.4510, -69.3040)* |
| `SPM_BIZ_005` | **Fritura El Primo Chimi y Picalonga** | `FRITURA` | 3 | 220 | 50 L | Malecón de San Pedro de Macorís <br> *(18.4485, -69.3020)* |
| `SPM_BIZ_006` | **D' Yanet Empanadas Monumental** | `CAFETERIA` | 2 | 190 | 50 L | Calle Sánchez, Barrio Restauración <br> *(18.4570, -69.3120)* |
| `SPM_BIZ_007` | **Comedor Típico Doña Yudelka** | `RESTAURANTE` | 2 | 130 | 50 L | Sector Miramar, cerca del Puerto SPM <br> *(18.4460, -69.3055)* |
| `SPM_BIZ_008` | **Pollo Cibao Express Macorís** | `PICA_POLLO` | 4 | 410 | 100 L | Av. Mauricio Báez, San Pedro de Macorís <br> *(18.4595, -69.3060)* |
| `SPM_BIZ_009` | **Cafetería El Buen Gusto Estudiantil** | `CAFETERIA` | 1 | 95 | 20 L | Entrada Este UCE <br> *(18.4545, -69.3110)* |
| `SPM_BIZ_010` | **Fritura La Famosa de Placer Bonito** | `FRITURA` | 3 | 260 | 50 L | Sector Placer Bonito, San Pedro de Macorís <br> *(18.4635, -69.3035)* |

SPM_BIZ_011 Agrega Pica Pollo Sandy en SPM tambien: FP55+57C, San Pedro de Macorís 21000
---

### 3.2. Container Provisioning Rules

For each business seeded above:
1. Create a linked `Container` record.
2. Capacity assigned:
   * **100 Liters:** For establishments with $\ge 4$ fryers (High volume *Pica Pollos*).
   * **50 Liters:** For businesses with 2–3 cauldrons (*Frituras* and high-traffic empanada stands).
   * **20 Liters:** For single-fryer cafeterias.
3. Assign physical calibration constants:
   * `tare_weight_kg`: $2.20\text{ kg}$ (for 20L), $3.80\text{ kg}$ (for 50L), $6.50\text{ kg}$ (for 100L).
   * `oil_density_kg_l`: $0.92\text{ kg/L}$.
   * `device_token`: Cryptographically secure unique string formatted as `sicra_live_tok_<biz_id>_<hex16>`.
   * `status`: `ACTIVE`.

---

### 3.3. Initial System Users Seed

1. **System Administrator:**
   * czorrilla@sicra.do 
   * dcaraballo@sicra.do     
   * yrodriguez@sicra.do
   * fcharles@sicra.do
   * amontero@sicra.do
   * jburgos@sicra.do
   * mcarrasco@sicra.do
   contraseñas: `AdminSecure2026!` para todos esos de arriba
   * Email: `admin@sicra.do`
   * Password: Hash of `AdminSecure2026!` (using Passlib / Bcrypt)
   * Role: `ADMIN`
2. **Authorized Waste Collector Users (Reoil & Mevosa):**
   * Email: `operaciones@reoil.do` (Role: `COLLECTOR`)
   * Email: `logistica@mevosa.do` (Role: `COLLECTOR`)
3. **Business Managers:**
   * Create account for each pilot business (e.g. `picapollo.expreso@sicra.do`, `dona.gladys@sicra.do`) linked to their corresponding `business_id`. Role: `BUSINESS_OWNER`.

---

## 4. Implementation Requirements for `seed.py`

* The script must be executable via standard CLI:
  ```bash
  python -m src.database.seed
  # Options:
  #   --reset    (Drops and recreates all tables before seeding)
  #   --quiet    (Suppresses detailed stdout logs)
  ```
* **Idempotency Guarantee:** If executed multiple times without `--reset`, the script must check for the presence of existing IDs or emails and skip duplicates gracefully without crashing.
* Data source isolation: Store the raw business seeds in a clean JSON/Dict file (`src/database/seed_data/dominican_businesses.json`) separating seed configuration from database execution logic.

---

## 5. Verification and Test Criteria

1. Execute `python -m src.database.seed --reset`.
2. Run database verification queries:
   * Assert exactly 11 businesses are created.
   * Assert all 11 businesses have linked active containers with correct capacity tiers (100L, 50L, 20L).
   * Assert all coordinates are within the geographic bounding box of San Pedro de Macorís ($\text{lat} \in [18.40, 18.50]$, $\text{lon} \in [-69.35, -69.25]$).
   * Verify password hashes with bcrypt verification.
