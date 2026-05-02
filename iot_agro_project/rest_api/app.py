import os
from datetime import datetime

from flask import Flask, jsonify, request
from flasgger import Swagger
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure

app = Flask(__name__)

# Swagger UI en /apidocs — solo documentación; no valida peticiones (no interfiere con clientes).
Swagger(
    app,
    template={
        "swagger": "2.0",
        "info": {
            "title": "Mina IoT — API lecturas",
            "description": "REST de solo lectura (sector configurado por entorno). MongoDB: colección de lecturas.",
            "version": "1.0.0",
        },
    },
)

GRUPO = os.getenv("GRUPO", "zapallo")
SECTOR_ID = os.getenv("SECTOR_ID", "sector_norte_Fuenzalida_Vallejos")
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
            import time

            time.sleep(espera)
    raise RuntimeError("No se pudo conectar a MongoDB tras varios intentos")


mongo = conectar_mongo()
coleccion = mongo[DB_NAME][COLL_NAME]


def _serializar_doc(doc):
    out = dict(doc)
    ts = out.get("timestamp")
    if isinstance(ts, datetime):
        out["timestamp"] = ts.isoformat()
    return out


@app.route("/health", methods=["GET"])
def health():
    """Comprobación de vida del servicio
    ---
    tags:
      - Sistema
    responses:
      200:
        description: API operativa
        schema:
          type: object
          properties:
            status:
              type: string
              example: ok
            sector:
              type: string
    """
    return jsonify({"status": "ok", "sector": SECTOR_ID})


@app.route("/logs", methods=["GET"])
def logs():
    """Lecturas históricas del sector (solo lectura)
    ---
    tags:
      - Lecturas
    parameters:
      - name: limit
        in: query
        type: integer
        default: 400
        description: Cantidad máxima de documentos (máximo 5000)
      - name: order
        in: query
        type: string
        enum: [asc, desc]
        default: desc
        description: Orden por timestamp
      - name: categoria
        in: query
        type: string
        required: false
        description: Filtrar por categoría (p. ej. produccion)
      - name: sensor
        in: query
        type: string
        required: false
        description: Filtrar por nombre de sensor
    responses:
      200:
        description: Lista de lecturas (JSON array)
        schema:
          type: array
          items:
            type: object
      500:
        description: Error al consultar MongoDB
        schema:
          type: object
          properties:
            error:
              type: string
    """
    try:
        filt = {"sector": SECTOR_ID}
        cat = request.args.get("categoria")
        sen = request.args.get("sensor")
        if cat:
            filt["categoria"] = cat
        if sen:
            filt["sensor"] = sen

        limit = min(int(request.args.get("limit", 400)), 5000)
        orden = request.args.get("order", "desc")
        sort_dir = DESCENDING if orden != "asc" else ASCENDING

        cursor = coleccion.find(filt, {"_id": 0}).sort("timestamp", sort_dir).limit(limit)
        docs = [_serializar_doc(d) for d in cursor]
        return jsonify(docs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/meta", methods=["GET"])
def meta():
    """Categorías y sensores distintos (filtros UI)
    ---
    tags:
      - Metadatos
    responses:
      200:
        description: Listas para selectores en Streamlit
        schema:
          type: object
          properties:
            sector:
              type: string
            grupo:
              type: string
            categorias:
              type: array
              items:
                type: string
            sensores:
              type: array
              items:
                type: string
      500:
        description: Error al consultar MongoDB
        schema:
          type: object
          properties:
            error:
              type: string
    """
    try:
        categorias = coleccion.distinct("categoria", {"sector": SECTOR_ID})
        sensores = coleccion.distinct("sensor", {"sector": SECTOR_ID})
        return jsonify(
            {
                "sector": SECTOR_ID,
                "grupo": GRUPO,
                "categorias": sorted(categorias),
                "sensores": sorted(sensores),
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
