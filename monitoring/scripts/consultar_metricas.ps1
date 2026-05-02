# Consultas rápidas a Prometheus (stack mina_iot en localhost).
# Requisitos: docker compose levantado; Prometheus :9090 accesible.

$base = "http://localhost:9090/api/v1/query"

function Get-PromQuery {
    param([string]$Query)
    $enc = [uri]::EscapeDataString($Query)
    $url = "$base`?query=$enc"
    try {
        $r = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 15
        return $r
    } catch {
        Write-Host "Error llamando a Prometheus: $_" -ForegroundColor Red
        return $null
    }
}

Write-Host "=== 1) Latencia de transmisión (p95 y p50, últimos 5m) ===" -ForegroundColor Cyan
$q95 = 'histogram_quantile(0.95, sum(rate(mina_mqtt_ingest_latency_seconds_bucket[5m])) by (le))'
$q50 = 'histogram_quantile(0.50, sum(rate(mina_mqtt_ingest_latency_seconds_bucket[5m])) by (le))'
(Get-PromQuery $q95).data.result | ForEach-Object { "  p95 (s): $($_.value[1])" }
(Get-PromQuery $q50).data.result | ForEach-Object { "  p50 (s): $($_.value[1])" }

Write-Host "`n=== 2) Frecuencia de publicación / ingesta (msg/s, ventana 1m) ===" -ForegroundColor Cyan
$qp = "rate(mina_mqtt_messages_published_total[1m])"
$qr = "rate(mina_mqtt_messages_received_total[1m])"
(Get-PromQuery $qp).data.result | ForEach-Object { "  publicados/s: $($_.value[1])" }
(Get-PromQuery $qr).data.result | ForEach-Object { "  persistidos/s: $($_.value[1])" }

Write-Host "`n=== 3) Volumen datos MongoDB (bytes, métrica exporter) ===" -ForegroundColor Cyan
$qm = 'sum(mongodb_dbstats_data_size_bytes{database="mina_iot"}) or sum(mongodb_dbstats_data_size_bytes)'
(Get-PromQuery $qm).data.result | ForEach-Object { "  dataSize (bytes): $($_.value[1])" }

Write-Host "`n=== Endpoints útiles ===" -ForegroundColor Cyan
Write-Host "  Grafana:     http://localhost:3000"
Write-Host "  Prometheus:  http://localhost:9090"
Write-Host "  /metrics subscriber: http://localhost:9101/metrics"
Write-Host "  /metrics publicador: http://localhost:9102/metrics"
Write-Host "  /metrics mongo exp.: http://localhost:9216/metrics"
