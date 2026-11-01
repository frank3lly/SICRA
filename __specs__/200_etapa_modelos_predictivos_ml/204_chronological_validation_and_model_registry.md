# Subspec 204: Chronological Cross-Validation, Golden Rule Evaluator, and Model Registry

> **Stage:** `200_etapa_modelos_predictivos_ml`  
> **Subspec ID:** `204`  
> **Deliverable:** Chronological TimeSeriesSplit Evaluator, Golden Rule Decision Engine (R-04), Model Registry, and Unified Inference Engine  
> **Target Path:** `src/ml/evaluator.py`, `src/ml/registry.py`, `src/ml/inference.py`, `src/ml/cli.py`  
> **Status:** Executable Implementation Prompt  

---

## 1. Objective and Scope

Implement the validation harness, automated decision gate, serialization registry, and production inference facade for Stage 200:

1. **Chronological Evaluation Harness (`src/ml/evaluator.py`):** Enforces strict temporal cross-validation (`TimeSeriesSplit`) without future data leakage, computing Mean Absolute Error (MAE) across consecutive time horizons.
2. **Automated "Golden Rule" Gate (Requirement R-04):** Programmatically verifies whether candidate models outperform the Seasonal Naive baseline on unseen chronological test data. If a model fails to beat the baseline, it triggers an automatic fallback (*safe default*) to `SeasonalNaivePredictor`.
3. **Model Registry (`src/ml/registry.py`):** Serializes fitted pipelines, persists performance metrics and feature rankings in JSON manifests, and manages versioned deployment tags (`models/`).
4. **Unified Inference Engine (`src/ml/inference.py`):** Provides a high-level API facade that the Stage 300 backend server will consume directly to fetch daily volume predictions and hours-to-$80\%$ estimates.

---

## 2. Architecture and Evaluation Workflow

```
                   CHRONOLOGICAL EVALUATION & REGISTRY PIPELINE

  ┌─────────────────────────────────┐
  │ data/processed/train_chrono.csv │
  │ data/processed/test_chrono.csv  │
  └────────────────┬────────────────┘
                   │
                   ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │                       EVALUATOR HARNESS (R-04)                         │
  │  - Fit Candidate (GLM / Ensemble) on Train                             │
  │  - Fit Seasonal Naive Benchmark on Train                               │
  │  - Compute MAE_candidate vs. MAE_baseline on Held-Out Test Set         │
  └────────────────────────────────┬───────────────────────────────────────┘
                                   │
                   ┌───────────────┴───────────────┐
                   ▼                               ▼
       MAE_candidate < MAE_baseline     MAE_candidate >= MAE_baseline
       (R-04 PASSED: SUCCESS)           (R-04 FAILED: RT01 FALLBACK)
                   │                               │
                   ▼                               ▼
  ┌─────────────────────────────────┐   ┌─────────────────────────────────┐
  │ Promote Candidate to Production │   │ Deploy Seasonal Naive Baseline  │
  │ Status: ACTIVE_PRODUCTION       │   │ Status: FALLBACK_ACTIVE         │
  └────────────────┬────────────────┘   └────────────────┬────────────────┘
                   │                                     │
                   └──────────────────┬──────────────────┘
                                      ▼
                        ┌───────────────────────────┐
                        │   UNIFIED INFERENCE API   │
                        │   (Consumed by Backend)   │
                        └───────────────────────────┘
```

---

## 3. Mathematical and Technical Specifications

### 3.1. Chronological Cross-Validation (`src/ml/evaluator.py`)

* **No-Shuffle Rolling Origin (`TimeSeriesSplit`):**
  * Divides chronological data into $K = 5$ expanding window splits:
    $$\text{Fold } k: \quad \text{Train} = [t_0, t_k], \quad \text{Validation} = [t_k + 1, t_k + \Delta t]$$
  * **Strict Temporal Directionality:** At no point during training or validation may any future data point be observed.
* **Evaluation Metrics:**
  * Mean Absolute Error:
    $$\text{MAE} = \frac{1}{N} \sum_{i=1}^N |y_i - \hat{y}_i| \quad [\text{Liters / Day}]$$
  * Root Mean Squared Error (RMSE) and Coefficient of Determination ($R^2$).

---

### 3.2. Automated Golden Rule Decision Gate (Requirement R-04)

The evaluation runner compares candidate models against the baseline:
```python
def evaluate_golden_rule(candidate_mae: float, baseline_mae: float) -> GoldenRuleResult:
    r04_passed = candidate_mae < baseline_mae
    improvement_pct = ((baseline_mae - candidate_mae) / baseline_mae) * 100.0
    return GoldenRuleResult(
        passed=r04_passed,
        candidate_mae=candidate_mae,
        baseline_mae=baseline_mae,
        improvement_pct=improvement_pct,
        active_model_type="CANDIDATE" if r04_passed else "SEASONAL_NAIVE_FALLBACK"
    )
```

If `passed == False`:
* Emit warning log: `[ALERT-RT01] Candidate model MAE ({candidate_mae:.3f}) >= Baseline ({baseline_mae:.3f}). Reverting to Seasonal Naive fallback.`
* The registry automatically registers the `SeasonalNaivePredictor` as the active production model to guarantee operational safety.

---

### 3.3. Model Registry and Serialization (`src/ml/registry.py`)

* **Artifact Storage Directory:** `models/production/`
* **Artifacts Persisted:**
  1. `model.joblib`: Binary pipeline containing transformers and fitted estimator.
  2. `metadata.json`: Manifest recording:
     ```json
     {
       "model_id": "glm_gamma_20261031_v1",
       "algorithm": "GLMPredictor",
       "created_at": "2026-10-31T22:00:00Z",
       "r04_passed": true,
       "test_mae": 1.42,
       "baseline_mae": 1.89,
       "improvement_pct": 24.87,
       "train_records_count": 8000,
       "hyperparameters": {"family": "gamma", "alpha": 0.1},
       "features": ["num_fryers", "avg_customers", "type_fritura", "..."]
     }
     ```

---

### 3.4. Unified Inference Engine Facade (`src/ml/inference.py`)

Exposes a clean API for the Stage 300 FastAPI backend:

```python
class InferenceEngine:
    def __init__(self, models_dir: str = "models/production"):
        """Loads the active production model and baseline fallback."""
        pass

    def predict_daily_volume(
        self,
        business_type: str,
        num_fryers: int,
        avg_daily_customers: int,
        day_of_week: int,
        lag_7d_liters: float,
        business_id: Optional[str] = None
    ) -> float:
        """Returns non-negative predicted volume in liters for a business day."""
        pass

    def predict_hours_to_80_percent(
        self,
        current_liters: float,
        capacity_liters: float,
        daily_pour_rate: float
    ) -> float:
        """Returns projected hours until reaching 80% volume threshold."""
        pass
```

---

## 4. CLI Execution Specification (`src/ml/cli.py`)

A full end-to-end training, evaluation, and registry pipeline must be executable via terminal:

```bash
python -m src.ml.cli --data-dir data/processed/ --model-type glm --family gamma
# Options:
#   --model-type: 'glm', 'ridge', 'random_forest', 'hist_gradient_boosting'
#   --enforce-r04: Enforce Golden Rule gate before registry promotion
#   --save-dir: Destination directory (default: 'models/production')
```

---

## 5. Verification and Test Suite (`tests/test_stage_200.py`)

The integration test suite must verify:
1. `test_chronological_split_has_no_future_leakage()`: Asserts timestamps in training strictly precede validation sets in `TimeSeriesSplit`.
2. `test_golden_rule_promotion_when_superior()`: Asserts that when $\text{MAE}_{\text{cand}} < \text{MAE}_{\text{base}}$, the candidate is marked as active.
3. `test_golden_rule_fallback_when_inferior()`: Simulates a degraded model ($\text{MAE} = 10.0$) and asserts that `InferenceEngine` falls back to `SeasonalNaivePredictor` without breaking.
4. `test_inference_engine_non_negative_outputs()`: Asserts all predictions from `InferenceEngine.predict_daily_volume()` are strictly $\ge 0.0$.
5. `test_registry_serialization_and_deserialization()`: Asserts that saving and reloading preserves model weights and metadata fidelity.

---

## 6. Definition of Done for Stage 200

Stage 200 is officially complete when:
1. All baseline and candidate predictors (`SeasonalNaivePredictor`, `LoadCellRateEstimator`, `RegularizedLinearPredictor`, `GLMPredictor`, `TreeEnsemblePredictor`) are implemented and pass unit tests.
2. The Golden Rule evaluator runs on `data/processed/test_chronological.csv` and outputs an audit report comparing MAE.
3. The winning model (or verified fallback) is exported to `models/production/` with its JSON metadata manifest.
4. `InferenceEngine` responds to prediction requests in $< 10\text{ ms}$.
5. `pytest tests/test_stage_200.py` passes with $100\%$ green status.
