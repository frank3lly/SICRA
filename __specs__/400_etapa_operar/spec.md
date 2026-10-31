# Especificación General: Etapa 400 - Operar (O-4.0)

> **Proyecto:** Sistema Inteligente para el Control y Recolección de Aceite Vegetal Usado (SICRA)  
> **Metodología:** Marco CDIO (Concebir – Diseñar – Implementar – Operar)  
> **Código de Etapa:** `400_etapa_operar`  
> **Propósito del Documento:** Guía de despliegue en campo, puesta en servicio, mantenimiento de hardware, ciclo de MLOps (reentrenamiento y vigilancia de deriva del modelo predictivo), despacho dinámico de rutas de recolección y cumplimiento ambiental bajo la Ley 225-20.

---

## 1. Visión General de la Etapa

La etapa **400 - Operar** traslada el prototipo validado al entorno operacional cotidiano en los locales comerciales seleccionados. Constituye el cierre del ciclo CDIO donde se genera el impacto ambiental y económico directo del proyecto:

1. **Puesta en Servicio e Interacción Humana:** Instalación física en el local, conexión al enlace Wi-Fi comercial y capacitación presencial al operador de la cocina para que el vertido de aceite sea intuitivo, sin herramientas y sin asistencia (Requisito R-07).
2. **Logística Dinámica y Alertas Tempranas:** Monitoreo del nivel volumétrico diario y emisión automática de alertas cuando un recipiente alcanza aproximadamente el **80% de su capacidad**, generando dinámicamente hojas de ruta agrupadas para los camiones de empresas recolectoras autorizadas (Requisito R-05).
3. **MLOps y Vigilancia Continua del Modelo:** Supervisión semanal del Error Absoluto Medio (MAE), detección de deriva de concepto (*concept drift*) por cambios estacionales en los hábitos de consumo de comida frita y reentrenamiento automatizado con datos recientes.
4. **Mantenimiento y Ciclo de Vida Responsable:** Rutinas de calibración periódica de la celda de carga, inspección de sellado hermético contra salpicaduras de grasa y disposición final controlada de baterías y electrónica en desuso según la Ley 225-20.

---

## 2. Paquetes de Trabajo de la Etapa (EDT / WBS)

```
                            ┌────────────────────────────────────────┐
                            │          O-4.0 FASE OPERAR             │
                            └───────────────────┬────────────────────┘
                                                │
         ┌──────────────────────────────────────┴──────────────────────────────────────┐
         ▼                                                                             ▼
┌─────────────────────────────────┐                                   ┌─────────────────────────────────┐
│              O-4.1              │                                   │              O-4.2              │
│ Despliegue en Campo,            │                                   │ Reentrenamiento Semanal del     │
│ Capacitación al Encargado,      │                                   │ Modelo, Mantenimiento Hardware  │
│ Alerta al 80% y Ruteo Dinámico  │                                   │ y Gestión de Residuos L. 225-20 │
└─────────────────────────────────┘                                   └─────────────────────────────────┘
```

### Paquete O-4.1: Instalación, Capacitación, Puesta en Servicio y Alertas al 80%
* **Responsable / Aprobador:** Carlos, Félix, Dahiana, Anlly (R) / Yamilet (Industrial) (A/R).
* **Alcance operacional:**
  * Fijación del recipiente inteligente en el establecimiento piloto, garantizando la distancia de seguridad recomendada ($\ge 1.5\text{ m}$ respecto a freidoras o calderos calientes, mitigación de RG-05) y la perfecta nivelación de la base de goma con el nivel de burbuja.
  * Vinculación del ESP32 a la red Wi-Fi del negocio y verificación de la primera telemetría recibida en el servidor.
  * Capacitación al personal de cocina del establecimiento: entrega de guía gráfica plastificada de uso rápido, demostración de apertura/cierre de tapa sin herramientas (R-07) y protocolo de limpieza externa.
  * Firma del Acta de Puesta en Servicio e inicio de la prueba de estabilidad en servicio ($\ge 7$ días continuos de transmisión sin fallos).
  * Monitoreo del algoritmo de disparo de alertas:
    $$\text{Si } V(t) \ge 0.80 \times V_{\text{capacidad}} \quad \longrightarrow \quad \text{Disparar evento de alerta en plataforma web}$$
  * Agrupación automática de negocios en el módulo de rutas para el despacho del camión recolector antes de que ocurra cualquier desborde (mitigación de riesgo RG-08).
* **Entregables:** Acta formal de instalación, guía de uso para el encargado del negocio y panel web operativo emitiendo alertas al 80% de volumen.
* **Criterio de Aceptación:** $\ge 7$ días de operación continua verificada; generación comprobada de ruta cuando el nivel alcanza el 80% (R-05).

### Paquete O-4.2: Reentrenamiento Semanal, Mantenimiento y Gestión de Residuos
* **Responsable / Aprobador:** 
  * *MLOps / Software:* Yamilet (R) / Félix (Software) (A/R).
  * *Hardware y Residuos:* Dahiana, Johalfry (R) / Carlos (Electromecánica) (A/R).
* **Alcance operacional:**
  * **Ciclo Semanal de MLOps:**
    * Extracción semanal de los nuevos registros reales transmitidos por los nodos IoT.
    * Ejecución automática o programada del script de reentrenamiento.
    * Registro en bitácora del MAE obtenido durante la semana frente al modelo de referencia (*seasonal naive*).
    * Si durante 2 semanas consecutivas el error del modelo supera al de referencia, se activa el retorno correctivo **RT06**.
  * **Plan de Mantenimiento Preventivo y Metrológico:**
    * Inspección mensual de la celda de carga con pesas patrón: recalibración si el error supera $\pm 0.5\text{ kg}$.
    * Comprobación del estado de carga y salud de las baterías recargables 18650.
    * Inspección visual de la caja plástica IP65 contra ingreso de polvo, vapores grasos o insectos.
  * **Gestión Ambiental de Residuos de Fin de Vida (Ley 225-20):**
    * Plan de disposición final segura para celdas de litio degradadas y componentes electrónicos desincorporados (RAEE), canalizándolos a través de los programas oficiales de recolección de residuos peligrosos.
    * Certificación de entrega del aceite vegetal usado acumulado exclusivamente a empresas recicladoras autorizadas (Reoil Dominicana, Mevosa) para su aprovechamiento en biodiésel o lubricantes industriales (Requisito R-10).
* **Entregables:** Bitácora semanal de errores de pronóstico, calendario de mantenimiento preventivo y manifiestos de trazabilidad de entrega de residuos.
* **Criterio de Aceptación:** 100% de las semanas evaluadas con reporte de error; calibración dentro de $\pm 0.5\text{ kg}$; cero vertidos ilegales al drenaje público.

---

## 3. Matriz RACI de la Etapa 400

| Paquete de Trabajo | Dahiana (Civil) | Carlos (Electromec.) | Yamilet (Industrial) | Félix (Software) | Anlly (Civil) | Johalfry (Civil) | Marian (Ciberseg.) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **O-4.1 Instalación, capacitación y rutas** | **R** | **R** | **A/R** | **R** | **R** | C | C |
| **O-4.2 (MLOps) Reentrenamiento semanal** | I | C | **R** | **A/R** | I | I | C |
| **O-4.2 (HW) Mantenimiento y residuos** | **R** | **A/R** | C | I | I | **R** | I |

---

## 4. Retornos Técnicos (Feedback Loops) Originados en Operación

La etapa de operación retroalimenta a las etapas de diseño e implementación si se detectan anomalías durante el servicio real:

1. **Retorno RT05 (Operar O-4.2 $\rightarrow$ Diseñar D-2.3):**
   * *Disparador:* Pérdida de paquetes de telemetría $> 5\%$ debido a caídas prolongadas de la red Wi-Fi del establecimiento.
   * *Acción:* Regresar al diseño del firmware del ESP32 para ampliar el tamaño de la memoria Flash asignada al búfer local no volátil y ajustar los intervalos de reintento exponencial.
   * *Aprobador de retorno:* Félix (Software).
2. **Retorno RT06 (Operar O-4.2 $\rightarrow$ Implementar I-3.3):**
   * *Disparador:* El modelo predictivo presenta un desempeño deficiente frente al modelo base de referencia durante 2 semanas consecutivas ($\text{MAE}_{\text{modelo}} \ge \text{MAE}_{\text{ref}}$ en 2 semanas seguidas).
   * *Acción:* Retornar a la fase de implementación para ejecutar un reentrenamiento extraordinario, actualizar las variables de estacionalidad con los datos frescos y reajustar los hiperparámetros del estimador.
   * *Aprobador de retorno:* Félix (Software).

---

## 5. Protocolo de Contingencia Operacional (Matriz de Riesgos)

Ante situaciones imprevistas en los locales, se aplican los siguientes protocolos derivados del registro de riesgos:

* **Falla de conectividad Wi-Fi prolongada (RG-03):** Se realiza verificación física del nivel del bidón mediante escala graduada o pesaje manual y se coordina la recolección vía telefónica de respaldo mientras se restablece el servicio.
* **Incumplimiento de horario de llegada de la empresa recolectora (RG-08):** Para evitar desbordes accidentales si la capacidad supera el 85%, el sistema dispara alerta prioritaria al encargado y activa el uso de un bidón de reserva temporal en el local.
* **Falla o caída del script de procesamiento en el servidor (RG-09):** La interfaz web muestra visiblemente la última fecha/hora de cálculo y se activa el modo de cálculo manual de contingencia basado en el promedio histórico del nodo hasta reiniciar el servicio.

---

## 6. Recursos Educativos y Lecturas Recomendadas (Further Reading)

### MLOps, Mantenimiento de Modelos y Detección de Deriva
* **MLOps en Producción y Deriva de Concepto (*Concept & Data Drift*):**
  * *Chip Huyen:* "Designing Machine Learning Systems" (O'Reilly). Capítulo 9: *Continual Learning and Test in Production*, y Capítulo 10: *Infrastructure and Tooling for MLOps*.
  * Conceptos clave: Monitoreo de degradación de métricas de regresión (MAE, MSE) a lo largo del tiempo ante cambios de estacionalidad (ej. días festivos, vacaciones universitarias).
* **Pipelines Automatizados de Reentrenamiento:**
  * Uso de tareas programadas tipo Cron y orquestadores ligeros en Python para reajuste periódico de coeficientes de regresión.

### Logística de Transporte Inversa y Optimización Dinámica de Rutas
* **Logística Inversa para Economía Circular:**
  * *Rogers, D. S., & Tibben-Lembke, R. S.* "Going Backwards: Reverse Logistics Trends and Practices". Reverse Logistics Executive Council.
  * Modelado de recolección de aceites de cocina usados (UCO) para cadenas de suministro de biocombustibles (biodiésel HVO/FAME).
* **Motores de Ruteo y Optimización Espacial:**
  * *Google OR-Tools:* Documentación del problema de ruteo de vehículos (*Vehicle Routing Problem - VRP* con ventanas de tiempo y capacidades).
  * Servicios de cartografía y cálculo de matrices de distancia: OpenStreetMap / OSRM (Open Source Routing Machine).

### Gestión de Residuos Peligrosos y RAEE
* **Ley 225-20 y Reglamentación Dominicana de Residuos:**
  * Manual de manejo y disposición de Residuos de Aparatos Eléctricos y Electrónicos (RAEE) y acumuladores de energía portátiles (baterías de Li-ion).
  * Directivas internacionales sobre reciclaje seguro de aceites minerales y vegetales usados.
