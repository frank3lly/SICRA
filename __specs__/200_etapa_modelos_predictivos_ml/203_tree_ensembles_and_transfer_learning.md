# Subspec 203: Tree Ensembles, Pre-Training, and Fine-Tuning Pipeline

> **Stage:** `200_etapa_modelos_predictivos_ml`  
> **Subspec ID:** `203`  
> **Deliverable:** Random Forest, Gradient Boosting, Synthetic Pre-Training, and Fine-Tuning Pipeline  
> **Target Path:** `src/ml/ensemble_models.py`  
> **Status:** Executable Implementation Prompt  

---

## 1. Objective and Scope

Implement the advanced non-linear ensemble models and tabular transfer learning workflow specified in **Option 4** of the mathematical study guide:

1. **Non-Linear Tree Estimators (`src/ml/ensemble_models.py`):** Wrappers around Scikit-Learn's `RandomForestRegressor` and `HistGradientBoostingRegressor` to capture complex interaction patterns and non-linearities without manual feature engineering.
2. **Two-Stage Pre-Training & Fine-Tuning Pipeline:**
   * **Stage A (Pre-training):** Pre-train the ensemble on the massive synthetic dataset ($\ge 50,000$ rows) generated in Stage 100 to establish baseline structural representations of fryer count, day-of-week peaks, and customer scaling.
   * **Stage B (Fine-Tuning / Adaptation):** Calibrate the model against scarce real field observations ($\approx 70\text{ to }140$ empirical records) using sample re-weighting and warm-start tree addition.
3. **Model Interpretability:** Compute Mean Decrease in Impurity (MDI) and Permutation Feature Importance to explain model decisions to stakeholders.

---

## 2. Architecture and Methodological Workflow

```
                   SYNTHETIC PRE-TRAINING & REAL-DATA FINE-TUNING
                   
  ┌───────────────────────────────┐
  │  Stage 100 Synthetic Data     │ ──► [ Phase 1: Heavy Pre-Training ]
  │  (50,000+ Monte Carlo rows)   │       Fits 150 base decision trees
  └───────────────────────────────┘       Learns general domain physics
                                                        │
                                                        ▼
  ┌───────────────────────────────┐       ┌───────────────────────────────┐
  │   Real Field Observations     │ ────► │ Phase 2: Fine-Tuning / Tuning │
  │   (70 to 140 empirical rows)  │       │ Weighted Calibration (w=10x)  │
  └───────────────────────────────┘       │ or warm-start incremental fit │
                                          └───────────────┬───────────────┘
                                                          │
                                                          ▼
                                          ┌───────────────────────────────┐
                                          │  DEPLOYED ENSEMBLE PREDICTOR  │
                                          │  + Feature Importance Report  │
                                          └───────────────────────────────┘
```

---

## 3. Mathematical and Algorithmic Specifications

### 3.1. Tree Ensemble Estimators

1. **Random Forest (`RandomForestRegressor`):**
   * Aggregates $B$ bootstrap-aggregated regression trees:
     $$\hat{y}_{\text{rf}}(x) = \frac{1}{B} \sum_{b=1}^B T_b(x)$$
   * Default hyperparameters: `n_estimators=100`, `max_depth=12`, `min_samples_split=5`, `random_state=42`.
2. **Histogram-Based Gradient Boosting (`HistGradientBoostingRegressor`):**
   * Sequentially minimizes absolute loss ($L_1$) or Poisson deviance using gradient descent in functional space:
     $$F_m(x) = F_{m-1}(x) + \gamma_m h_m(x)$$
   * Handles categorical variables natively without extensive dummy expansion (`categorical_features` parameter).

---

### 3.2. Two-Stage Fine-Tuning Strategy

Because empirical data from the 5 pilot businesses in San Pedro de Macorís is initially small, training a 200-tree ensemble solely on real data leads to extreme variance and overfitting. The fine-tuning module implements two complementary strategies:

* **Strategy 1: Sample Weighting Mixture (Recommended):**
  Combine synthetic and real datasets with differential sample weights:
  $$w_i = \begin{cases} 
  1.0, & \text{if } \text{is\_synthetic}_i = \text{True} \\
  \omega_{\text{real}}, & \text{if } \text{is\_synthetic}_i = \text{False} \quad (\text{where } \omega_{\text{real}} \in [5.0, 15.0])
  \end{cases}$$
  The objective function forces the loss minimization to prioritize empirical ground truth by an order of magnitude while maintaining regularized structural priors from the simulation.
* **Strategy 2: Warm-Start Incremental Fitting:**
  Pre-train on synthetic data with $B_1 = 100$ trees, then enable `warm_start=True` and fit an additional $B_2 = 50$ trees using solely the real dataset.

---

### 3.3. Interpretability and Feature Importance

The module must expose a ranking of predictive impact:
1. **MDI (Gini / Impurity Reduction):** Rapid feature ranking directly from tree split metrics (`feature_importances_`).
2. **Permutation Importance:** Assesses validation MAE increase when a feature column is randomly shuffled (`sklearn.inspection.permutation_importance`).

---

## 4. Class and Module Specifications (`src/ml/ensemble_models.py`)

* Class: `TreeEnsemblePredictor(BasePredictor)`
  * Constructor:
    ```python
    def __init__(
        self,
        algorithm: str = "hist_gradient_boosting", # or 'random_forest'
        n_estimators: int = 150,
        max_depth: int = 10,
        loss: str = "absolute_error", # or 'poisson'
        random_state: int = 42
    )
    ```
  * Methods:
    * `fit(X, y, sample_weight=None) -> "TreeEnsemblePredictor"`
    * `pretrain_and_finetune(X_synth, y_synth, X_real, y_real, real_weight_multiplier: float = 10.0) -> "TreeEnsemblePredictor"`
    * `predict(X) -> np.ndarray`: Strictly non-negative output ($\hat{y} \ge 0$).
    * `get_feature_importances(feature_names: List[str]) -> pd.DataFrame`: Returns sorted dataframe with columns `['feature', 'importance']`.

---

## 5. Verification and Test Criteria (`tests/test_ensemble_models.py`)

1. **Pre-Training & Fine-Tuning Continuity:**
   * Fit pre-training on 2,000 synthetic rows. Verify baseline MAE.
   * Execute fine-tuning on 100 real rows. Assert training loss converges cleanly without runtime exceptions or NaN values.
2. **Feature Importance Sanity:**
   * Assert that `num_fryers` or `avg_daily_customers` ranks among the top 3 most important features (reflecting physical kitchen capacity).
3. **Non-Negativity Constraint:**
   * Ensure all predictions satisfy $\hat{y} \ge 0.0$ regardless of input edge cases.
4. **Reproducibility Test:**
   * With `random_state=42`, two separate runs must generate identical predictions down to $10^{-6}$ precision.
