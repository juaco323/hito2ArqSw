# Monitoreo minero IoT — Sector norte (Hito 2)

Sistema acorde a la consigna **«Sistema IoT para monitoreo de extracción minera»**: telemetría simulada para la zona **sector_norte_Fuenzalida_Vallejos**, **MQTT solo contra AWS IoT Core** (sin broker local tipo Mosquitto), persistencia en **MongoDB**, API **Flask**, dashboard **Streamlit** y despliegue con **Docker**.

> **Consigna PDF:** conexión obligatoria al broker configurado en **AWS IoT Core**. No está permitido crear ni usar un broker MQTT alternativo (p. ej. Mosquitto en Docker).

---

## Arquitectura

```
[Publicadores : producción / química / seguridad]
            │  MQTT TLS :8883   ┌─────────────────────┐
            └──────────────────►│   AWS IoT Core      │
                                │   (único broker)    │
            ┌──────────────────►│                     │
[subscriber]│  subscribe + certs└─────────────────────┘
            │
            ▼ insert
      [MongoDB :27017] ◄── find ── [REST API Flask :5000] ◄── HTTP ── [Streamlit :8501]
```

| Rol | Qué es | Puerto expuesto (host) |
|-----|--------|-------------------------|
| Broker MQTT | **AWS IoT Core** (fuera de Docker) | — (8883 en la nube) |
| MongoDB | Base `mina_iot` | 27017 |
| `subscriber` | PAHO MQTT → MongoDB | — |
| `rest_api` | Flask | 5000 |
| `frontend` | Streamlit | 8501 |
| `publicador` | Simula todos los sensores del sector (un proceso) | — |

Los certificados del thing (`certs/*.pem`) se montan en volumen de solo lectura en subscriber y publicadores.

---

## Requisitos

- Docker y Docker Compose
- Políticas en **AWS IoT Core** que permitan publicar/suscribir en los topics `mina/sector_norte_Fuenzalida_Vallejos/#` (o el prefijo que uses), con el certificado del proyecto

---

## Ejecución con Docker (todo el sistema)

El archivo **`docker-compose.yml`** está en la carpeta **`iot_agro_project_Zapallo`** (raíz del repo). Ahí debés ejecutar Compose o abrir el proyecto en Docker Desktop.

```bash
cd ruta\a\iot_agro_project_Zapallo
docker compose up --build -d
```

**Docker Desktop:** *Containers* → *Import* / *Open* la carpeta `iot_agro_project_Zapallo`, o desde terminal en esa carpeta ejecutá el comando de arriba; el stack aparecerá como **`mina_iot_sector_norte`**.

- Dashboard: `http://localhost:8501`  
- API: `http://localhost:5000/logs` , `http://localhost:5000/health`

---

## Estructura relevante

```
iot_agro_project_Zapallo/
├── docker-compose.yml        # Único compose del proyecto (raíz)
iot_agro_project/
├── certs/                    # Certificados AWS IoT (no versionar claves en repos públicos)
├── mqtt_client/subscriber.py
├── rest_api/app.py
├── frontend/app.py
└── sensors/publicador_zona.py
```

---

## Solución de problemas

| Síntoma | Qué revisar |
|---------|----------------|
| Clientes MQTT no conectan | Política IAM del certificado en AWS IoT; endpoint `AWS_IOT_ENDPOINT`; validez del certificado |
| API sin datos | Subscriber corriendo y escribiendo en MongoDB; mismo `GRUPO`/`SECTOR_ID` en publicadores y subscriber |
| Frontend vacío | `rest_api` healthy; esperar unos segundos tras el arranque |

---

## Referencias de diseño

- `../JUSTIFICACION_ARQUITECTONICA.md` — decisiones y preguntas típicas de defensa oral  
- `FUNCIONAMIENTO.md` — flujo técnico del sistema actual (AWS IoT Core)
