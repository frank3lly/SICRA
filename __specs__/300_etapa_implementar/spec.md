# Especificación General: Etapa 300 - Implementar (I-3.0)

> **Proyecto:** Sistema Inteligente para el Control y Recolección de Aceite Vegetal Usado (SICRA)  
> **Metodología:** Marco CDIO (Concebir – Diseñar – Implementar – Operar)  
> **Código de Etapa:** `300_etapa_implementar`  
> **Propósito del Documento:** Guía práctica, experimental y de validación para la adquisición de componentes, construcción del prototipo físico, recolección empírica de datos, entrenamiento/ajuste del modelo predictivo y ejecución de pruebas de laboratorio y campo.

---

## 1. Visión General de la Etapa

La etapa **300 - Implementar** representa la materialización física y lógica del proyecto SICRA. En esta fase convergen el montaje de hardware en los bidones de Polietileno de Alta Densidad (PEAD), la calibración metrológica de la celda de carga con el conversor HX711, la recopilación manual de datos reales en los negocios de comida frita seleccionados y el entrenamiento computacional del pipeline de Machine Learning en Python.

Durante esta etapa se somete a prueba la hipótesis técnica del proyecto a través de pruebas de estrés térmico, pruebas de descarga de baterías para autonomía de 30 días, corte intencional de conectividad para verificar el guardado en memoria no volátil, y la validación numérica de la **Regla de Oro**: el modelo de regresión debe superar fehacientemente al modelo de referencia en datos reales futuros no vistos.

---

## 2. Paquetes de Trabajo de la Etapa (EDT / WBS)

```
                            ┌────────────────────────────────────────┐
                            │        I-3.0 FASE IMPLEMENTAR          │
                            └───────────────────┬────────────────────┘
                                                │
         ┌──────────────────────────────┬───────┴──────────────┬──────────────────────────────┐
         ▼                              ▼                      ▼                              ▼
┌──────────────────┐          ┌──────────────────┐   ┌──────────────────┐           ┌──────────────────┐
│      I-3.1       │          │      I-3.2       │   │      I-3.3       │           │      I-3.4       │
│ Recolección      │          │ Adquisición,     │   │ Entrenamiento    │           │ Calibración,     │
│ Manual Datos CSV │          │ Construcción y   │   │ y Validación     │           │ Pruebas Red y    │
│ (>= 70 filas)    │          │ Ensamble Físico  │   │ Modelo Python    │           │ Piloto           │
└──────────────────┘          └──────────────────┘   └──────────────────┘           └──────────────────┘
```

### Paquete I-3.1: Recolección Manual de Datos de Entrenamiento
* **Responsable / Aprobador:** Equipo multidisciplinario (Dahiana, Carlos, Félix, Anlly, Johalfry, Marian - R) / Yamilet (Industrial) (A).
* **Alcance práctico:**
  * Visitas diarias programadas a los $\ge 5$ establecimientos candidatos seleccionados durante un período de 14 días continuos (garantizando al menos 2 registros por cada día de la semana para capturar efectos de estacionalidad semanal).
  * Registro de variables en cada visita:
    * Litros reales vertidos por día (medidos con probeta / recipiente graduado de referencia).
    * Cantidad de clientes atendidos en la jornada.
    * Número de freidoras o calderos en servicio activo.
    * Tipo de negocio y día de la semana.
  * Consolidación y limpieza de la base de datos cruda en formato `dataset_entrenamiento_real.csv` ($\ge 70$ observaciones completas sin valores nulos).
* **Entregable:** Archivo CSV de entrenamiento validado y foliado.
* **Criterio de Aceptación:** $\ge 70$ registros completos verificados; cero celdas vacías.

### Paquete I-3.2: Adquisición de Componentes, Construcción y Ensamble
* **Responsable / Aprobador:** Dahiana, Félix, Anlly, Johalfry (R) / Carlos (Electromecánica) (A/R).
* **Alcance práctico:**
  * Compra y recepción de piezas según la lista de materiales cotizada (ESP32, celda de carga de 20 a 50 kg, HX711, 2 baterías 18650 con portabaterías y regulador, caja plástica IP65, cableado y protoboard).
  * Mecanizado y perforación del soporte de la base del bidón PEAD garantizando que todo el peso descanse de forma ortogonal sobre la celda de carga sin rozamientos parásitos en las paredes.
  * Integración de patas antivibración de goma y nivel de burbuja circular en la base.
  * Montaje de la electrónica en caja sellada aislada térmicamente del contacto directo con grasa caliente o vapor (mitigación de riesgos RG-01 y RG-05).
* **Entregable:** 1 prototipo físico ensamblado, funcional y documentado en manual de armado.
* **Criterio de Aceptación:** Prototipo estructuralmente estable; costo total dentro del límite presupuestario (R-06).

### Paquete I-3.3: Entrenamiento, Ajuste y Validación del Modelo Predictivo
* **Responsable / Aprobador:** Marian (R) / Félix (Software) (A/R) en coordinación con Yamilet (Industrial).
* **Alcance práctico:**
  * Desarrollo del script de entrenamiento en Python (`train_model.py`) usando Pandas, NumPy y Scikit-Learn / Statsmodels.
  * Implementación de tubería de datos sintéticos con simulación Monte Carlo (generación de 20,000 a 100,000 registros sintéticos para pruebas de robustez del software y pre-entrenamiento de árboles de decisión / gradient boosting).
  * Partición cronológica estricta: los primeros 10 días para entrenamiento y los últimos 4 días más recientes como conjunto de prueba ciego (*test set*).
  * Cálculo del modelo base de referencia (*seasonal naive*):
    $$\hat{y}_{\text{ref}}(d) = \text{promedio histórico del mismo día de la semana en ese local}$$
  * Ajuste de la regresión lineal múltiple con regularización y cálculo del Error Absoluto Medio (MAE):
    $$\text{MAE} = \frac{1}{n} \sum_{i=1}^{n} |y_i - \hat{y}_i|$$
  * Verificación rigurosa del requisito R-04:
    $$\text{MAE}_{\text{modelo}} < \text{MAE}_{\text{referencia}} \quad \text{en el conjunto de prueba}$$
* **Entregable:** Script reproducible en Python, modelo exportado y reporte formal de errores comparativos.
* **Criterio de Aceptación:** $\text{MAE}_{\text{modelo}} < \text{MAE}_{\text{ref}}$ en datos reales de prueba. Si no cumple, se activa inmediatamente el retorno RT01.

### Paquete I-3.4: Calibración Metrológica, Transmisión y Piloto
* **Responsable / Aprobador:** Félix, Johalfry, Marian (R) / Carlos (Electromecánica) (A/R).
* **Alcance práctico:**
  * Procedimiento de calibración en 5 puntos de peso patrón conocido (ej. 2 kg, 5 kg, 10 kg, 15 kg, 20 kg):
    * Ajuste de la ganancia y tara en el firmware del ESP32.
    * Verificación de repetibilidad: desviación estándar $\le 0.1\text{ kg}$ en 10 lecturas consecutivas.
    * Verificación de exactitud: error de pesaje $\le \pm 0.5\text{ kg}$ (R-01).
    * Comprobación de conversión volumétrica: error de volumen $\le 3\%$ en 3 pruebas de vertido con aceite graduado.
  * Prueba de simulación de corte de conectividad Wi-Fi (R-09):
    * Apagado del router durante el pesaje; verificación de almacenamiento en cola de memoria Flash del ESP32; reanudación de la red y confirmación de que todas las mediciones pendientes se enviaron al servidor sin pérdidas ni duplicados.
  * Prueba de descarga de batería en 7 días para validar tasa de consumo en miliamperios-hora y confirmar autonomía proyectada $\ge 30$ días (R-02).
* **Entregable:** Informe técnico de calibración metrológica y registro de pruebas de transmisión y corte de red.
* **Criterio de Aceptación:** Cumplimiento simultáneo de tolerancias de R-01, R-02 y R-09.

---

## 3. Matriz RACI de la Etapa 300

| Paquete de Trabajo | Dahiana (Civil) | Carlos (Electromec.) | Yamilet (Industrial) | Félix (Software) | Anlly (Civil) | Johalfry (Civil) | Marian (Ciberseg.) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **I-3.1 Recolección manual datos** | **R** | C | **A** | C | **R** | **R** | C |
| **I-3.2 Adquisición, ensamble** | C | **A/R** | C | **R** | **R** | **R** | C |
| **I-3.3 Entrenamiento y validación**| C | C | C | **A/R** | I | I | **R** |
| **I-3.4 Calibración y pruebas red** | C | **A/R** | C | **R** | I | C | **R** |
| **QA y Documentación previa piloto** | **R** | **R** | **A** | **R** | **R** | **R** | **R** |

---

## 4. Retornos Técnicos (Feedback Loops) en Acción

Esta etapa concentra la mayor cantidad de validaciones empíricas y es el origen de tres retornos críticos:

1. **RT01 (Implementar I-3.3 $\rightarrow$ Diseñar D-2.4):**
   * *Disparador:* El error absoluto medio del modelo predictivo en el conjunto de prueba es mayor o igual al modelo de referencia ($\text{MAE}_{\text{modelo}} \ge \text{MAE}_{\text{ref}}$).
   * *Acción:* Regresar a la fase de diseño para replantear la especificación matemática: probar transformaciones logarítmicas, añadir términos de interacción (ej. tipo de comida $\times$ día), ajustar parámetros de regularización Ridge/Lasso, o ampliar el volumen de muestras de entrenamiento en I-3.1.
   * *Aprobador de retorno:* Yamilet (Industrial).
2. **RT02 (Implementar I-3.4 $\rightarrow$ Diseñar D-2.2):**
   * *Disparador:* La celda presenta un error de pesaje $> \pm 0.5\text{ kg}$ tras calibrar, o se observa deriva térmica/mecánica intolerable.
   * *Acción:* Rediseñar la etapa de amplificación, apantallamiento de cables HX711, desacoplo de masa o corregir la fijación mecánica de la base.
   * *Aprobador de retorno:* Carlos (Electromecánica).
3. **RT03 (Implementar I-3.1 $\rightarrow$ Concebir C-1.1):**
   * *Disparador:* Algún local medido arroja una dispersión incontrolable o genera volúmenes que desbordan las premisas del prototipo.
   * *Acción:* Redefinir la capacidad del recipiente o sustituir el local en la fase de delimitación.
   * *Aprobador de retorno:* Carlos (Electromecánica).

---

## 5. Recursos Educativos y Lecturas Recomendadas (Further Reading)

### Simulación de Datos y Modelos Ensamblados (Guía de Estudio Bloques 3 y 4)
* **Simulación Monte Carlo y Generación de Datos Sintéticos:**
  * *NumPy Documentation:* Módulo `numpy.random.Generator` (generación de distribuciones Poisson, Normal truncada y Gamma para modelar vertido de fluidos).
  * En YouTube: *"Monte Carlo simulation explained with Python"* y *"Synthetic data generation for machine learning workflows"*.
  * Concepto de *Domain Randomization* y Brecha Simulación-Realidad (*Sim-to-Real Gap*).
* **Modelos Basados en Árboles (Random Forest y Gradient Boosting):**
  * *StatQuest con Josh Starmer:*
    * *"Decision Trees":* Construcción de árboles de regresión, división por reducción de varianza.
    * *"Random Forests Part 1 & Part 2":* Agregación por Bootstrap (Bagging) y estimación Out-of-Bag.
    * *"Gradient Boost Part 1 & Part 2":* Ajuste secuencial sobre residuos (*pseudo-residuals*).
  * *Kaggle Learn:* Cursos *"Intro to Machine Learning"* y *"Intermediate Machine Learning"*.
  * *Scikit-learn Docs:* `sklearn.ensemble.RandomForestRegressor` y `sklearn.ensemble.HistGradientBoostingRegressor`.
  * *Estrategia de Fine-Tuning:* Pre-entrenamiento con datos sintéticos simulados ($\approx 50,000$ filas) para estabilizar hiperparámetros y ajuste fino con los datos reales de los 5 locales piloto.

### Metrología, Instrumentación y Validación de Ensayos
* **Normas Metrológicas para Instrumentos de Pesaje:**
  * *OIML R 60:* "Metrological regulation for load cells" — Organización Internacional de Metrología Legal.
  * Conceptos de histéresis, no linealidad, fluencia (*creep*) y coeficiente de temperatura en galgas extensométricas.
* **Pruebas de Baterías y Gestión Energética en Sistemas Embebidos:**
  * Cálculo de tasa de descarga Peukert en baterías de Litio 18650 y perfiles de corriente con osciloscopio / multímetro de banco.
