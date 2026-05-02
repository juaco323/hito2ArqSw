# Funcionamiento del sistema — Hito 2 (mina, AWS IoT Core)

Este documento describe el despliegue **vigente**: cumple la consigna de usar **únicamente AWS IoT Core** como broker MQTT (**no** Eclipse Mosquitto ni otro broker alternativo en Docker o en máquina local).

---

## 1. Visión general

El sistema simula sensores de una **mina a tajo abierto** en el sector **sector_norte_Fuenzalida_Vallejos**. Hay tres familias de variables:

- **Producción:** toneladas por hora, ciclos.
- **Química:** pH, CO₂, SO₂, material particulado.
- **Seguridad:** temperatura, humedad, vibración.

La telemetría sale por **MQTT** hacia **AWS IoT Core** (broker gestionado). Un **subscriber** en Docker se suscribe a los topics del sector, valida el mensaje y lo guarda en **MongoDB**. El **dashboard Streamlit** no usa MQTT directamente: consulta una **API Flask** que lee MongoDB.

---

## 2. Arquitectura y flujo de datos

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         Internet / AWS                                    │
│   ┌────────────────────────────────────────────────────────────────────┐ │
│   │  AWS IoT Core — único broker MQTT (TLS :8883, certificados X.509)  │ │
│   └────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
        ▲ publish                           ▲ subscribe
        │ topics: mina/<sector>/<cat>/<métrica>
┌───────┴──────────────────────────────────────────────────────────────────┐
│                       Red Docker (Compose)                                │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────────────┐ │
│  │ publicador      │   │ subscriber      │   │ MongoDB :27017          │ │
│  │ (simula zona)   │   │ mqtt_client     │──►│ db mina_iot / lecturas  │ │
│  └─────────────────┘   └────────┬────────┘   └────────────▲────────────┘ │
│                                 │ insert                   │ find          │
│                                 │             ┌────────────┴────────────┐ │
│                                 │             │ rest_api Flask :5000    │ │
│                                 │             └────────────▲────────────┘ │
│                                 │                          │ GET           │
│                                 │             ┌────────────┴────────────┐ │
│                                 │             │ Streamlit :8501       │ │
│                                 │             └───────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

**Orden lógico de arranque (Compose):** MongoDB *healthy* → subscriber y API → API *healthy* → Streamlit; los publicadores esperan al subscriber *started* para reducir pérdidas tempranas de mensajes.

---

## 3. MQTT y broker

| Concepto | En este proyecto |
|----------|-------------------|
| **Broker** | **Solo AWS IoT Core**. No hay servicio `mosquitto` ni puerto **1883** en la stack Docker. |
| **Transporte** | MQTT sobre **TLS** (puerto **8883**), autenticación con CA + certificado de dispositivo + clave privada. |
| **Topics** | Jerárquicos: `mina/sector_norte_Fuenzalida_Vallejos/<categoría>/<métrica>`. |
| **QoS** | Nivel **1** (al menos una entrega) en publicación y suscripción, según implementación en código. |

Los clientes Python usan **Paho** (`paho-mqtt`) con `tls_set(...)` apuntando a los archivos en `certs/`.

---

## 4. Por qué no hay Mosquitto aquí

La evaluación sumativa exige el broker **ya configurado en AWS IoT Core** y **no permite** un broker alternativo. Mosquitto sería un segundo broker en paralelo y contradiría la consigna. El patrón pub/sub se cumple igual: el **agente broker** es el de AWS, no un contenedor local.

---

## 5. REST API y Streamlit

- **Flask** expone JSON (`/logs`, `/meta`, `/health`) para no acoplar la UI a MongoDB.
- **Streamlit** hace polling HTTP (actualización cuasi en tiempo real), no suscripción MQTT en el navegador.

---

## 6. MongoDB

Cada mensaje aceptado por el subscriber genera un documento con `timestamp` (UTC), `sector`, `categoria`, `sensor`, `valor`, `unidad`, `topic_mqtt`, `grupo`, etc.

---

## 7. QoS y sesión MQTT (recordatorio)

Con **QoS 1**, el broker confirma recepción del mensaje al publicador; conviene para telemetría que no deba perderse por cortes breves. Los **client IDs** deben ser únicos en el broker para cada conexión simultánea.

---

## 8. Ciclo de vida de un dato (resumen)

1. El `publicador` construye cada JSON y lo publica en AWS IoT Core.
2. AWS enruta el mensaje al `subscriber` suscrito al prefijo del sector.
3. El subscriber inserta en MongoDB.
4. Streamlit pide datos al Flask; el usuario ve tablas y tendencias.

Si necesitas contrastar **MQTT frente a REST** en abstracto (conceptos de curso), sigue siendo válido: MQTT para muchos eventos pequeños desde el borde; REST para consultas bajo demanda desde la aplicación web.
