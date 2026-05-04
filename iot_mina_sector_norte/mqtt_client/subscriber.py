import json
import os
import ssl
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from prometheus_client import Counter, Histogram, start_http_server
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

SECTOR_ID = os.getenv("SECTOR_ID", "sector_norte_Fuenzalida_Vallejos")
AWS_ENDPOINT = os.getenv("AWS_IOT_ENDPOINT", "a2apsmaa0mdv52-ats.iot.us-east-1.amazonaws.com")
AWS_PORT = 8883
CERT_DIR = os.getenv("CERT_DIR", "/app/certs")
TOPIC = f"mina/{SECTOR_ID}/#"
METRICS_PORT = int(os.getenv("METRICS_PORT", "9101"))

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017/")
DB_NAME = os.getenv("MONGO_DB", "mina_iot")
COLL_NAME = os.getenv("MONGO_COLLECTION", "lecturas")

LATENCY_SECONDS = Histogram(
    "mina_mqtt_ingest_latency_seconds",
    "Tiempo desde published_at (publicador) hasta recepción en subscriber",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)
MESSAGES_RECEIVED = Counter(
    "mina_mqtt_messages_received_total",
    "Mensajes MQTT del sector esperado persistidos en MongoDB",
)
MESSAGES_IGNORED = Counter(
    "mina_mqtt_messages_ignored_total",
    "Mensajes MQTT descartados (sector del payload distinto al configurado)",
)


def conectar_mongo(reintentos=10, espera=3):
    for intento in range(1, reintentos + 1):
        try:
            cliente = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
            cliente.admin.command("ping")
            print("Conectado a MongoDB")
            return cliente
        except ConnectionFailure:
            print(f"MongoDB no disponible, reintento {intento}/{reintentos}...")
            time.sleep(espera)
    raise RuntimeError("No se pudo conectar a MongoDB tras varios intentos")


def _parse_published_at(raw):
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _latency_seconds(pub_at):
    if pub_at is None:
        return None
    now = datetime.now(timezone.utc)
    return max(0.0, (now - pub_at).total_seconds())


# /metrics antes de Mongo para que Prometheus pueda scrapear aunque la DB tarde
start_http_server(METRICS_PORT)
print(f"Métricas Prometheus en puerto {METRICS_PORT}")

mongo = conectar_mongo()
coleccion = mongo[DB_NAME][COLL_NAME]


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Subscriber conectado a AWS IoT Core: {AWS_ENDPOINT}")
        client.subscribe(TOPIC, qos=1)
        print(f"Suscrito al topic: {TOPIC}")
    else:
        print(f"Error al conectar, código: {rc}")


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        partes = msg.topic.split("/")
        if len(partes) >= 4:
            data.setdefault("sector", partes[1])
            data.setdefault("categoria", partes[2])
            data.setdefault("sensor", partes[3])

        if data.get("sector") != SECTOR_ID:
            print(f"Mensaje ignorado (sector): {data.get('sector')} topic={msg.topic}")
            MESSAGES_IGNORED.inc()
            return

        pub_raw = data.pop("published_at", None)
        pub_dt = _parse_published_at(pub_raw)
        lat = _latency_seconds(pub_dt)
        if lat is not None:
            LATENCY_SECONDS.observe(lat)

        data["timestamp"] = datetime.now(timezone.utc)
        data["topic_mqtt"] = msg.topic
        coleccion.insert_one(data)
        MESSAGES_RECEIVED.inc()
        print(f"Guardado MongoDB topic={msg.topic} sensor={data.get('sensor')}")
    except Exception as e:
        print(f"Error procesando mensaje: {e}")


client = mqtt.Client(client_id="subscriber_mina_norte_fvz", protocol=mqtt.MQTTv311)
client.tls_set(
    ca_certs=f"{CERT_DIR}/AmazonRootCA1.pem",
    certfile=f"{CERT_DIR}/certificate.pem.crt",
    keyfile=f"{CERT_DIR}/private.pem.key",
    tls_version=ssl.PROTOCOL_TLSv1_2,
)
client.on_connect = on_connect
client.on_message = on_message

client.connect(AWS_ENDPOINT, AWS_PORT, keepalive=60)
client.loop_forever()
