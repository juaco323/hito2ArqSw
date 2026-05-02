import os

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh

API_BASE = os.getenv("STREAMLIT_API_BASE", "http://localhost:5000")
SECTOR_LABEL = os.getenv("SECTOR_ID", "sector_norte_Fuenzalida_Vallejos")

st.set_page_config(
    page_title="Mina — Sector Norte",
    page_icon="⛏️",
    layout="wide",
)

st_autorefresh(interval=8000, key="refresh_mina")

st.title("Monitoreo minero — Sector Norte")
st.caption(
    f"Zona operativa **{SECTOR_LABEL}** · Telemetría vía MQTT (AWS IoT Core) · Persistencia MongoDB"
)


def fetch_json(path, params=None):
    r = requests.get(f"{API_BASE}{path}", params=params or {}, timeout=15)
    r.raise_for_status()
    return r.json()


try:
    meta = fetch_json("/meta")
except Exception as e:
    st.error(f"No se pudo contactar el backend Flask ({API_BASE}): {e}")
    st.stop()

col_f1, col_f2 = st.columns(2)
with col_f1:
    cats = ["(todas)"] + list(meta.get("categorias") or [])
    categoria = st.selectbox("Filtrar por categoría", cats)
with col_f2:
    sens = ["(todos)"] + list(meta.get("sensores") or [])
    sensor = st.selectbox("Filtrar por sensor", sens)

params = {"limit": 500, "order": "desc"}
if categoria != "(todas)":
    params["categoria"] = categoria
if sensor != "(todos)":
    params["sensor"] = sensor

try:
    rows = fetch_json("/logs", params=params)
except Exception as e:
    st.error(f"Error leyendo lecturas: {e}")
    st.stop()

if not rows:
    st.info("Sin datos aún. Verificá que el subscriber y los publicadores estén activos.")
    st.stop()

df = pd.DataFrame(rows)
if "timestamp" in df.columns:
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    # Siempre: más reciente arriba → al hacer scroll hacia abajo, lecturas más antiguas
    df = df.sort_values("timestamp", ascending=False, na_position="last")

st.subheader("Últimas lecturas")
show_cols = [c for c in ["timestamp", "categoria", "sensor", "valor", "unidad", "topic_mqtt"] if c in df.columns]
st.dataframe(
    df[show_cols],
    use_container_width=True,
    height=420,
)

st.subheader("Tendencias por categoría")
charted = False
if len(df) >= 2 and "valor" in df.columns and "categoria" in df.columns and "sensor" in df.columns:
    for cat in sorted(df["categoria"].dropna().unique()):
        sub = df[df["categoria"] == cat]
        if sub.empty:
            continue
        top_s = sub["sensor"].value_counts().index[0]
        sub_s = sub[sub["sensor"] == top_s].sort_values("timestamp")
        if len(sub_s) < 2:
            continue
        fig = px.line(
            sub_s,
            x="timestamp",
            y="valor",
            markers=True,
            title=f"{str(cat).title()} · variable «{top_s}» (ejemplo de tendencia en {SECTOR_LABEL})",
        )
        fig.update_layout(hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
        charted = True

if not charted:
    st.warning("Datos insuficientes o filtros demasiado restrictivos para armar gráficos de línea.")

with st.expander("Estado del API"):
    try:
        h = fetch_json("/health")
        st.json(h)
    except Exception as ex:
        st.write(ex)
