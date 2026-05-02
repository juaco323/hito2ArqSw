# Justificación de decisiones arquitectónicas — Hito 2 MQTT (mina, sector norte)

Proyecto orientado a la evaluación sumativa **«Sistema IoT para monitoreo de extracción minera»**, focalizado en la zona **sector_norte_Fuenzalida_Vallejos**, con las tecnologías obligatorias: **AWS IoT Core (MQTT)**, **MongoDB**, **Flask (REST)**, **Streamlit** y **Docker**.

**Fidelidad al PDF:** la consigna exige usar **solo** el broker configurado en **AWS IoT Core** y **no** crear un broker MQTT alternativo. Por tanto **no se usa Mosquitto** (ni otro broker local en Docker/puerto 1883): el único broker es el **servicio gestionado en AWS**.

## 1. Visión general de la arquitectura

El sistema sigue un patrón **orientado a eventos / publicar–suscribir** entre borde simulado y núcleo de procesamiento:

1. **Publicadores** (contenedores Python + PAHO) generan telemetría de producción, química y seguridad y la envían al **broker único** **AWS IoT Core** mediante MQTT sobre TLS (puerto 8883).
2. El **subscriber** se suscribe con un wildcard jerárquico al prefijo del sector y persiste cada mensaje válido en **MongoDB** con marca temporal **UTC**.
3. **Flask** expone la colección mediante **REST** (solo lectura para el dashboard), permitiendo filtrar por categoría y tipo de sensor.
4. **Streamlit** consume el API, aplica filtros en la UI y muestra tablas y **gráficos de tendencia** (Plotly), con actualización **cuasi en tiempo real** (auto-refresh).
5. **Docker Compose** orquesta MongoDB, subscriber, API, frontend y el publicador de zona para un despliegue reproducible.

Esta separación desacopla el **ritmo de publicación MQTT** del **consumo HTTP** del operador: los sensores no conocen al dashboard; el dashboard no bloquea la ingesta.

## 2. Decisiones clave y su motivación

### 2.1 Topics MQTT jerárquicos (`mina/<sector>/<categoría>/<métrica>`)

**Decisión:** Usar una convención alineada con la consigna del PDF (`mina/zona_norte/...`), sustituyendo la zona por el identificador del grupo **sector_norte_Fuenzalida_Vallejos**.

**Por qué:**

- Refleja la **estructura física/operativa** (mina → sector → familia de variables → métrica).
- Permite **wildcard** del suscriptor (`mina/sector_norte_Fuenzalida_Vallejos/#`) sin mezclar otras zonas si en el futuro se agregan más sectores en el mismo broker.
- Facilita **políticas IAM / autorización** en AWS IoT Core por prefijo de topic.

**Importante:** Si las políticas del certificado en AWS IoT Core estaban limitadas a otro prefijo (por ejemplo `campo/#`), debe actualizarse la política para permitir `mina/*` o el prefijo concreto del sector; si no, los clientes recibirán error de autorización.

### 2.2 QoS 1 en publicación y suscripción

**Decisión:** Publicar y suscribir con **QoS 1** (al menos una entrega).

**Por qué:**

- En entorno industrial/minero interesa **no perder lecturas** por cortes breves de red.
- QoS 1 ofrece un equilibrio razonable entre **confiabilidad** y **coste de mensajes** respecto a QoS 2 (exactamente una vez, más conversación en el protocolo).
- QoS 0 habría sido aceptable solo para métricas puramente “best effort”; la consigna y la rúbrica valoran la **justificación del QoS**, por eso se privilegió 1.

### 2.3 MongoDB (NoSQL, documentos)

**Decisión:** Base **mina_iot**, colección **lecturas**, un documento por evento con campos como `sector`, `categoria`, `sensor`, `valor`, `unidad`, `timestamp`, `topic_mqtt`, `grupo`.

**Por qué:**

- El dominio es **alta frecuencia de escrituras** con esquema relativamente uniforme pero evolutivo (nuevas métricas o unidades): los documentos JSON encajan naturalmente.
- Permite **historizar** sin migraciones rígidas propias de tablas relacionales.
- Consultas por sector/categoría/sensor con índices simples (para producción se recomendaría crear índices compuestos sobre `sector`, `timestamp`, etc.).

### 2.4 Flask como capa REST entre MongoDB y Streamlit

**Decisión:** El dashboard **no** accede directamente a MongoDB.

**Por qué:**

- **Separación de responsabilidades:** Streamlit se centra en visualización; el API centraliza reglas de filtrado y límites (`limit`, `order`).
- **Seguridad y despliegue:** En un entorno real, expondrías autenticación y rate limiting en el API, no en el notebook/dashboard.
- La consigna pide explícitamente un **backend Flask** para el frontend Streamlit.

### 2.5 Streamlit local (en contenedor) y actualización cuasi en tiempo real

**Decisión:** Auto-refresh periódico (p. ej. 8 s) en lugar de WebSockets MQTT en el navegador.

**Por qué:**

- Cumple el requisito de **visualización local** y simplifica la demo académica.
- **MQTT en el browser** implicaría WebSockets + autenticación distinta o bridge; no es obligatorio en la consigna y añade complejidad.
- El retardo aceptado es **cuasi tiempo real**, adecuado para supervisión gerencial de tendencias.

### 2.6 Contenedores Docker

**Decisión:** Un servicio por rol (ingesta, DB, API, UI, un publicador que concentra la telemetría de la zona).

**Por qué:**

- Reproducibilidad para corrección y presentación oral.
- Escalar horizontalmente publicadores o réplicas del subscriber en escenarios mayores (con cuidado de **IDs de cliente MQTT únicos** y políticas AWS).

## 3. Métricas estimadas (para exposición oral)

| Concepto | Estimación orientativa |
|----------|-------------------------|
| Frecuencia del publicador | Una ronda completa de métricas (~9 publicaciones) cada ~13 s → orden de **0,5–0,7 eventos/s** en conjunto |
| Latencia publicador → suscriptor | Típicamente **100 ms–1 s** en Internet hogar/lab; medible con logs `timestamp` embebidos |
| Volumen en MongoDB | Con un publicador por zona activo, órdenes de **decenas de miles de documentos/día** si se dejara 24 h; en demo de minutos, bastante menor |

(Ajustar números midiendo en tu red durante la demo.)

## 4. Escalabilidad (cómo crecería el sistema)

- **Más zonas:** Nuevos prefijos `mina/<otro_sector>/...` y políticas AWS por prefijo; opcionalmente **varios subscribers** con partición por prefijo o **shard en MongoDB** por `sector`.
- **Mayor carga:** Cola intermediaria (p. ej. Kinesis, MSK) entre IoT Core y persistencia si el volumen supera la escritura directa a MongoDB.
- **Dashboard:** Cacheo en API, paginación, índices MongoDB, o sustitución de polling por **Server-Sent Events** si se requiere menor latencia.

## 5. Preguntas que podría hacer el profesor — y respuestas sugeridas

**P: ¿Por qué MQTT y no REST desde los sensores hacia el servidor?**  
**R:** MQTT está pensado para **telemetría continua**, **ancho de banda reducido** y redes **inestables**; el modelo pub/sub desacopla sensores de consumidores. REST implicaría **polling** o muchas conexiones HTTP concurrentes y mayor overhead por lectura.

**P: ¿Por qué QoS 1 y no 0 o 2?**  
**R:** QoS 0 no garantiza entrega; QoS 2 garantiza exactamente una vez pero con **más ida y vuelta** y coste. QoS 1 es el compromiso habitual para **telemetría que no puede perderse** pero tolera **duplicados raros** (manejables en ingesta idempotente).

**P: ¿Usan Mosquitto u otro broker en Docker? ¿Por qué no?**  
**R:** **No.** La consigna prohibe un broker alternativo al de **AWS IoT Core**. Mosquitto en local sería un segundo broker y no cumpliría el requisito. Todo el tráfico MQTT va al endpoint de AWS (**TLS 8883**, certificados del curso).

**P: ¿Cómo evitan que otro grupo “contamine” nuestra base de datos si todos usan el mismo broker?**  
**R:** Filtramos por **`grupo`** en el payload y por **`sector`** coherente con el topic; solo persistimos si coinciden. En producción se usarían **certificados/políticas por dispositivo** y topics aislados por cuenta o prefijo.

**P: ¿Por qué Flask y no GraphQL / FastAPI?**  
**R:** La consigna pide Flask explícito y el dominio es **consultas simples** de lectura; FastAPI podría ser alternativa moderna, pero no aporta ventaja decisiva para este alcance.

**P: ¿El dashboard es tiempo real?**  
**R:** Es **cuasi tiempo real**: Streamlit **refresca** periódicamente vía REST; la ingesta MQTT sigue siendo en tiempo real hasta MongoDB. Para latencias sub-segundo en UI haría falta otro canal (WebSockets).

**P: ¿Qué pasa si MongoDB cae?**  
**R:** El subscriber debería implementar **cola local** o política de **backpressure**; en esta versión académica se prioriza simplicidad y se reconoce el riesgo de pérdida de mensajes si la DB está caída.

**P: ¿Cómo escalarían a 50 sectores?**  
**R:** Particionar topics, **índices** por `sector` y `timestamp`, posiblemente **múltiples instancias** de subscriber con **client ID** únicos y políticas AWS; valorar **TTL** en colecciones para archivar datos antiguos.

**P: ¿Por qué documentos planos y no una colección por tipo de sensor?**  
**R:** Un solo tipo de **evento de lectura** simplifica ingesta y consultas globales; las colecciones separadas optimizarían casos muy específicos pero complican el pipeline de ingesta.

---

*Documento orientado a la defensa oral del Hito 2; el código ejecutable y la demo en Docker complementan estas respuestas.*
