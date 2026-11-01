# Especificación General: Etapa 200 - Motor Predictivo y Modelos Matemáticos

> **Proyecto:** Sistema Inteligente para el Control y Recolección de Aceite Vegetal Usado (SICRA)  
> **Área:** Ciencia de Datos, Machine Learning y Modelado Estadístico  
> **Código de Etapa:** `200_etapa_modelos_predictivos_ml`  
> **Propósito:** Guía conceptual, matemática y algorítmica para la construcción, entrenamiento, validación y comparación de los modelos predictivos de generación y acumulación de aceite vegetal usado.

---

## 1. Visión General de la Etapa

El objetivo de esta etapa es dotar a SICRA de inteligencia predictiva para anticipar el flujo diario de aceite generado en cada establecimiento comercial y predecir con precisión cuándo cada contenedor alcanzará el **umbral crítico del 80%**.

Siguiendo las directrices de la *Guía de Estudio del Modelo Predictivo*, el desarrollo del motor se estructura en una jerarquía de cuatro opciones complementarias:

```
┌────────────────────────────────────────────────────────────────────────┐
│             JERARQUÍA DEL SISTEMA PREDICTIVO DE SICRA                  │
├──────────────────────────────────┬─────────────────────────────────────┤
│  OPCIÓN 1: MODELO PRINCIPAL      │  OPCIÓN 2: MODELOS DE REFERENCIA    │
│  - Regresión Lineal Múltiple     │  - Seasonal Naive (mismo día sem.)  │
│  - Interacción (tipo × día)      │  - Tasa de llenado reciente celda   │
│  - Regularización (Ridge/Lasso)  │    (pendiente local $\Delta V/\Delta t$)           │
│  - GLM (Gamma/Poisson) $\ge 0$   │                                     │
├──────────────────────────────────┼─────────────────────────────────────┤
│  OPCIÓN 3: PIPELINE SINTÉTICO    │  OPCIÓN 4: MODELO SECUNDARIO (ML)   │
│  - Validación E2E con Monte Carlo│  - Random Forest / Gradient Boost   │
│  - Análisis de sensibilidad      │  - Preentrenado con 20k-100k filas  │
│  - Marcado 'es_sintetico'        │  - Fine-tuning con datos reales     │
└──────────────────────────────────┴─────────────────────────────────────┘
```

---

## 2. Especificación Matemática de los Modelos

### 2.1. Opción 1: Regresión Mejorada como Modelo Principal

* **Variables de Entrada (Features):**
  * $X_1$: `clientes_por_dia` (variable cuantitativa continua).
  * $X_2$: `num_freidoras_calderos` (variable cuantitativa discreta).
  * $X_3$: `tipo_negocio` (variable categórica codificada con variables indicadoras / *dummies*).
  * $X_4$: `dia_semana` (lunes a domingo, categórica codificada).
  * $X_5$: Término de interacción `tipo_negocio × dia_semana` (captura que una fritura intensifica su producción en fin de semana de forma distinta a una cafetería).
  * $X_6$: Variable rezagada (*lag*): volumen generado el mismo día de la semana anterior ($y_{t-7}$).
* **Tratamiento de No Negatividad (GLM):**
  En un sistema físico de fluidos, la generación de aceite nunca puede ser negativa ($\hat{y} \ge 0$). La regresión lineal ordinaria (OLS) puede predecir valores negativos con valores extremos de entrada. Por ello, se implementan Modelos Lineales Generalizados (GLM) con función de enlace logarítmico:
  $$\ln(\mathbb{E}[Y|X]) = \beta_0 + \sum_{j=1}^{p} \beta_j X_j \quad \implies \quad \hat{y} = \exp\left(\beta_0 + \sum_{j=1}^{p} \beta_j X_j\right) > 0$$
  utilizando familias de distribución **Gamma** o **Poisson**.
* **Control de Sobreajuste (Regularización):**
  * Penalización Ridge ($L_2$) para estabilizar coeficientes multicolineales.
  * Penalización Lasso ($L_1$) para descartar automáticamente variables de bajo impacto.

---

### 2.2. Opción 2: Modelos de Referencia Simples (Baselines)

Para evaluar si el modelo de machine learning aporta verdadero valor operativo, se deben implementar dos modelos de referencia obligatorios:

1. **Seasonal Naive Baseline (Estacionalidad Semanal):**
   Pronostica para hoy el promedio histórico de los días equivalentes pasados:
   $$\hat{y}_{\text{naive}}(t) = \frac{1}{K}\sum_{k=1}^{K} y_{\text{mismo día de la semana en semanas anteriores}}$$
2. **Tasa de Llenado Reciente de la Celda de Carga:**
   Regresión lineal local sobre las lecturas efectivas de los últimos $N$ días/horas para calcular la pendiente volumétrica ($\text{litros/hora}$):
   $$m = \frac{\Delta V}{\Delta t} \quad \implies \quad t_{80\%} = t_{\text{actual}} + \frac{0.80 \cdot V_{\text{capacidad}} - V_{\text{actual}}}{m}$$
   Este método resulta sumamente robusto para pronósticos de corto plazo (24 a 48 horas).

---

### 2.3. Opción 4: Modelos Ensamblados Avanzados (Comparación Secundaria)

* Implementación con `RandomForestRegressor` y `HistGradientBoostingRegressor` (Scikit-Learn).
* **Estrategia de Transferencia / Fine-Tuning:**
  1. Se preentrena el ensamble sobre el dataset sintético masivo generado en la Etapa 100 ($\ge 20,000$ muestras) para que aprenda las relaciones no lineales globales.
  2. Se reajustan los árboles terminales o se hace ajuste fino (*fine-tuning*) con el conjunto de datos reales recolectados en campo.
* **Interpretabilidad:** Extracción de importancia de variables (*Feature Importance* / valores SHAP) para documentar qué factores pesan más en la generación de aceite.

---

## 3. Protocolo de Evaluación y "Regla de Oro"

### 3.1. Partición Cronológica Estricta (Anti Data Leakage)
* **Prohibido:** Particiones aleatorias tipo `train_test_split(shuffle=True)`. Al tratarse de series de tiempo, una división aleatoria comete *fuga de información del futuro hacia el pasado*.
* **Requerido:** División cronológica secuencial (`TimeSeriesSplit`):
  * Entrenamiento: registros del pasado ($t_0$ a $t_{\text{corte}}$).
  * Prueba (*Test Set*): registros del futuro más reciente ($t_{\text{corte}+1}$ a $t_{\text{final}}$).

### 3.2. Métrica Objetivo y Regla de Decisión

Se adopta como métrica estándar el **Error Absoluto Medio (MAE)** por su interpretación física directa en litros/día:
$$\text{MAE} = \frac{1}{n} \sum_{i=1}^{n} |y_i - \hat{y}_i|$$

> **Regla de Oro:**  
> En el conjunto de prueba con datos reales, el modelo solo se considera aceptado para producción si cumple estrictamente el requisito **R-04**:
> $$\text{MAE}_{\text{modelo}} < \text{MAE}_{\text{referencia}}$$
> Si el modelo complejo no supera al modelo de referencia, el sistema en producción debe conmutar automáticamente al modelo estacional simple (*safe fallback*).

---

## 4. Recursos Educativos y Lecturas Recomendadas (Further Reading)

### Bloque 0: Base en Python para Datos
* **Kaggle Learn (Cursos Prácticos Gratuitos):**
  * *Python:* Sintaxis, estructuras de control y funciones.
  * *Pandas:* Lectura de CSVs, indexación cronológica, agregación (`groupby`) y limpieza de nulos.
  * *Data Visualization:* Gráficos de dispersión y series temporales con Matplotlib y Seaborn.

### Bloque 1: Regresión Lineal, Regularización y GLM (StatQuest & Libros)
* **Canal de YouTube StatQuest (Josh Starmer):**
  * *"Linear Regression and OLS Explained Step-by-Step"*
  * *"Ridge Regression Explained"* y *"Lasso Regression Explained"*
  * *"Generalized Linear Models (GLM)":* Comprensión de distribuciones exponenciales y función link.
* **Libro Texto de Referencia:**
  * *James, G., Witten, D., Hastie, T., & Tibshirani, R.* **An Introduction to Statistical Learning (ISLR)**:
    * *Capítulo 3:* Linear Regression (interpretación de coeficientes, errores estándar y p-valores).
    * *Capítulo 6:* Linear Model Selection and Regularization. Disponible en [statlearning.com](https://www.statlearning.com/).

### Bloque 2: Evaluación y Modelos de Referencia para Series de Tiempo
* **Forecasting: Principles and Practice (FPP3) - Hyndman & Athanasopoulos:**
  * *Capítulo 5:* "The forecaster's toolbox" — Benchmarks simples (*Naive, Seasonal Naive*), métricas de precisión MAE/RMSE y validación cruzada temporal. Disponible en [otexts.com/fpp3](https://otexts.com/fpp3/).
* **StatQuest:**
  * *"Cross Validation"* y *"Bias-Variance Tradeoff"*.

### Bloque 4: Árboles de Decisión y Gradient Boosting
* **StatQuest:**
  * *"Decision Trees"*, *"Random Forests"* y serie de *"Gradient Boost"*.
* **Documentación Oficial Scikit-Learn:**
  * `sklearn.ensemble.RandomForestRegressor`
  * `sklearn.ensemble.HistGradientBoostingRegressor`
