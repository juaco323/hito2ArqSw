#!/usr/bin/env bash
# Consultas rápidas a Prometheus (Linux/macOS/Git Bash).
set -euo pipefail

BASE="http://localhost:9090/api/v1/query"

q() {
  curl -sG "$BASE" --data-urlencode "query=$1"
}

echo "=== 1) Latencia de transmisión (p95 / p50, últimos 5m) ==="
q 'histogram_quantile(0.95, sum(rate(mina_mqtt_ingest_latency_seconds_bucket[5m])) by (le))' | head -c 1200
echo ""
q 'histogram_quantile(0.50, sum(rate(mina_mqtt_ingest_latency_seconds_bucket[5m])) by (le))' | head -c 1200
echo ""

echo "=== 2) Frecuencia publicación / ingesta (msg/s, ventana 1m) ==="
q 'rate(mina_mqtt_messages_published_total[1m])' | head -c 1200
echo ""
q 'rate(mina_mqtt_messages_received_total[1m])' | head -c 1200
echo ""

echo "=== 3) Volumen datos MongoDB (bytes) ==="
q 'sum(mongodb_dbstats_data_size_bytes{database="mina_iot"}) or sum(mongodb_dbstats_data_size_bytes)' | head -c 1200
echo ""

echo "=== Endpoints ==="
echo "  Grafana: http://localhost:3000"
echo "  Prometheus: http://localhost:9090"
echo "  /metrics subscriber :9101 | publicador :9102 | mongo_exporter :9216"
