"""Configuración compartida para publicadores MQTT (mina → AWS IoT Core)."""
import os

SECTOR_ID = os.getenv("SECTOR_ID", "sector_norte_Fuenzalida_Vallejos")
AWS_ENDPOINT = os.getenv("AWS_IOT_ENDPOINT", "a2apsmaa0mdv52-ats.iot.us-east-1.amazonaws.com")
AWS_PORT = 8883
CERT_DIR = os.getenv("CERT_DIR", "/app/certs")


def topic(categoria: str, metrica: str) -> str:
    return f"mina/{SECTOR_ID}/{categoria}/{metrica}"
