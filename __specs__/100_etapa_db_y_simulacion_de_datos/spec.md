# Especificación General: Etapa 100 - Base de Datos, Persistencia y Simulación de Datos

> **Proyecto:** Sistema Inteligente para el Control y Recolección de Aceite Vegetal Usado (SICRA)  
> **Área:** Arquitectura de Software, Almacenamiento y Generación Sintética  
> **Código de Etapa:** `100_etapa_db_y_simulacion_de_datos`  
> **Propósito:** Servir como guía conceptual y técnica para el diseño del modelo de datos relacional y el subsistema de simulación estadística de telemetría y vertido de aceite (Monte Carlo).

---

## 1. Visión General de la Etapa

Esta etapa constituye la base de datos y la fuente primaria de información para todo el ecosistema de software de SICRA (Backend, Motor Predictivo y Frontend). Dado que el desarrollo del software se realiza en paralelo al despliegue del hardware IoT, es indispensable desacoplar el software del mundo físico mediante dos pilares fundamentales:

1. **Diseño del Esquema de Datos:** Modelado robusto de entidades que representen los negocios generadores de aceite, los contenedores inteligentes, los eventos de telemetría, las predicciones volumétricas, las alertas y la logística de rutas.
2. **Generador de Datos Sintéticos (Simulación Monte Carlo):** Un motor probabilístico en Python capaz de simular desde 20,000 hasta 100,000 registros de telemetría y vertido diario basados en perfiles estadísticos reales de establecimientos de comida frita (frituras, cafeterías y pica-pollos), permitiendo alimentar y poner a prueba los modelos predictivos y la plataforma web sin depender del hardware físico.

---

## 2. Alcance y Componentes del Software

```
┌────────────────────────────────────────────────────────────────────────┐
│             ETAPA 100: CAPA DE PERSISTENCIA Y SIMULACIÓN               │
├──────────────────────────────────┬─────────────────────────────────────┤
│  1. MODELO DE DATOS RELACIONAL   │  2. SIMULADOR MONTE CARLO (PYTHON)  │
│  - Negocios y Establecimientos   │  - Modelado de distribución Gamma   │
│  - Recipientes / Nodos IoT       │  - Variación por día de la semana   │
│  - Telemetría (peso, litros)     │  - Detección de vaciados/recogidas  │
│  - Predicciones y Alertas        │  - Flag obligatorio: 'es_sintetico' │
│  - Rutas de Recolección          │  - Semilla fija (Reproducibilidad)  │
└──────────────────────────────────┴─────────────────────────────────────┘
```

### 2.1. Esquema de Entidades (Base de Datos)

El modelo de datos debe soportar las siguientes entidades nucleares:

* **`negocios`**:
  * `id`: Identificador único (UUID / Int).
  * `nombre`: Nombre del establecimiento (ej. "Pica Pollo Expreso", "Fritura El Primo").
  * `tipo_negocio`: Clasificación categórica (`fritura`, `cafeteria`, `pica_pollo`, `restaurante`).
  * `num_freidoras_calderos`: Cantidad de freidoras o calderos activos.
  * `clientes_promedio_dia`: Afluencia promedio estimada.
  * `ubicacion_lat`, `ubicacion_lon`: Coordenadas geográficas para ruteo logístico.
  * `direccion`: Dirección física de referencia en el entorno piloto.
* **`recipientes`**:
  * `id`: Identificador único del nodo.
  * `negocio_id`: Relación foránea con el negocio propietario.
  * `capacidad_max_litros`: Capacidad nominal del bidón de PEAD (ej. 20L, 50L, 100L).
  * `peso_tara_kg`: Peso del contenedor vacío.
  * `densidad_aceite`: Factor de conversión físico (valor típico: $0.92\text{ kg/L}$).
  * `token_autenticacion`: Clave segura de autorización para ingesta desde el hardware.
* **`telemetrias`**:
  * `id`: Clave primaria del evento.
  * `recipiente_id`: ID del recipiente emisor.
  * `peso_crudo_kg`: Peso bruto registrado por la balanza.
  * `litros_calculados`: Volumen calculado mediante $\text{Litros} = (\text{peso} - \text{tara}) / \rho$.
  * `porcentaje_llenado`: Relación respecto a la capacidad máxima.
  * `bateria_mv`: Nivel de voltaje o porcentaje de batería del dispositivo IoT.
  * `timestamp_medicion`: Fecha y hora en la que se generó la medición en el nodo.
  * `recibido_en`: Fecha y hora de recepción en el servidor.
  * `es_sintetico`: Booleano (`true`/`false`) que diferencia mediciones simuladas de telemetría física real.
* **`predicciones`**:
  * `id`: Clave primaria.
  * `recipiente_id`: Nodo evaluado.
  * `fecha_calculo`: Momento de ejecución del script predictivo.
  * `fecha_proyeccion`: Día proyectado.
  * `litros_estimados_dia`: Volumen que se espera que el negocio genere ese día.
  * `horas_hasta_80_porciento`: Tiempo estimado hasta alcanzar el umbral crítico de recogida.
  * `modelo_usado`: Identificador de la técnica (`regresion_glm`, `ridge`, `random_forest`, `seasonal_naive`).
  * `mae_historico`: Error absoluto medio registrado por el modelo para trazabilidad.
* **`alertas`**:
  * `id`: Clave primaria.
  * `recipiente_id`: Recipiente que disparó el evento.
  * `tipo`: `LLENADO_80`, `LLENADO_CRITICO_95`, `BATERIA_BAJA`, `INACTIVIDAD`.
  * `nivel_alcanzado`: Porcentaje de llenado al momento del aviso.
  * `atendida`: Booleano que indica si la recolectora ya programó o ejecutó el retiro.
* **`rutas_recoleccion`**:
  * `id`: Identificador de la hoja de ruta.
  * `fecha_generacion`: Día y hora de creación de la ruta.
  * `estado`: `SUGERIDA`, `EN_CURSO`, `COMPLETADA`.
  * `paradas_ordenadas_json`: Secuencia ordenada de paradas con IDs de negocios, coordenadas y litros previstos a recoger.

---

### 2.2. Motor de Simulación Monte Carlo de Datos (Bloque 3 de la Guía)

El simulador en Python debe recrear el comportamiento operativo de los negocios gastronómicos utilizando distribuciones probabilísticas realistas:

1. **Parámetros de Simulación por Perfil de Negocio:**
   * **Frituras:** Mayor intensidad de desecho por fritura rápida intensiva (distribución Gamma con mayor sesgo en fines de semana).
   * **Pica-Pollos:** Alto volumen diario constante, fuertemente acoplado al número de freidoras comerciales.
   * **Cafeterías:** Desecho menor y más disperso durante días laborales.
2. **Generación de Ruido y Comportamientos Físicos:**
   * **Efecto de Día de la Semana:** Multiplicadores estacionales (viernes a domingo presentan típicamente de $1.5\times$ a $2.2\times$ la generación de lunes a miércoles).
   * **Eventos de Vaciado:** Simulación de caídas abruptas de peso (cuando el recolector retira el aceite acumulado y reinicia el recipiente a su tara).
   * **Ruido de Medición y Outliers:** Incorporación de leves fluctuaciones gaussianas en la lectura de peso ($\pm 0.05\text{ kg}$) para emular la vibración ambiental.
3. **Reproducibilidad y Etiquetado:**
   * Uso obligatorio de generador con semilla reproducible (`numpy.random.default_rng(seed=42)`).
   * Cada registro generado debe llevar irrevocablemente la marca `es_sintetico = True`.

---

## 3. Criterios de Aceptación de la Etapa

1. **Integridad Referencial:** Esquema relacional con claves primarias, foráneas e índices apropiados en `timestamp_medicion` y `recipiente_id`.
2. **Capacidad de Carga:** El generador sintético debe generar un dataset de al menos 20,000 registros completos en formato CSV / SQL en menos de 5 segundos.
3. **Consistencia Física:** Los datos simulados nunca deben generar volúmenes negativos ni exceder la capacidad geométrica del bidón asignado sin registrar un vaciado.

---

## 4. Recursos Educativos y Lecturas Recomendadas (Further Reading)

### Modelado de Bases de Datos y ORMs en Python
* **SQLAlchemy & SQLModel Documentation:**
  * Diseño de esquemas declarativos en Python y manejo eficiente de migraciones con Alembic.
  * Índices para series temporales y consultas de telemetría IoT.
* **Diseño Relacional en PostgreSQL / SQLite:**
  * Técnicas de normalización (3FN) y optimización para series de tiempo (*time-series tables*).

### Simulación Monte Carlo y Generación de Datos Sintéticos (Guía de Estudio Bloque 3)
* **Documentación Oficial de NumPy:**
  * `numpy.random.Generator`: Uso de distribuciones `gamma()`, `poisson()` y `normal()` para simulación de fenómenos continuos y discretos.
* **Conceptos de Sim-to-Real y Datos Sintéticos:**
  * *YouTube Tutorials:* "Monte Carlo Simulation in Python" y "Generating Synthetic Datasets for Machine Learning Testing".
  * *StatQuest:* "Probabilistic Distributions (Poisson, Normal, Gamma) Explained".
  * Buenas prácticas: Documentación explícita de supuestos probabilísticos y matrices de correlación simuladas.
