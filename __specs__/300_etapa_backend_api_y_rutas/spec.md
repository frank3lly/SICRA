# Especificación General: Etapa 300 - Servidor Backend, Ingesta IoT y Ruteo Dinámico

> **Proyecto:** Sistema Inteligente para el Control y Recolección de Aceite Vegetal Usado (SICRA)  
> **Área:** Backend, APIs REST, Ingesta de Telemetría y Optimización Logística  
> **Código de Etapa:** `300_etapa_backend_api_y_rutas`  
> **Propósito:** Guía de desarrollo del servidor backend, contratos de comunicación para telemetría IoT, servicios de detección de vaciados, motor de alertas al 80% y algoritmos de optimización de rutas de recolección.

---

## 1. Visión General de la Etapa

Esta etapa materializa la capa de servicios central del ecosistema SICRA. El backend actúa como el núcleo de procesamiento que:

1. Expone interfaces seguras para recibir la telemetría enviada por los recipientes IoT (garantizando resiliencia ante cortes de red mediante procesamiento de lotes diferidos).
2. Orquesta la ejecución del motor predictivo desarrollado en la Etapa 200.
3. Monitorea continuamente los niveles de llenado y detona automáticamente las **alertas al 80% de capacidad** (Requisito R-05).
4. Resuelve el problema logístico de recolección agrupando los recipientes críticos en **hojas de ruta optimizadas** para los camiones de las empresas recolectoras autorizadas.
5. Gestiona la autenticación, autorización basada en roles (RBAC) y la integridad de los datos según las pautas de ISO 27001 (Requisito R-08).

---

## 2. Arquitectura de Servicios del Backend

```
┌────────────────────────────────────────────────────────────────────────┐
│                        SICRA BACKEND (FASTAPI)                         │
├────────────────────────────────────────────────────────────────────────┤
│  [1. Contrato de Ingesta IoT]  ──►  [Detección de Vaciados y Litros]   │
│  [2. Invocación de ML]         ──►  [Proyección de Horas hasta 80%]    │
│  [3. Motor de Alertas]         ──►  [Disparo automático a 80%]        │
│  [4. Algoritmo de Rutas]       ──►  [Enrutamiento Óptimo TSP/VRP]      │
│  [5. Control de Acceso RBAC]   ──►  [Admin / Recolectora / Negocio]    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Especificación de Componentes

### 3.1. Contrato de Ingesta de Telemetría IoT (`POST /api/v1/telemetry/ingest`)

Aunque el código de los microcontroladores se desarrolla externamente, el servidor define el contrato estricto de comunicación que debe cumplir el hardware:

* **Soporte de Lotes Desconectados (Requisito R-09):**  
  El endpoint debe aceptar tanto mediciones individuales en tiempo real como arreglos (*arrays*) de mediciones acumuladas durante interrupciones del enlace Wi-Fi.
* **Estructura del Payload (JSON):**
  ```json
  {
    "device_token": "sec_tok_xyz123",
    "readings": [
      {
        "timestamp": "2026-10-31T14:30:00Z",
        "raw_weight_kg": 18.45,
        "battery_mv": 3950,
        "is_synthetic": false
      }
    ]
  }
  ```
* **Lógica de Procesamiento del Backend:**
  1. Validación del token del dispositivo contra la tabla `recipientes`.
  2. Cálculo volumétrico en servidor utilizando los parámetros calibrados del recipiente:
     $$\text{litros} = \frac{\text{raw\_weight\_kg} - \text{tara\_kg}}{\rho_{\text{aceite}}}$$
     $$\text{porcentaje\_llenado} = \left(\frac{\text{litros}}{\text{capacidad\_max\_litros}}\right) \times 100$$
  3. **Algoritmo de Detección de Vaciado:**  
     Si la lectura actual presenta una reducción abrupta de peso ($\Delta \text{peso} < -0.40 \cdot \text{capacidad}$), el sistema registra un evento de recogida/vaciado, restablece el contador de ciclo y notifica la confirmación de retiro.

---

### 3.2. Servicio de Predicción y Motor de Alertas al 80% (Requisito R-05)

* **Servicio Periódico de Pronóstico (Worker / Cron):**
  * Invoca periódicamente los modelos entrenados (Etapa 200) para cada nodo activo.
  * Calcula la tasa de llenado proyectada ($\text{litros/día}$) y estima el tiempo restante:
    $$\Delta t_{80\%} = \frac{0.80 \cdot V_{\text{capacidad}} - V_{\text{actual}}}{r_{\text{diaria}}}$$
* **Regla de Alerta Inmediata:**
  * Si $\text{porcentaje\_llenado} \ge 80\%$ o si $\Delta t_{80\%} \le 24\text{ horas}$, se genera una alerta con prioridad `ALTA` en la base de datos y se incluye el nodo como parada obligatoria en la cola de recolección logística.

---

### 3.3. Motor de Optimización de Rutas de Recolección

* **Entrada del Algoritmo:** Conjunto de ubicaciones geográficas de recipientes con alerta activa ($\ge 80\%$) más punto de partida del vehículo de recolección (depósito de Reoil / Mevosa).
* **Función Objetivo:** Minimizar la distancia total euclidiana / vial recorrida:
  $$\min \sum_{i=1}^{m} \text{distancia}(P_i, P_{i+1})$$
* **Método Heurístico de Resolución:**
  * Algoritmo del Vecino Más Cercano (*Nearest Neighbor*) con refinamiento local 2-opt, adecuado para flotas urbanas pequeñas y medianas (5 a 50 puntos de acopio).
  * Retorno de la ruta estructurada con paradas numeradas, coordenadas geográficas, litros estimados a retirar y distancia acumulada.

---

### 3.4. Seguridad, Autenticación y RBAC (ISO 27001 / Requisito R-08)

* **Protocolo de Comunicación:** Cifrado en tránsito vía TLS/HTTPS en todos los endpoints.
* **Autenticación:** Tokens JWT (JSON Web Tokens) con firma criptográfica asimétrica o clave secreta robusta.
* **Roles de Usuario (RBAC):**
  * **`ADMIN`:** Gestión total de usuarios, comercios, dispositivos y reentrenamiento de modelos.
  * **`RECOLECTORA`:** Acceso a la visualización de rutas del día, mapas de contenedores en alerta y registro de recolecciones realizadas.
  * **`NEGOCIO`:** Acceso restringido exclusivamente a las métricas de su propio local (nivel actual, fecha estimada de llenado y registro de recolecciones). Sin acceso a datos de competidores ni registros de clientes (principio de minimización de datos).

---

## 4. Criterios de Aceptación de la Etapa

1. **Rendimiento de Ingesta:** Capacidad de procesar lotes de hasta 500 telemetrías por segundo con tiempo de respuesta $\le 100\text{ ms}$.
2. **Disparo Confiable de Alertas:** Toda telemetría que supere el umbral del 80% debe generar su respectivo registro de alerta en menos de 1 segundo.
3. **Cálculo de Ruta Dinámica:** Para cualquier grupo de nodos en alerta, el motor de rutas debe devolver una secuencia ordenada válida sin ciclos en menos de 200 ms.

---

## 5. Recursos Educativos y Lecturas Recomendadas (Further Reading)

### Desarrollo de APIs Modernas y Asincronía en Python
* **Documentación Oficial de FastAPI:**
  * Conceptos de `async / await`, inyección de dependencias (`Depends`), y validación con Pydantic V2.
  * Generación automática de especificaciones OpenAPI y Swagger UI.
* **Manejo de Tareas en Segundo Plano:**
  * *FastAPI BackgroundTasks* y planificadores asíncronos (*APScheduler* / *Celery* con Redis).

### Algoritmos de Ruteo y Optimización Logística
* **Problema del Viajante de Comercio (TSP) y Ruteo de Vehículos (VRP):**
  * *Google OR-Tools for Python:* Guía del "Vehicle Routing Problem" ([developers.google.com/optimization/routing](https://developers.google.com/optimization/routing)).
  * Heurística 2-opt para optimización de trayectorias en grafos urbanos.
* **Cálculo de Matrices Geoespaciales:**
  * Fórmulas de Haversine para distancias geodésicas y consumo de APIs de OpenStreetMap (OSRM).

### Ciberseguridad en APIs y Control de Acceso
* **OWASP API Security Top 10:**
  * Prevención de Broken Object Level Authorization (BOLA) y Broken Function Level Authorization.
* **Estándar ISO/IEC 27001:**
  * Controles de seguridad para aplicaciones web y gestión de identidades con tokens temporales de expiración corta.
