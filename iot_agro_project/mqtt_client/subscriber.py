import json
import os
import ssl
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

GRUPO = os.getenv("GRUPO", "zapallo")
SECTOR_ID = os.getenv("SECTOR_ID", "sector_norte_Fuenzalida_Vallejos")
AWS_ENDPOINT = os.getenv("AWS_IOT_ENDPOINT", "a2apsmaa0mdv52-ats.iot.us-east-1.amazonaws.com")
AWS_PORT = 8883
CERT_DIR = os.getenv("CERT_DIR", "/app/certs")
TOPIC = f"mina/{SECTOR_ID}/#"

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017/")
DB_NAME = os.getenv("MONGO_DB", "mina_iot")
COLL_NAME = os.getenv("MONGO_COLLECTION", "lecturas")


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

        if data.get("grupo") != GRUPO:
            print(f"Mensaje ignorado (grupo): {data.get('grupo')} topic={msg.topic}")
            return
        if data.get("sector") != SECTOR_ID:
            print(f"Mensaje ignorado (sector): {data.get('sector')} topic={msg.topic}")
            return

        data["timestamp"] = datetime.now(timezone.utc)
        data["topic_mqtt"] = msg.topic
        coleccion.insert_one(data)
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
