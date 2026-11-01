# Subspec 202: Regularized Linear Regression and Generalized Linear Models (GLM)

> **Stage:** `200_etapa_modelos_predictivos_ml`  
> **Subspec ID:** `202`  
> **Deliverable:** Feature Engineering Pipeline, Regularized Regression (Ridge/Lasso), and Non-Negative GLM (Gamma/Poisson)  
> **Target Path:** `src/ml/preprocessor.py`, `src/ml/linear_models.py`  
> **Status:** Executable Implementation Prompt  

---

## 1. Objective and Scope

Implement the primary predictive model architecture specified in **Option 1** of the mathematical study guide:

1. **Feature Engineering Pipeline (`src/ml/preprocessor.py`):** Transforms raw business and daily temporal features into encoded matrices, incorporating one-hot encodings, scaling, 7-day seasonal lags, and explicit domain-specific interaction terms (`business_type × day_of_week`).
2. **Regularized Linear Models (`RegularizedLinearPredictor` in `src/ml/linear_models.py`):** Ordinary Least Squares with $L_2$ (Ridge) and $L_1$ (Lasso) penalties to prevent overfitting on collinear variables.
3. **Generalized Linear Models (`GLMPredictor` in `src/ml/linear_models.py`):** Uses log-link functions with **Gamma** and **Poisson** exponential dispersion families to guarantee that volume predictions are strictly non-negative ($\hat{y} > 0$), matching physical fluid reality.

---

## 2. Mathematical Formulations and Feature Engineering

```
                          FEATURE ENGINEERING & GLM PIPELINE

  ┌─────────────────────────────────┐
  │         RAW FEATURES            │
  │ - business_type, day_of_week    │ ──► [ One-Hot Encoder (k-1 dummies) ] ──┐
  │ - num_fryers, avg_customers     │ ──► [ StandardScaler ]                  ├─► Concatenate
  │ - lag_7d_liters (same day t-7)  │ ──► [ RobustScaler / Imputer ]          │
  └─────────────────────────────────┘                                         │
                                                                              │
  ┌─────────────────────────────────┐                                         │
  │       INTERACTION TERMS         │                                         │
  │ business_type × day_of_week     │ ────────────────────────────────────────┘
  │ num_fryers × avg_customers      │
  └─────────────────────────────────┘
                  │
                  ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │                        ESTIMATOR SELECTION                             │
  ├──────────────────────────────────┬─────────────────────────────────────┤
  │   REGULARIZED LINEAR (L1 / L2)   │   GENERALIZED LINEAR MODEL (GLM)    │
  │   min ||y - Xβ||² + α||β||       │   ln(E[Y|X]) = β₀ + ∑ βⱼXⱼ          │
  │   ŷ = max(0, Xβ)  (clipped)      │   ŷ = exp(Xβ) > 0  (Strictly > 0)    │
  │   (Ridge / Lasso via Scikit)     │   (Gamma / Poisson family)          │
  └──────────────────────────────────┴─────────────────────────────────────┘
```

### 2.1. Feature Matrix Specification

* **Continuous Predictors:**
  * `num_fryers` ($X_1$): Standardized via `StandardScaler`.
  * `avg_daily_customers` ($X_2$): Standardized via `StandardScaler`.
  * `lag_7d_liters` ($X_3$): Volume dumped exactly 7 days prior. If missing (first week of data), imputed with the establishment's historical median.
* **Categorical Predictors:**
  * `business_type` ($X_4$): One-Hot encoded (`drop='first'`).
  * `day_of_week` ($X_5$): One-Hot encoded with Monday as reference ($0 = \text{Mon}, \dots, 6 = \text{Sun}$).
* **Crucial Domain Interactions:**
  Dominican gastronomic activity exhibits distinct type-day dynamics:
  * Street *frituras* experience massive volume increases on Friday/Saturday nights.
  * Commercial *pica pollos* generate peak oil desaturation on Sunday family meal rushes.
  * Student *cafeterias* drop sharply on Saturday and Sunday.
  * Explicit interaction feature vector:
    $$I_{\text{type, day}} = \mathbf{1}_{\{\text{type} = T\}} \times \mathbf{1}_{\{\text{day} = D\}}$$

---

### 2.2. Generalized Linear Models (GLM)

Linear regression assumes Gaussian error with constant variance and can produce negative predictions ($\hat{y} < 0$). SICRA resolves this via GLM:

1. **Log-Link Function:**
   $$\eta_i = g(\mu_i) = \ln(\mu_i) = \beta_0 + \sum_{j=1}^p \beta_j X_{ij} \quad \implies \quad \mu_i = \exp(\eta_i)$$
2. **Distribution Families:**
   * **Gamma Family (`sm.families.Gamma(link=sm.families.links.Log())` or `sklearn.linear_model.GammaRegressor`):**  
     Variance proportional to the square of the mean: $\text{Var}(Y) = \phi \mu^2$. Ideal for continuous positive volumes with constant coefficient of variation.
   * **Poisson Family (`sklearn.linear_model.PoissonRegressor`):**  
     Variance proportional to the mean: $\text{Var}(Y) = \phi \mu$. Robust count-rate formulation.

---

### 2.3. Regularized Linear Estimation (Ridge & Lasso)

When fitting with high-dimensional interaction matrices:
* **Ridge ($L_2$):** Penalizes $\alpha \sum_{j=1}^p \beta_j^2$, shrinking coefficients of correlated predictors.
* **Lasso ($L_1$):** Penalizes $\alpha \sum_{j=1}^p |\beta_j|$, performing automated feature selection by zeroing out non-informative interaction terms.
* **Boundary Safeguard:** All predictions pass through a zero-floor threshold: $\hat{y}_{\text{clipped}} = \max(0.0, \hat{y})$.

---

## 3. Class and Module Specifications

### 3.1. Preprocessing Pipeline: `src/ml/preprocessor.py`

* Class: `FeaturePipeline`
  * Methods:
    * `fit(df: pd.DataFrame) -> "FeaturePipeline"`
    * `transform(df: pd.DataFrame) -> np.ndarray`: Produces the dense feature matrix.
    * `fit_transform(df: pd.DataFrame) -> np.ndarray`
    * `get_feature_names_out() -> List[str]`: Retains human-readable column names for coefficient inspection.

### 3.2. Models Module: `src/ml/linear_models.py`

* Class: `RegularizedLinearPredictor(BasePredictor)`
  * Constructor: `__init__(method: str = "ridge", alpha: float = 1.0)`
  * Attributes: `model_`, `pipeline_`
  * Methods: `fit(X, y)`, `predict(X)`, `get_coefficients() -> Dict[str, float]`
* Class: `GLMPredictor(BasePredictor)`
  * Constructor: `__init__(family: str = "gamma", alpha: float = 0.1)`
  * Attributes: `model_`, `pipeline_`
  * Methods:
    * `fit(X, y)`: Fits either `GammaRegressor` or `PoissonRegressor` (or statsmodels GLM).
    * `predict(X) -> np.ndarray`: Computes $\exp(X\beta)$, asserting strictly positive outputs.
    * `summary() -> str`: Returns model deviance, AIC, and feature weights.

---

## 4. Verification and Test Criteria (`tests/test_linear_models.py`)

1. **Non-Negativity Guarantee:**
   * Generate 1,000 synthetic test samples with extreme inputs (e.g., zero customers, single small fryer).
   * Assert $\min(\hat{y}_{\text{GLM}}) > 0.0$ and $\min(\hat{y}_{\text{Ridge}}) \ge 0.0$.
2. **Interaction Detection:**
   * Verify that the interaction term `business_type[FRITURA] * day_of_week[Saturday]` receives a positive coefficient ($\beta > 0$).
3. **Regularization Penalty Effect:**
   * Fit Ridge with $\alpha = 0.01$ and $\alpha = 100.0$. Assert $\|\beta\|_{\alpha=100} < \|\beta\|_{\alpha=0.01}$.
4. **Serialization Test:**
   * Save and reload models using `joblib`. Assert identical predictions before and after loading.
