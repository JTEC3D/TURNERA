
import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="Turnera - Vistas Demo Final", layout="wide")

# --- Base de datos ---
db_path = os.path.join(os.path.dirname(__file__), "turnos.db")
conn = sqlite3.connect(db_path, check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS turnos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paciente TEXT,
    email TEXT,
    fecha TEXT,
    hora TEXT,
    observaciones TEXT
)''')
conn.commit()

# --- Funciones ---
def obtener_turnos():
    c.execute("SELECT * FROM turnos ORDER BY fecha, hora")
    df = pd.DataFrame(c.fetchall(), columns=["ID", "Paciente", "Email", "Fecha", "Hora", "Observaciones"])
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df = df.dropna(subset=["Fecha", "Hora"])
    df["Hora"] = df["Hora"].astype(str).str.strip().str[:5]
    df["Datetime"] = pd.to_datetime(df["Fecha"].dt.strftime("%Y-%m-%d") + " " + df["Hora"], errors="coerce")
    return df

def generar_base_semanal():
    horarios_m = [f"{h:02d}:00" for h in list(range(7, 12))]
    horarios_t = [f"{h:02d}:00" for h in list(range(15, 21))]
    horarios = horarios_m + horarios_t
    base = []
    hoy = datetime.today()
    lunes = hoy - timedelta(days=hoy.weekday())
    for semana in [0, 1]:
        for dia in range(6):  # Lunes a sábado
            fecha = lunes + timedelta(days=dia + semana * 7)
            if fecha.weekday() == 5:
                horas = horarios_m
            else:
                horas = horarios
            for h in horas:
                base.append({"Fecha": fecha.date(), "Hora": h})
    return pd.DataFrame(base)

# --- Cargar datos ---
df_turnos = obtener_turnos()
df_base = generar_base_semanal()

# Unimos base con turnos para identificar ocupación
df_base["key"] = df_base["Fecha"].astype(str) + " " + df_base["Hora"]
df_turnos["key"] = df_turnos["Fecha"].dt.date.astype(str) + " " + df_turnos["Hora"]
df_merge = pd.merge(df_base, df_turnos, on="key", how="left")

# Selector de vista
st.title("📊 Vistas Semanales de Turnos")
vista = st.selectbox("Elegí la vista", ["Vista tipo Gantt", "Mapa de calor", "Timeline por paciente"])

# --- Vista tipo Gantt (Plotly) ---
if vista == "Vista tipo Gantt":
    st.subheader("📅 Turnos estilo Gantt semanal")

    gantt_data = df_turnos.copy()
    gantt_data["start"] = gantt_data["Datetime"]
    gantt_data["end"] = gantt_data["start"] + pd.Timedelta(hours=1)
    gantt_data["FechaStr"] = gantt_data["Fecha"].dt.strftime("%a %d/%m")

    if not gantt_data.empty:
        fig = px.timeline(
            gantt_data,
            x_start="start",
            x_end="end",
            y="FechaStr",
            color="Paciente",
            hover_data=["Hora", "Email", "Observaciones"]
        )
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay turnos cargados para mostrar.")

# --- Vista Heatmap ---
elif vista == "Mapa de calor":
    st.subheader("🟩🟥 Mapa de calor de ocupación")

    df_heat = df_merge.copy()
    df_heat["estado"] = df_heat["Paciente"].notnull().map({True: "Ocupado", False: "Libre"})
    pivot = df_heat.pivot(index="Hora", columns="Fecha", values="estado").fillna("Libre")

    fig, ax = plt.subplots(figsize=(12, 6))
    sns.heatmap(pivot.replace({"Libre": 0, "Ocupado": 1}), cmap="RdYlGn_r", linewidths=0.5, linecolor='gray', cbar=False, ax=ax)
    ax.set_title("Mapa de calor de turnos (verde: libre / rojo: ocupado)", fontsize=14)
    st.pyplot(fig)

# --- Vista Timeline por paciente ---
elif vista == "Timeline por paciente":
    st.subheader("⏱️ Timeline de turnos por paciente")

    df_timeline = df_turnos.copy()
    df_timeline["HoraCompleta"] = df_timeline["Datetime"]
    df_timeline["PacienteHora"] = df_timeline["Paciente"] + " - " + df_timeline["Hora"]

    if not df_timeline.empty:
        fig = px.timeline(
            df_timeline,
            x_start="HoraCompleta",
            x_end=df_timeline["HoraCompleta"] + pd.Timedelta(minutes=59),
            y="Paciente",
            color="Paciente",
            hover_data=["Fecha", "Hora", "Email", "Observaciones"]
        )
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay turnos cargados para mostrar.")
