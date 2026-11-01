# Subspec 104: Dataset Export, Data Integrity, and Statistical Validation Suite

> **Stage:** `100_etapa_db_y_simulacion_de_datos`  
> **Subspec ID:** `104`  
> **Deliverable:** Integrity Audit Suite, Daily Aggregation Pipeline, and Chronological Split Exporter  
> **Target Path:** `src/data/`, `tests/`  
> **Status:** Executable Implementation Prompt  

---

## 1. Objective and Scope

Implement the quality assurance, data integrity auditing, and feature export pipeline that bridges the synthetic/real data layer (Stage 100) with the Machine Learning and predictive modeling layer (Stage 200).

This subspec delivers:
1. An **Integrity Validator** (`src/data/validator.py`) to verify that all persisted data respects physical laws, relational constraints, and cultural consumption profiles of the Dominican Republic.
2. A **Daily Aggregation Pipeline** (`src/data/aggregator.py`) that converts raw high-frequency telemetry into the daily tabular format required for multiple linear regression, GLM, and tree models.
3. A **Chronological Dataset Exporter** (`src/data/exporter.py`) that exports pre-split training and testing sets ready for ML cross-validation.
4. A **Pytest Integration Suite** (`tests/test_stage_100.py`) certifying the complete closure of Stage 100.

---

## 2. Technical Specifications

```
  ┌────────────────────────────────────────────────────────────────────────┐
  │                   STAGE 100 VERIFICATION PIPELINE                     │
  └──────────────────────────────────┬─────────────────────────────────────┘
                                     │
         ┌───────────────────────────┴───────────────────────────┐
         ▼                                                       ▼
┌───────────────────────────────┐               ┌───────────────────────────────┐
│     INTEGRITY VALIDATOR       │               │      FEATURE AGGREGATOR       │
│ - Check no negative liters    │               │ - Resample telemetry to daily │
│ - Verify 100% synthetic flags │               │ - Calculate 24h delta volume  │
│ - Check Dominican weekend lift│               │ - Compute 7-day seasonal lag  │
│ - Validate foreign keys       │               │ - One-hot dummy encodings     │
└───────────────────────────────┘               └───────────────┬───────────────┘
                                                                │
                                                                ▼
                                                ┌───────────────────────────────┐
                                                │    CHRONOLOGICAL EXPORTER     │
                                                │ - Train set: 80% oldest dates │
                                                │ - Test set: 20% newest dates  │
                                                │ - Output: data/processed/     │
                                                └───────────────────────────────┘
```

---

## 3. Component Details

### 3.1. Data Integrity and Sanity Auditor (`src/data/validator.py`)

The auditor must run automated assertions across the database:

1. **Physical Plausibility Checks:**
   * $\text{calculated\_liters} \ge 0.0$ across all rows.
   * $\text{fill\_percentage} \le 105.0\%$ (allowing slight physical meniscus tolerance, but flagging overfill anomalies).
   * Battery voltage between $3200\text{ mV}$ and $4350\text{ mV}$.
2. **Relational and Provenance Checks:**
   * Zero orphaned telemetry records (every `container_id` references a valid `containers.id`).
   * When validating synthetic batches, assert $100\%$ of rows have `is_synthetic == True`.
3. **Statistical Profile Validation (Dominican Gastro-Profile):**
   * Assert $\text{MeanVolume}(\text{PICA\_POLLO}) > \text{MeanVolume}(\text{FRITURA}) > \text{MeanVolume}(\text{CAFETERIA})$.
   * Assert $\text{MeanVolume}(\text{Friday, Saturday, Sunday}) \ge 1.4 \times \text{MeanVolume}(\text{Monday, Tuesday, Wednesday})$.

---

### 3.2. Telemetry to Daily Features Aggregator (`src/data/aggregator.py`)

The raw telemetry table contains frequent weight snapshots (e.g., every 2 hours). Machine Learning algorithms require daily aggregated observations per business.

* **Daily Resampling Logic:**
  1. For each `container_id` and calendar date:
     * Extract positive volume increments ($\Delta V = \max(0, V_{t} - V_{t-1})$ excluding drain/emptying resets).
     * Sum increments to obtain total daily generated volume: $\text{daily\_liters}$.
  2. Join business attributes: `business_type`, `num_fryers`, `avg_daily_customers`, and `city`.
  3. Calculate temporal features:
     * `day_of_week` ($0 = \text{Monday}, \dots, 6 = \text{Sunday}$).
     * `is_weekend` (boolean, True for Friday, Saturday, Sunday in Dominican context).
     * `lag_same_day_prev_week` ($y_{t-7}$, volume poured exactly 7 days prior).
* Output dataframe columns:
  `['date', 'container_id', 'business_id', 'business_name', 'business_type', 'num_fryers', 'avg_daily_customers', 'day_of_week', 'is_weekend', 'lag_7d_liters', 'daily_liters', 'is_synthetic']`

---

### 3.3. Chronological Dataset Exporter (`src/data/exporter.py`)

To prevent data leakage in Stage 200, the dataset must **never** be shuffled randomly.

* **Exporter CLI:**
  ```bash
  python -m src.data.exporter --train-ratio 0.8 --output-dir data/processed/
  ```
* **Output Artifacts:**
  * `data/processed/daily_oil_generation.csv`: Full aggregated time-series.
  * `data/processed/train_chronological.csv`: Oldest $80\%$ of consecutive calendar dates.
  * `data/processed/test_chronological.csv`: Most recent $20\%$ of consecutive calendar dates.
  * `data/processed/dataset_summary.json`: Metadata report with row counts, date ranges, mean daily liters, and feature schema.

---

## 4. Test Suite Specification (`tests/test_stage_100.py`)

Implement a comprehensive integration test suite using **pytest**:

1. `test_schema_creation_and_foreign_keys()`: Verifies that tables instantiate correctly with SQLite pragmas enabled.
2. `test_dominican_seed_idempotency_and_completeness()`: Runs the seed script twice and asserts exactly 10 businesses are present, with correct Dominican addresses and container capacities.
3. `test_monte_carlo_generator_reproducibility()`: Asserts that identical seeds yield identical outputs.
4. `test_no_negative_volumes_or_leaks()`: Inspects 50,000 generated rows to assert strictly zero negative values.
5. `test_chronological_split_integrity()`: Asserts $\max(\text{Date}_{\text{train}}) < \min(\text{Date}_{\text{test}})$ (zero temporal overlap).

---

## 5. Definition of Done for Stage 100

Stage 100 is officially complete when:
1. All ORM models and migrations are functional (`alembic upgrade head`).
2. Seeding runs cleanly via `python -m src.database.seed --reset`.
3. Monte Carlo generator creates $\ge 50,000$ synthetic telemetry records in SQLite.
4. Exporter generates `train_chronological.csv` and `test_chronological.csv` in `data/processed/`.
5. `pytest tests/test_stage_100.py` passes with $100\%$ green status.
