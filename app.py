
import streamlit as st
import sqlite3
import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

st.set_page_config(page_title="Turnera Final Sin Duplicados", layout="wide")

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

# Asegurar columna 'email'
c.execute("PRAGMA table_info(turnos)")
if 'email' not in [col[1] for col in c.fetchall()]:
    c.execute("ALTER TABLE turnos ADD COLUMN email TEXT")
    conn.commit()

# --- Funciones ---
def normalizar_hora(hora_str):
    try:
        return datetime.strptime(hora_str.strip()[:5], "%H:%M").strftime("%H:%M")
    except:
        return "07:00"

def agregar_turno(paciente, email, fecha, hora, observaciones):
    hora = normalizar_hora(hora)
    c.execute("INSERT INTO turnos (paciente, email, fecha, hora, observaciones) VALUES (?, ?, ?, ?, ?)",
              (paciente, email, fecha, hora, observaciones))
    conn.commit()

def obtener_turnos():
    c.execute("SELECT * FROM turnos")
    df = pd.DataFrame(c.fetchall(), columns=["ID", "Paciente", "Email", "Fecha", "Hora", "Observaciones"])
    df = df.dropna(subset=["Fecha", "Hora"])
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce").dt.date
    df["Hora"] = df["Hora"].astype(str).str.strip().str[:5].apply(normalizar_hora)
    return df.dropna()

def generar_base_semanal():
    horarios_m = [f"{h:02d}:00" for h in range(7, 12)]
    horarios_t = [f"{h:02d}:00" for h in range(15, 21)]
    base = []
    hoy = datetime.today()
    lunes = hoy - timedelta(days=hoy.weekday())
    for semana in [0, 1]:
        for dia in range(6):  # lunes a sábado
            fecha = (lunes + timedelta(days=dia + semana * 7)).date()
            horarios = horarios_m if fecha.weekday() == 5 else horarios_m + horarios_t
            for h in horarios:
                base.append({"Fecha": fecha, "Hora": h})
    return pd.DataFrame(base)

# --- Interfaz ---
st.title("📅 Turnera Sin Duplicados")

# --- Carga de turnos ---
st.subheader("➕ Agendar nuevo turno")
fecha_turno = st.date_input("Fecha del turno")
dia = fecha_turno.weekday()
horas_validas = list(range(7, 12)) + list(range(15, 21)) if dia < 5 else list(range(7, 12))
hora_turno = st.selectbox("Hora", [f"{h:02d}:00" for h in horas_validas])

with st.form("form_turno"):
    paciente = st.text_input("Nombre del paciente")
    email = st.text_input("Correo electrónico")
    observaciones = st.text_area("Observaciones")
    guardar = st.form_submit_button("Guardar turno")

if guardar:
    if paciente and email and observaciones:
        agregar_turno(paciente, email, fecha_turno.isoformat(), hora_turno, observaciones)
        st.success("Turno agendado correctamente.")
    else:
        st.warning("Completá todos los campos para guardar el turno.")

# --- Cargar turnos y generar mapa ---
df_turnos = obtener_turnos()
df_base = generar_base_semanal()

df_turnos["key"] = df_turnos["Fecha"].astype(str) + "_" + df_turnos["Hora"]
df_base["key"] = df_base["Fecha"].astype(str) + "_" + df_base["Hora"]
df_merge = pd.merge(df_base, df_turnos, on="key", how="left", suffixes=("_base", "_turno"))

# Evitar duplicados en mapa de calor
df_unique = df_merge.drop_duplicates(subset=["Fecha_base", "Hora_base"])

df_unique["estado"] = df_unique["Paciente"].notnull().map({True: "Ocupado", False: "Libre"})

# --- Mapa de calor ---
st.subheader("🟩🟥 Mapa de calor de turnos")

try:
    pivot = df_unique.pivot(index="Hora_base", columns="Fecha_base", values="estado").fillna("Libre")
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.heatmap(pivot.replace({"Libre": 0, "Ocupado": 1}),
                cmap="RdYlGn_r", linewidths=0.5, linecolor='gray', cbar=False, ax=ax)
    ax.set_title("Turnos (verde: libre / rojo: ocupado)", fontsize=14)
    st.pyplot(fig)
except Exception as e:
    st.error(f"No se pudo generar el mapa de calor: {e}")

# --- Exportar turnos ---
st.subheader("📤 Exportar turnos")
if not df_turnos.empty:
    df_export = df_turnos.drop(columns="ID")
    df_export.to_excel("turnos_exportados.xlsx", index=False)
    with open("turnos_exportados.xlsx", "rb") as f:
        st.download_button("Descargar Excel", f, "turnos_exportados.xlsx")
else:
    st.info("No hay turnos cargados para exportar.")
