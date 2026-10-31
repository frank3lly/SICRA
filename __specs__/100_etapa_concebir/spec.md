# Especificación General: Etapa 100 - Concebir (C-1.0)

> **Proyecto:** Sistema Inteligente para el Control y Recolección de Aceite Vegetal Usado (SICRA)  
> **Metodología:** Marco CDIO (Concebir – Diseñar – Implementar – Operar)  
> **Código de Etapa:** `100_etapa_concebir`  
> **Propósito del Documento:** Guía conceptual, metodológica y operativa para entender la fase de concepción del proyecto SICRA, sus requisitos, paquetes de trabajo, criterios de aceptación y recursos de aprendizaje para los miembros del equipo.

---

## 1. Visión General de la Etapa

La etapa **100 - Concebir** constituye la base estratégica, regulatoria y arquitectónica del proyecto SICRA. Su propósito central es identificar la problemática del vertido inadecuado de aceite de cocina usado (ACU) en establecimientos comerciales dominicanos (frituras, cafeterías y pica-pollos), delimitar la demanda real, formalizar los requisitos de ingeniería y evaluar las alternativas técnicas y logísticas para formular la arquitectura de la solución preliminar.

En esta fase se establecen las reglas de juego del proyecto, asegurando que cada decisión técnica (desde la elección del Polietileno de Alta Densidad - PEAD hasta el esquema predictivo) responda directamente a necesidades reales, restricciones presupuestarias y al marco legal dominicano vigente.

---

## 2. Paquetes de Trabajo de la Etapa (EDT / WBS)

```
                    ┌───────────────────────────────────────┐
                    │          C-1.0 FASE CONCEBIR          │
                    └──────────────────┬────────────────────┘
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         ▼                             ▼                             ▼
┌───────────────────┐        ┌───────────────────┐        ┌───────────────────┐
│ C-1.1 Delimitación│        │ C-1.2 Requisitos  │        │ C-1.3 Concepto y  │
│  y Negocios       │        │  Normativa y      │        │   Arquitectura    │
│  Candidatos       │        │  Alternativas     │        │   Preliminar      │
└───────────────────┘        └───────────────────┘        └───────────────────┘
```

### Paquete C-1.1: Delimitación de Litros/Día y Fuentes de Demanda
* **Descripción:** Identificación, visita técnica y caracterización de los negocios candidatos en el entorno de la Universidad Central del Este (UCE) y zonas aledañas.
* **Entradas:** Censo exploratorio preliminar, ubicación geográfica de comercios de fritura y comida rápida.
* **Actividades clave:**
  1. Visitas de campo y entrevistas a dueños y encargados de locales piloto.
  2. Levantamiento de variables operativas: número de calderos/freidoras, volumen promedio estimado, clientes promedio diarios y tipo de establecimiento.
  3. Verificación de condiciones de instalación (conectividad Wi-Fi disponible, espacio físico nivelado, distancia segura a fuentes de fuego, accesibilidad para el personal de recolección).
* **Entregables:** Ficha técnica de delimitación y lista oficial de ~5 negocios seleccionados y aceptados.
* **Criterio de Aceptación:** Al menos 5 negocios formales/informales que cumplan 100% de los criterios mínimos de viabilidad física y conectividad.

### Paquete C-1.2: Formulación de Requisitos, Normativa y Evaluación de Alternativas
* **Descripción:** Redacción y validación de los 10 requisitos técnicos y operacionales esenciales (R-01 a R-10), contextualizados en las leyes ambientales dominicanas y matrices de decisión de ingeniería.
* **Entradas:** Contexto ambiental de RD (95% de residuos en vertederos, daño hídrico de 1L aceite : 1,000L agua), requerimientos de empresas recolectoras (Reoil, Mevosa).
* **Actividades clave:**
  1. Formalización de la tabla de requisitos medibles, criterios de aceptación cuantitativos y métodos de verificación (R-01 a R-10).
  2. Evaluación comparativa de materiales para el contenedor:
     * *Acero Inoxidable:* Excelente higiene, alta resistencia estructural; descartado por costo elevado y peso propio excesivo.
     * *Polietileno de Alta Densidad (PEAD):* Seleccionado por bajo costo, excelente compatibilidad química con grasas, baja conductividad térmica y durabilidad mecánica.
  3. Evaluación comparativa del esquema de recolección logística:
     * *Horario/Frecuencia fija:* Descartado (provoca viajes innecesarios y vacíos).
     * *Aviso manual por parte del negocio:* Descartado (genera despachos reactivos, desordenados y aislados).
     * *Sistema predictivo y alerta al 80% (SICRA):* Seleccionado (permite enrutamiento dinámico y anticipación de desbordes).
  4. Mapeo normativo: Ley 225-20 (Gestión de Residuos), Ley 64-00 (Medio Ambiente), Ley 42-01 (Salud Pública, art. 51), normas ISO 14001 e ISO 27001.
* **Entregables:** Tabla consolidada de requisitos R-01 a R-10 y Matriz de decisión técnica formalizada por escrito.
* **Criterio de Aceptación:** 10 requisitos cerrados sin ambigüedades con método de verificación asignado; alternativas justificadas cuantitativamente.

### Paquete C-1.3: Concepto, Alcance y Arquitectura Preliminar del Sistema
* **Descripción:** Diseño arquitectónico de alto nivel integrando subsistema físico/sensor (celda de carga + HX711 + ESP32), subsistema de backend/modelo (Python, base de datos) y subsistema web de visualización logística.
* **Entradas:** Requisitos funcionales y matriz de decisión aprobada.
* **Actividades clave:**
  1. Diagramación de la arquitectura extremo a extremo: Nodo sensor IoT $\rightarrow$ Gateway Wi-Fi $\rightarrow$ API / Servidor Cloud $\rightarrow$ Base de Datos $\rightarrow$ Pipeline de Regresión $\rightarrow$ Dashboard Operativo.
  2. Definición formal del alcance: Prototipo funcional para el grupo piloto delimitado; se excluye el refinado industrial del aceite y la fabricación masiva comercial.
  3. Definición del modelo de localización-asignación capacitada para optimización logística.
* **Entregables:** Diagrama de arquitectura del sistema y Plan Maestro del Proyecto.
* **Criterio de Aceptación:** Interfaces preliminares definidas y documento aprobado por el aprobador del paquete.

---

## 3. Matriz RACI de la Etapa 100

| Paquete de Trabajo | Dahiana (Civil) | Carlos (Electromec.) | Yamilet (Industrial) | Félix (Software) | Anlly (Civil) | Johalfry (Civil) | Marian (Ciberseg.) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **C-1.1 Delimitación y fuentes** | **R** | **A** | C | I | **R** | I | I |
| **C-1.2 Requisitos, normativa, alternativas** | **R** | **R** | **A** | C | I | C | C |
| **C-1.3 Concepto y arquitectura preliminar** | **A** | **R** | C | **R** | I | I | C |

* **A (Accountable / Aprobador):** Único responsable por la aprobación formal de la entrega.
* **R (Responsible / Realizador):** Miembro(s) encargado(s) de ejecutar la tarea.
* **C (Consulted / Consultado):** Aporta criterio técnico y asesoría.
* **I (Informed / Informado):** Mantenido al tanto del estado y avances.

---

## 4. Requisitos Clave Asociados a la Etapa

* **R-06 (Presupuesto y reserva para imprevistos):** Todo el concepto debe acotarse al presupuesto estimado del prototipo, manteniendo una reserva documentada para contingencias de compras locales o importación.
* **R-08 (Protección de datos y privacidad):** El concepto debe contemplar el principio de minimización de datos (sin almacenar datos personales de consumidores de los locales, solo variables operativas).
* **R-10 (Cumplimiento legal y ambiental):** Alineación directa obligatoria con la Ley 225-20, canalizando el residuo recolectado exclusivamente hacia gestores autorizados reconocidos (como Reoil Dominicana o Mevosa).

---

## 5. Disparadores de Retorno hacia/desde la Etapa (Feedback Loops CDIO)

En el marco CDIO, la etapa de concepción recibe retroalimentación si las etapas posteriores encuentran desvíos operativos o de costos:

1. **Retorno RT03 (Implementar I-3.1 $\rightarrow$ Concebir C-1.1):**
   * *Disparador:* Si durante el levantamiento de datos un tipo de negocio genera flujos atípicos por encima o por debajo de la capacidad operativa viable.
   * *Acción:* Redefinir la delimitación, cambiar la capacidad de bidón asignada al local o reemplazar el negocio por otro candidato de la lista.
   * *Aprobador:* Carlos (Electromecánica).
2. **Retorno RT04 (Diseñar D-2.1 a D-2.2 $\rightarrow$ Concebir C-1.2):**
   * *Disparador:* Si el costo cotizado de los componentes del prototipo supera el tope presupuestario fijado en R-06.
   * *Acción:* Ajustar el alcance técnico o evaluar alternativas más económicas de materiales (análisis del Triángulo de Hierro de Proyectos).
   * *Aprobador:* Yamilet (Industrial).

---

## 6. Recursos Educativos y Lecturas Recomendadas (Further Reading)

Para profundizar en los fundamentos de esta etapa, se recomienda el estudio de las siguientes fuentes:

### Gestión de Proyectos y Marco CDIO
* **Metodología CDIO (Conceive-Design-Implement-Operate):**
  * *Crawley, E. F., et al.* "Rethinking Engineering Education: The CDIO Approach". Springer.
  * Sitio oficial: [cdio.org](http://www.cdio.org/) — Estándares mundiales para la educación e ingeniería en proyectos.
* **El Triángulo de Hierro de la Gestión de Proyectos:**
  * *Asana Guide:* "Triángulo de hierro o de gestión de proyectos: Qué es y cómo funciona" ([asana.com](https://asana.com/es/resources/project-management-triangle)).
  * *PMBOK Guide (Project Management Institute):* Capítulos de Gestión del Alcance y Gestión de la Calidad.

### Normativa y Legislación Dominicana sobre Residuos y Medio Ambiente
* **Ley General de Gestión Integral y Coprocesamiento de Residuos Sólidos (Ley No. 225-20):**
  * Gaceta Oficial No. 10990, Congreso Nacional de la República Dominicana.
  * Lectura clave: Principio de Responsabilidad Compartida, Régimen de almacenamiento de aceites vegetales usados y rol de gestores autorizados.
* **Ley General sobre Medio Ambiente y Recursos Naturales (Ley No. 64-00):**
  * Artículos referidos a la protección de cuerpos de agua y vertido de sustancias contaminantes líquidas.
* **Ley General de Salud (Ley No. 42-01):**
  * Artículo 51: Manejo y disposición de residuos y sustancias en establecimientos de manipulación de alimentos.

### Estándares Internacionales y Logística
* **ISO 14001:2015 / ISO 14001:2026:**
  * Sistemas de Gestión Ambiental (SGA) — Requisitos con orientación para su uso.
* **Modelos de Localización-Asignación en Logística:**
  * *Vilà Bonilla, M. (2019).* "Modelos de localización". Universitat Oberta de Catalunya (UOC).
  * Conceptos clave: Localización-asignación capacitada (Capacitated Facility Location Problem - CFLP) para optimizar redes de puntos de acopio de residuos con capacidades máximas.
