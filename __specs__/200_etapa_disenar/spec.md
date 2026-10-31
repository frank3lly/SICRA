# Especificación General: Etapa 200 - Diseñar (D-2.0)

> **Proyecto:** Sistema Inteligente para el Control y Recolección de Aceite Vegetal Usado (SICRA)  
> **Metodología:** Marco CDIO (Concebir – Diseñar – Implementar – Operar)  
> **Código de Etapa:** `200_etapa_disenar`  
> **Propósito del Documento:** Guía técnica, de ingeniería de detalle y metodológica para comprender la etapa de diseño de hardware, firmware, modelo predictivo, plataforma web, ciberseguridad y logística de rutas de SICRA.

---

## 1. Visión General de la Etapa

La etapa **200 - Diseñar** transforma los requerimientos y el concepto general definidos en la etapa 100 en especificaciones técnicas de ingeniería listas para ser ensambladas y programadas. Abarca seis disciplinas estrechamente interconectadas:

1. **Diseño Mecánico y Estructural:** Contenedor de Polietileno de Alta Densidad (PEAD), soporte de celda y protección térmica/vuelco.
2. **Diseño Electrónico:** Sensorica de pesaje (celda de carga + módulo convertidor HX711), acondicionamiento de potencia (baterías 18650) y cálculo de balance energético.
3. **Diseño de Firmware (ESP32):** Lógica embebida, filtrado estadístico, cálculo de litros según densidad, gestión de sueño profundo (*deep-sleep*) y almacenamiento local resiliente ante fallas de red.
4. **Diseño del Modelo Predictivo:** Formulación matemática de regresión lineal múltiple con regularización y GLM, selección de variables explicativas, definición de partición cronológica (*time-split*) y métrica objetivo frente a un modelo base (*seasonal naive*).
5. **Diseño de Software y Web:** Arquitectura de base de datos relacional, scripts de procesamiento periódico y panel de visualización logística con alertas al 80%.
6. **Diseño de Seguridad y Rutas:** Esquemas de autorización por roles (RBAC), cifrado en tránsito y modelo de optimización logística para agrupamiento de rutas.

---

## 2. Paquetes de Trabajo de la Etapa (EDT / WBS)

```
                            ┌────────────────────────────────────────┐
                            │          D-2.0 FASE DISEÑAR            │
                            └───────────────────┬────────────────────┘
                                                │
         ┌───────────────┬───────────────┬──────┴────────┬───────────────┬───────────────┐
         ▼               ▼               ▼               ▼               ▼               ▼
    ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
    │  D-2.1  │     │  D-2.2  │     │  D-2.3  │     │  D-2.4  │     │  D-2.5  │     │  D-2.6  │
    │ Recipi- │     │ Diseño  │     │Firmware │     │ Modelo  │     │ Base de │     │ Seguri- │
    │  ente   │     │ Electr. │     │  ESP32  │     │Predict. │     │Datos/Web│     │   dad   │
    └─────────┘     └─────────┘     └─────────┘     └─────────┘     └─────────┘     └────┬────┘
                                                                                         │
                                                                                    ┌────┴────┐
                                                                                    │  D-2.7  │
                                                                                    │  Rutas  │
                                                                                    └─────────┘
```

### Paquete D-2.1: Diseño del Recipiente y Estructura Mecánica
* **Responsable / Aprobador:** Carlos, Johalfry, Anlly (R) / Dahiana (A).
* **Alcance técnico:**
  * Selección de cubicaje en bidones de PEAD adaptado al volumen de cada local piloto.
  * Cálculo de carga máxima estructural y distribución uniforme del peso sobre la celda.
  * Base con apoyos de goma antivibración y nivel de burbuja para garantizar verticalidad del vector de carga (mitigación del riesgo RG-02).
  * Aislamiento y compartimentación: ubicación del habitáculo electrónico a una distancia mínima segura de calor ($\ge 1.5$ m de calderos/freidoras, mitigación de riesgos RG-01 y RG-05).
* **Entregable:** Planos/croquis de ensamble mecánico y memoria de cálculo de carga admisible.

### Paquete D-2.2: Diseño Electrónico y Gestión Energética
* **Responsable / Aprobador:** Carlos (Electromecánica) (A/R).
* **Alcance técnico:**
  * Circuito de lectura de puente de Wheatstone con celda de carga resistiva y conversor ADC de 24 bits HX711 conectado al microcontrolador ESP32.
  * Módulo elevador/regulador de voltaje alimentado por dos baterías de iones de litio 18650 (2000 a 3000 mAh).
  * Cálculo de perfil de consumo energético: corriente en reposo ($I_{sleep}$) y corriente activa en transmisión Wi-Fi ($I_{tx}$).
  * Modelado de ciclo de trabajo (*duty-cycle*) para garantizar una autonomía mínima $\ge 30$ días sin conexión a red eléctrica de pared (Requisito R-02).
* **Entregables:** Diagrama esquemático eléctrico, lista de materiales preliminar (BOM) y balance energético calculado.

### Paquete D-2.3: Especificación del Firmware del ESP32
* **Responsable / Aprobador:** Félix (Software) (A/R).
* **Alcance técnico:**
  * Secuencia de operación: despertar por temporizador o por evento de interacción $\rightarrow$ excitación de celda $\rightarrow$ estabilización de señal.
  * Algoritmo de filtrado: toma de $\ge 10$ muestras consecutivas, cálculo de mediana y descarte de lecturas atípicas (*outliers*) generadas por vibración o impacto accidental.
  * Algoritmo de conversión física:
    $$\text{Litros} = \frac{\text{Peso Medido} - \text{Tara}}{\rho_{\text{aceite}}}$$
    *(donde la densidad $\rho_{\text{aceite}} \approx 0.915\text{ a }0.925 \text{ kg/L}$ a temperatura operativa).*
  * Lógica de resiliencia ante pérdida de red (Requisito R-09 y riesgo RG-03): almacenamiento local de lecturas no transmitidas en la memoria Flash/EEPROM (*buffer FIFO*) y reintentos automáticos tras reanudación del enlace Wi-Fi.
* **Entregables:** Diagrama de flujo detallado del firmware, máquina de estados finitos y protocolo de tramas de datos.

### Paquete D-2.4: Diseño del Modelo Predictivo y Protocolo de Datos
* **Responsable / Aprobador:** Carlos (R) / Yamilet (Industrial) (A/R).
* **Alcance técnico:**
  * Selección de variables independientes: clientes promedio por día ($X_1$), tipo de negocio ($X_2$, variable categórica codificada con *one-hot/dummies*), número de freidoras/calderos ($X_3$) y día de la semana ($X_4$, con posibles términos de interacción tipo $\times$ día).
  * Formulación matemática: Regresión lineal múltiple con regularización (Ridge/Lasso) y evaluación de modelos lineales generalizados (GLM con enlace logarítmico o distribuciones Gamma/Poisson) para evitar predicciones físicas absurdas (flujos negativos).
  * Modelo base de referencia (*Baseline / Seasonal Naive*): promedio histórico del volumen generado en el mismo día de la semana en ese nodo.
  * Esquema de partición de datos: división puramente cronológica (no aleatoria) para simular escenarios reales de pronóstico y prevenir fuga de información temporal (*data leakage*).
  * Protocolo de recolección manual de datos: plantilla estandarizada en papel/hoja de cálculo para levantar las variables en los locales piloto durante 14 días completos.
* **Entregables:** Documento de diseño del modelo matemático, protocolo de campo de recolección y especificación de métrica objetivo:
  $$\text{MAE}_{\text{modelo}} < \text{MAE}_{\text{baseline}} \quad \text{(Requisito R-04)}$$

### Paquetes D-2.5, D-2.6 y D-2.7: Software, Seguridad y Logística de Rutas
* **D-2.5 (Base de datos y Plataforma Web):**
  * Modelo de datos relacional: tablas de `negocios`, `dispositivos`, `mediciones_peso`, `predicciones` y `rutas_recoleccion`.
  * Dashboard de control con visualización de nivel en tiempo real, histórico de llenado y estimación de días restantes para alcanzar la capacidad crítica.
  * Disparador de alerta automática cuando un recipiente supere el ~80% de su capacidad nominal (Requisito R-05).
* **D-2.6 (Seguridad de Datos - Marian A/R):**
  * Protección contra ataques y fuga de datos (Requisito R-08, ISO 27001): conexiones HTTP/HTTPS cifradas, autenticación con tokens/JWT, permisos según rol (Administrador, Recolectora, Operador de Negocio) y bitácora de auditoría.
* **D-2.7 (Modelo Logístico de Rutas - Yamilet R / Dahiana A):**
  * Regla de agrupamiento geográfico: consolidar en una misma hoja de ruta de recolección los recipientes que se encuentren en estado de alerta ($\ge 80\%$) o cuya predicción indique desborde en las siguientes 24–48 horas, minimizando distancia euclidiana/vial recorrida por el camión cisterna.

---

## 3. Matriz de Interfaces Disciplinarias

La fase de diseño requiere estricta coordinación entre las seis interfaces del proyecto SICRA:

| Interfaz | Disciplinas | Parámetro Acordado | Responsables |
| :--- | :--- | :--- | :--- |
| **Recipiente $\leftrightarrow$ Electrónica** | Civil / Electromecánica | Dimensiones de caja sellada, área de apoyo de celda, nivelación máxima ($< 2^\circ$), carga límite de rotura. | Dahiana (Civil), Carlos (Electromec.) |
| **Electrónica $\leftrightarrow$ Firmware** | Electromecánica / Software | Factor de escala analógico a digital (HX711), valor de tara, pines de interrupción GPIO, umbral de detección de reposo. | Carlos (Electromec.), Félix (Software) |
| **Firmware $\leftrightarrow$ Servidor** | Software / Ciberseguridad | Estructura JSON del paquete (`node_id`, `timestamp`, `raw_weight`, `liters`, `battery_mv`, `flags`), token de API. | Félix (Software), Marian (Ciberseg.) |
| **Datos $\leftrightarrow$ Modelo** | Software / Industrial | Normalización de variables, detección de eventos de vaciado (reducción abrupta de peso), filtrado de valores nulos. | Félix (Software), Yamilet (Industrial) |
| **Modelo $\leftrightarrow$ Logística** | Industrial | Días proyectados hasta el umbral del 80%, radio de cobertura territorial, reglas de agrupación de visitas. | Yamilet (Industrial), Dahiana (Civil) |
| **Costos $\leftrightarrow$ Diseño** | Todas las disciplinas | Techo presupuestario del prototipo unitario conforme a R-06 y costo de servidor web. | Félix, Carlos, Yamilet, Dahiana |

---

## 4. Matriz RACI de la Etapa 200

| Paquete de Trabajo | Dahiana (Civil) | Carlos (Electromec.) | Yamilet (Industrial) | Félix (Software) | Anlly (Civil) | Johalfry (Civil) | Marian (Ciberseg.) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **D-2.1 Diseño del recipiente** | **A** | C | I | I | **R** | **R** | I |
| **D-2.2 Diseño electrónico** | I | **A/R** | I | C | I | I | C |
| **D-2.3 Firmware del ESP32** | I | C | C | **A/R** | I | I | C |
| **D-2.4 Diseño modelo predictivo** | I | **R** | **A/R** | C | C | I | C |
| **D-2.5 Base de datos, script, web**| C | C | C | **A/R** | I | I | C |
| **D-2.6 Seguridad de datos** | I | C | I | C | I | I | **A/R** |
| **D-2.7 Modelo logístico de rutas** | **A** | C | **R** | C | C | I | I |
| **D-2.1 a D-2.7 Plan de pruebas** | **A** | **R** | C | C | C | C | C |

---

## 5. Criterios de Aceptación y Retornos Técnicos

* **Criterio de Presupuesto (R-06 $\rightarrow$ RT04):** Si la cotización de los componentes supera el presupuesto planificado, se revisan alternativas (por ejemplo, evaluar pantallas opcionales LCD frente a monitoreo exclusivamente web para ahorrar costos y batería).
* **Criterio de Autonomía (R-02):** La corriente consumida en reposo y en transmisión debe asegurar teóricamente $\ge 30$ días con 2 baterías 18650 antes de ordenar el ensamblaje.

---

## 6. Recursos Educativos y Lecturas Recomendadas (Further Reading)

### Electrónica de Medición y Sistemas Embebidos
* **Acondicionamiento de Celdas de Carga y Módulo HX711:**
  * *AVIA Semiconductor:* "HX711 24-Bit Analog-to-Digital Converter (ADC) for Weigh Scales Datasheet".
  * Principios del Puente de Wheatstone y amplificación diferencial en instrumentación electrónica.
* **ESP32 y Optimización de Consumo Energético:**
  * *Espressif Systems:* "ESP32 Series Datasheet & Low-Power Management Technical Reference Manual".
  * Técnicas de `esp_deep_sleep_start()`, retención en RTC Memory y calibración de ADC interno.
* **Filtrado Digital Básico para Sensores:**
  * Filtrado por mediana móvil vs media móvil para rechazo de impulsos espurios y ruido de vibración mecánica.

### Estadística y Modelado Predictivo (Guía de Estudio Bloques 0, 1 y 2)
* **Kaggle Learn (Cursos cortos prácticos interactivos):**
  * Curso *"Python"*, *"Pandas"* y *"Data Visualization"* (kaggle.com/learn).
* **StatQuest con Josh Starmer (Canal de YouTube):**
  * *"Linear Regression, Clearly Explained"*: Comprensión visual del ajuste por mínimos cuadrados ordinarios (OLS) y cálculo de coeficientes.
  * *"Ridge and Lasso Regression"*: Cómo la regularización $L_1$ y $L_2$ reduce el sobreajuste (*overfitting*).
  * *"Generalized Linear Models (GLM)"*: Comprensión de funciones de enlace (Log-link) y distribuciones Poisson/Gamma para garantizar salidas no negativas ($\hat{y} \ge 0$).
  * *"Cross Validation and Bias-Variance Tradeoff"*: Fundamentos para evaluar capacidad de generalización.
* **Libros de Texto Fundamentales:**
  * *James, G., Witten, D., Hastie, T., & Tibshirani, R.* "An Introduction to Statistical Learning with Applications in Python (ISLR)". Disponible gratuitamente en [statlearning.com](https://www.statlearning.com/). Leer especialmente:
    * *Capítulo 3:* Modelos de Regresión Lineal.
    * *Capítulo 6:* Regularización y Selección de Variables.
  * *Hyndman, R. J., & Athanasopoulos, G.* "Forecasting: Principles and Practice (3rd ed. - FPP3)". Disponible gratuitamente en [otexts.com/fpp3](https://otexts.com/fpp3/).
    * *Capítulo 5:* Métodos sencillos de referencia (*Seasonal Naive Benchmark*) y métricas de error (MAE, RMSE, MAPE).
* **Documentación Oficial de Bibliotecas Python:**
  * *Scikit-learn:* Sección `sklearn.linear_model` (LinearRegression, Ridge, Lasso) y `sklearn.model_selection.TimeSeriesSplit`.
  * *Statsmodels:* Módulo `statsmodels.api.GLM` con familias Gamma y Poisson.

### Ciberseguridad y Logística
* **ISO/IEC 27001:2022:** Estándar para controles de seguridad de la información en servicios web e infraestructura IoT.
* **OWASP IoT Top 10:** Buenas prácticas de seguridad para dispositivos de hardware embebido e interfaces de red.
* **Optimización de Rutas y Logística de Distribución:** Modelos básicos de ruteo de vehículos (Capacitated Vehicle Routing Problem - CVRP).
