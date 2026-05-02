"""
Único publicador simulado para la zona (PDF: sensores periódicos → AWS IoT Core).
Incluye producción, química y seguridad. Sin broker local.
"""
import json
import random
import ssl
import time

import paho.mqtt.client as mqtt

from config import AWS_ENDPOINT, AWS_PORT, CERT_DIR, GRUPO, SECTOR_ID, topic

client = mqtt.Client(client_id="pub_zona_norte_fvz", protocol=mqtt.MQTTv311)
client.tls_set(
    ca_certs=f"{CERT_DIR}/AmazonRootCA1.pem",
    certfile=f"{CERT_DIR}/certificate.pem.crt",
    keyfile=f"{CERT_DIR}/private.pem.key",
    tls_version=ssl.PROTOCOL_TLSv1_2,
)


def on_connect(c, userdata, flags, rc):
    if rc == 0:
        print(f"[Zona] Conectado a AWS IoT Core: {AWS_ENDPOINT}")
    else:
        print(f"[Zona] Error de conexión: {rc}")


client.on_connect = on_connect
client.connect(AWS_ENDPOINT, AWS_PORT, keepalive=60)
client.loop_start()

print(f"[Zona] Publicando telemetría mina/{SECTOR_ID}/{{produccion,quimica,seguridad}}/*")

try:
    while True:
        ronda = [
            (
                topic("produccion", "toneladas_hora"),
                {
                    "sector": SECTOR_ID,
                    "categoria": "produccion",
                    "sensor": "toneladas_hora",
                    "valor": round(random.uniform(120, 420), 2),
                    "unidad": "t/h",
                    "grupo": GRUPO,
                },
            ),
            (
                topic("produccion", "ciclos"),
                {
                    "sector": SECTOR_ID,
                    "categoria": "produccion",
                    "sensor": "ciclos",
                    "valor": random.randint(8, 28),
                    "unidad": "ciclos/h",
                    "grupo": GRUPO,
                },
            ),
            (
                topic("quimica", "ph"),
                {
                    "sector": SECTOR_ID,
                    "categoria": "quimica",
                    "sensor": "ph",
                    "valor": round(random.uniform(6.2, 8.4), 2),
                    "unidad": "pH",
                    "grupo": GRUPO,
                },
            ),
            (
                topic("quimica", "co2"),
                {
                    "sector": SECTOR_ID,
                    "categoria": "quimica",
                    "sensor": "co2",
                    "valor": round(random.uniform(380, 950), 1),
                    "unidad": "ppm",
                    "grupo": GRUPO,
                },
            ),
            (
                topic("quimica", "so2"),
                {
                    "sector": SECTOR_ID,
                    "categoria": "quimica",
                    "sensor": "so2",
                    "valor": round(random.uniform(0.02, 0.35), 3),
                    "unidad": "ppm",
                    "grupo": GRUPO,
                },
            ),
            (
                topic("quimica", "material_particulado"),
                {
                    "sector": SECTOR_ID,
                    "categoria": "quimica",
                    "sensor": "material_particulado",
                    "valor": round(random.uniform(35, 160), 1),
                    "unidad": "μg/m³",
                    "grupo": GRUPO,
                },
            ),
            (
                topic("seguridad", "temperatura"),
                {
                    "sector": SECTOR_ID,
                    "categoria": "seguridad",
                    "sensor": "temperatura",
                    "valor": round(random.uniform(12, 34), 2),
                    "unidad": "°C",
                    "grupo": GRUPO,
                },
            ),
            (
                topic("seguridad", "humedad"),
                {
                    "sector": SECTOR_ID,
                    "categoria": "seguridad",
                    "sensor": "humedad",
                    "valor": round(random.uniform(28, 78), 2),
                    "unidad": "%",
                    "grupo": GRUPO,
                },
            ),
            (
                topic("seguridad", "vibracion"),
                {
                    "sector": SECTOR_ID,
                    "categoria": "seguridad",
                    "sensor": "vibracion",
                    "valor": round(random.uniform(0.05, 2.5), 3),
                    "unidad": "m/s²",
                    "grupo": GRUPO,
                },
            ),
        ]
        for t, data in ronda:
            client.publish(t, json.dumps(data), qos=1)
            print(f"[Zona] {t}")
            time.sleep(1)
        time.sleep(4)
except KeyboardInterrupt:
    client.loop_stop()
    client.disconnect()
