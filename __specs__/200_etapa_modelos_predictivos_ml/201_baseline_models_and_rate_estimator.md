# Subspec 201: Baseline Models and Short-Term Rate Estimator

> **Stage:** `200_etapa_modelos_predictivos_ml`  
> **Subspec ID:** `201`  
> **Deliverable:** Abstract Base Predictor Interface, Seasonal Naive Baseline Model, and Recent Load Cell Fill Rate Estimator  
> **Target Path:** `src/ml/base.py`, `src/ml/baselines.py`, `src/ml/rate_estimator.py`  
> **Status:** Executable Implementation Prompt  

---

## 1. Objective and Scope

Implement the foundational prediction interface and the two baseline benchmark models required by Option 2 of the mathematical study guide:

1. **`BasePredictor` Abstract Class (`src/ml/base.py`):** Standardizes fit, predict, save, load, and metric evaluation methods across all models in the SICRA system.
2. **`SeasonalNaivePredictor` (`src/ml/baselines.py`):** The primary benchmark required for Requirement **R-04**. Forecasts daily volume using the historical empirical average of the same day of the week for each specific food establishment.
3. **`LoadCellRateEstimator` (`src/ml/rate_estimator.py`):** A high-precision short-term estimator calculating the real-time slope of volume change ($\Delta V / \Delta t$) from recent continuous load cell readings to project exact hours remaining until reaching the critical $80\%$ capacity threshold.

---

## 2. Mathematical Formulations

```
                       BENCHMARK & RATE ESTIMATION PIPELINE

  ┌───────────────────────────────┐               ┌───────────────────────────────┐
  │   SEASONAL NAIVE BENCHMARK    │               │    LOAD CELL RATE ESTIMATOR   │
  │   (Option 2 - Daily Baseline) │               │    (Option 2 - Short-Term)    │
  ├───────────────────────────────┤               ├───────────────────────────────┤
  │   Historical average for the  │               │ Local linear slope: m = ΔV/Δt │
  │   exact same day of the week  │               │ Hours to 80% = (0.8·Vmax - V)/m│
  │   ŷ(b, d) = mean(y_{b, d})    │               │ Rolling window: 24h to 72h    │
  └───────────────────────────────┘               └───────────────────────────────┘
```

### 2.1. Seasonal Naive Benchmark Formulation

For a given business $b$ and target day of the week $d \in \{0, 1, \dots, 6\}$:
$$\hat{y}_{\text{naive}}(b, d) = \frac{1}{|K_{b, d}|} \sum_{k \in K_{b, d}} y_{b, d, k}$$

* Where $K_{b, d}$ is the set of all observed historical daily volumes for business $b$ on weekday $d$.
* **Global Fallback:** If a business has zero historical observations for that weekday (e.g. newly onboarded establishment), fallback to the average of that weekday across all businesses of the same `business_type`. If still empty, fallback to the global daily mean.

---

### 2.2. Recent Load Cell Fill Rate Estimator ($\Delta V / \Delta t$)

Given time-series load cell telemetry readings $\{(t_i, V_i)\}_{i=1}^N$ over a sliding retrospective window $W$ (default: last $24$ to $48$ operational hours, filtering out drain/collection events):

1. **Local Linear Rate Calculation (Ordinary Least Squares Slope):**
   $$m = \frac{\sum_{i=1}^N (t_i - \bar{t})(V_i - \bar{V})}{\sum_{i=1}^N (t_i - \bar{t})^2} \quad [\text{Liters / Hour}]$$
2. **Time to Critical Threshold ($80\%$ Capacity):**
   $$\text{Hours to 80\%} = \begin{cases} 
   \dfrac{0.80 \cdot V_{\text{capacity}} - V_{\text{current}}}{m}, & \text{if } m > 0 \text{ and } V_{\text{current}} < 0.80 \cdot V_{\text{capacity}} \\
   0.0, & \text{if } V_{\text{current}} \ge 0.80 \cdot V_{\text{capacity}} \\
   \infty, & \text{if } m \le 0 \text{ (container inactive or emptied)}
   \end{cases}$$
3. **Robustness Safeguards:**
   * Exclude sudden negative volume drops ($\Delta V < -5.0\text{ L}$) caused by oil collection or tare resets.
   * Apply median filtering across the window to eliminate transient sensor noise ($\epsilon \sim \mathcal{N}(0, 0.03\text{ kg})$).

---

## 3. Class and Method Specifications

### 3.1. Base Class: `src/ml/base.py`

```python
from abc import ABC, abstractmethod
import pandas as pd
import numpy as np

class BasePredictor(ABC):
    @abstractmethod
    def fit(self, X: pd.DataFrame, y: pd.Series) -> "BasePredictor":
        """Fits model parameters on historical features and daily volumes."""
        pass

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Returns non-negative predicted volumes in liters/day."""
        pass

    def evaluate_mae(self, X: pd.DataFrame, y: pd.Series) -> float:
        """Computes Mean Absolute Error against ground truth."""
        preds = self.predict(X)
        return float(np.mean(np.abs(y.to_numpy() - preds)))
```

### 3.2. Seasonal Naive Predictor: `src/ml/baselines.py`

* Class: `SeasonalNaivePredictor(BasePredictor)`
* Attributes:
  * `lookup_table_`: Nested dictionary `{business_id: {day_of_week: mean_volume}}`.
  * `type_lookup_`: Dictionary `{business_type: {day_of_week: mean_volume}}`.
  * `global_mean_`: Float default.
* Methods:
  * `fit(X, y)`: Builds lookup tables by grouping by `['business_id', 'day_of_week']` and `['business_type', 'day_of_week']`.
  * `predict(X)`: Vectorized lookup with hierarchical fallbacks.
  * `save(path)` / `load(path)`: Serializes lookup tables via `joblib`.

### 3.3. Fill Rate Estimator: `src/ml/rate_estimator.py`

* Class: `LoadCellRateEstimator`
* Constructor parameters: `window_hours: int = 48`, `min_samples: int = 6`.
* Methods:
  * `calculate_slope(telemetry_df: pd.DataFrame) -> float`: Returns $m$ in Liters/hour.
  * `estimate_hours_to_threshold(telemetry_df: pd.DataFrame, capacity_liters: float, threshold_pct: float = 0.80) -> Optional[float]`.
  * `detect_drain_event(telemetry_df: pd.DataFrame) -> bool`: Identifies abrupt drops ($> 30\%$ capacity reduction in $< 1\text{ hour}$).

---

## 4. Verification and Test Criteria (`tests/test_baselines.py`)

1. **Seasonal Naive Invariance:**
   * Fit on historical data and assert predictions for the same business on Mondays always yield the historical Monday mean.
2. **Fallback Integrity:**
   * Pass an unseen `business_id` and assert it falls back to the `business_type` average without raising KeyErrors.
3. **Slope Rate Accuracy:**
   * Provide a synthetic linear series ($0.5\text{ L/hour}$ over $24\text{ hours}$ on a $50\text{L}$ container starting at $10\text{L}$).
   * Assert estimated hours to $80\%$ ($40\text{L}$) equals exactly $\frac{40 - 22}{0.5} = 36.0\text{ hours} \pm 0.1\text{ h}$.
4. **Non-Negativity Constraint:**
   * Assert all outputs are $\ge 0.0$.
