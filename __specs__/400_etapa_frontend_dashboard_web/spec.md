# Especificación General: Etapa 400 - Plataforma Web Frontend y Dashboard Operativo

> **Proyecto:** Sistema Inteligente para el Control y Recolección de Aceite Vegetal Usado (SICRA)  
> **Área:** Frontend Web, Visualización Geoespacial, UX Logística y Dashboard Analítico  
> **Código de Etapa:** `400_etapa_frontend_dashboard_web`  
> **Propósito:** Guía de diseño e implementación de la interfaz de usuario web, mapa de monitoreo de contenedores, panel de despacho dinámico de rutas, portal del establecimiento comercial y monitor de desempeño del modelo predictivo.

---

## 1. Visión General de la Etapa

Esta etapa materializa la capa de presentación e interacción con el usuario final de SICRA. La plataforma web traduce datos matemáticos y lecturas de telemetría en paneles visuales intuitivos, accesibles desde navegadores de escritorio y dispositivos móviles.

La aplicación frontend satisface tres casos de uso esenciales:

1. **Operación Logística (Empresa Recolectora - Reoil / Mevosa):** Monitoreo global de la flota de bidones inteligentes, gestión inmediata de **alertas al 80% de llenado** y visualización cartográfica de la ruta de recogida sugerida para optimizar tiempos y combustible.
2. **Autocontrol y Concientización (Dueño / Encargado del Negocio):** Visualización clara del nivel de llenado de su contenedor sin necesidad de abrir la tapa, fecha estimada para el próximo retiro y cálculo del impacto ambiental evitado.
3. **Supervisión de Ingeniería (MLOps y Auditoría):** Monitoreo en tiempo real del error del modelo predictivo (MAE) frente al modelo de referencia (*seasonal naive*), garantizando el cumplimiento continuo del requisito **R-04**.

---

## 2. Arquitectura de Vistas de la Plataforma Web

```
┌────────────────────────────────────────────────────────────────────────┐
│                      PLATAFORMA WEB SICRA                              │
├──────────────────────────────────┬─────────────────────────────────────┤
│  VISTA 1: LOGÍSTICA RECOLECTORA  │  VISTA 2: ENCARGADO DEL NEGOCIO     │
│  - Mapa interactivo con pines    │  - Indicador circular de nivel (%)  │
│  - Código de colores (verde/rojo)│  - Horas estimadas para llenado     │
│  - Alertas prioritarias (>= 80%) │  - Litros de agua preservados       │
│  - Hoja de ruta dinámica         │  - Histórico de recogidas           │
├──────────────────────────────────┴─────────────────────────────────────┤
│  VISTA 3: AUDITORÍA ANALÍTICA Y ML (INGENIERÍA)                        │
│  - Gráfico comparativo: Volumen Real vs. Predicho                      │
│  - Tarjeta de métrica: MAE Modelo vs. MAE Referencia (R-04)            │
│  - Selector de datos: Registros Sintéticos vs. Registros Reales        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Especificación de Componentes de la Interfaz

### 3.1. Dashboard de la Recolectora (Mapa y Rutas Dinámicas)

* **Mapa Cartográfico Interactivo (Leaflet / Mapbox):**
  * Marcadores geoespaciales para cada contenedor inteligente activo en la red piloto.
  * **Semáforo Visual de Llenado:**
    * 🟢 **Verde:** Nivel normal ($< 50\%$).
    * 🟡 **Amarillo:** Nivel medio ($50\% - 79\%$).
    * 🔴 **Rojo Parpadeante:** Alerta crítica de recolección ($\ge 80\%$ o desborde proyectado en $< 24$ horas).
  * **Tarjeta Flotante al Clicar un Nodo:** Nombre del local, tipo de negocio, volumen actual en litros, porcentaje, nivel de batería del dispositivo IoT y última hora de sincronización.
* **Módulo de Hoja de Ruta Sugerida:**
  * Trazo interactivo (*polyline*) sobre el mapa que une las paradas óptimas calculadas por el backend.
  * Tabla lateral con la secuencia de paradas:
    * Número de orden ($1, 2, \dots, N$).
    * Dirección y nombre del negocio.
    * Volumen estimado a recolectar.
    * Botón de acción: *"Confirmar Recogida"* (que dispara el evento de reseteo de tara).
  * Barra de resumen operativo: total de paradas, litros totales acumulados en la ruta y kilómetros calculados.

---

### 3.2. Portal del Encargado del Negocio Gastronómico

* **Diseño Ultra-Simplificado (Mobile-First):**
  * El encargado de cocina necesita una vista rápida y directa sin complicaciones técnicas.
  * **Widget Principal:** Calibrador circular grande (*circular progress gauge*) que indica el porcentaje de llenado actual ($0\%$ a $100\%$) y los litros disponibles.
  * **Mensaje de Estado en Lenguaje Claro:**
    * *"Tu recipiente tiene espacio de sobra."*
    * *"Recipiente casi lleno: el camión recolector ha sido notificado para visitarte."*
  * **Métricas de Impacto Ambiental Positivo:**
    * Contador acumulado de aceite reciclado legalmente (Ley 225-20).
    * Equivalencia ambiental: *"Has evitado la contaminación de $X$ mil litros de agua"* (calculado en base a la relación $1\text{L aceite} \implies 1,000\text{L agua potable}$).

---

### 3.3. Panel Analítico y Monitor de Modelos Predictivos

* **Comparación de Rendimiento de ML:**
  * Gráfica de series temporales (Chart.js / Plotly / Recharts) superponiendo:
    * Curva de vertido real diario ($y$).
    * Curva proyectada por la regresión GLM / Random Forest ($\hat{y}_{\text{modelo}}$).
    * Curva proyectada por el modelo de referencia estacional ($\hat{y}_{\text{ref}}$).
* **Métricas Clave de Trazabilidad:**
  * Tarjetas de MAE en litros/día: $\text{MAE}_{\text{modelo}}$ vs. $\text{MAE}_{\text{referencia}}$.
  * Indicador de estatus de la **Regla de Oro (R-04):**
    * 🟢 **SUPERADO:** El modelo predictivo reduce el error respecto al promedio estacional.
    * ⚠️ **FALLBACK:** El sistema está usando el modelo base mientras se recalibra el modelo principal.
  * Filtro de visualización: alternar entre datos reales y datos sintéticos procedentes de la simulación Monte Carlo.

---

## 4. Criterios de Aceptación de la Etapa

1. **Diseño Responsivo:** Compatibilidad 100% en pantallas móviles (smartphones de choferes y cocineros) y escritorios (central de despacho).
2. **Actualización Dinámica:** Refresco de alertas y estados en tiempo real (mediante polling o WebSockets/SSE) en menos de 2 segundos tras la ingesta de telemetría en el backend.
3. **Claridad Operativa:** El despachador debe poder visualizar la lista de negocios que superan el 80% y generar la hoja de ruta en un máximo de dos clics.

---

## 5. Recursos Educativos y Lecturas Recomendadas (Further Reading)

### Desarrollo Web Frontend Moderno y Dashboards
* **Frameworks Reactivos y UI:**
  * Documentación de React / Next.js / Vue.js.
  * Componentes de diseño accesibles: Tailwind CSS, Shadcn UI / Material UI.
* **Visualización de Datos y Gráficos:**
  * Chart.js y Recharts para series de tiempo, barras de dispersión y medidores radiales.

### Cartografía Digital y GIS para Logística
* **Librerías de Mapas Web:**
  * *Leaflet.js:* Guía oficial para marcadores personalizados, capas GeoJSON y polilíneas.
  * *Mapbox GL JS:* Renderizado vectorial de alta resolución y estilización de rutas vehiculares.

### Experiencia de Usuario (UX) en Logística y Sostenibilidad
* **Diseño de Interfaces para Operaciones de Campo:**
  * Principios de diseño para conductores y operarios de planta: alto contraste, botones de gran tamaño táctil y mínima fricción cognitiva.
* **Gamificación y Concientización Ambiental:**
  * Técnicas visuales para comunicar el ahorro de huella hídrica y cumplimiento de normativas de reciclaje (Ley 225-20).
