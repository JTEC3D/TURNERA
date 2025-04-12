
import streamlit as st
import sqlite3
import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime, timedelta, time

st.set_page_config(page_title="Turnera Final con Mapa de Calor", layout="wide")

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

# Agregar columna 'email' si falta
c.execute("PRAGMA table_info(turnos)")
columnas = [col[1] for col in c.fetchall()]
if "email" not in columnas:
    c.execute("ALTER TABLE turnos ADD COLUMN email TEXT")
    conn.commit()

# --- Funciones ---
def normalizar_hora(hora_str):
    try:
        return datetime.strptime(hora_str.strip(), "%H:%M").strftime("%H:%M")
    except:
        try:
            return datetime.strptime(hora_str.strip(), "%H:%M:%S").strftime("%H:%M")
        except:
            return "07:00"

def agregar_turno(paciente, email, fecha, hora, observaciones):
    hora_str = normalizar_hora(hora)
    c.execute("INSERT INTO turnos (paciente, email, fecha, hora, observaciones) VALUES (?, ?, ?, ?, ?)",
              (paciente, email, fecha, hora_str, observaciones))
    conn.commit()

def obtener_turnos():
    c.execute("SELECT * FROM turnos ORDER BY fecha, hora")
    df = pd.DataFrame(c.fetchall(), columns=["ID", "Paciente", "Email", "Fecha", "Hora", "Observaciones"])
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce").dt.date
    df = df.dropna(subset=["Fecha", "Hora"])
    df["Hora"] = df["Hora"].astype(str).str.strip().str[:5]
    return df

def generar_base_semanal():
    horarios_m = [f"{h:02d}:00" for h in range(7, 12)]
    horarios_t = [f"{h:02d}:00" for h in range(15, 21)]
    base = []
    hoy = datetime.today()
    lunes = hoy - timedelta(days=hoy.weekday())
    for semana in [0, 1]:
        for dia in range(6):  # Lunes a sábado
            fecha = lunes + timedelta(days=dia + semana * 7)
            horas = horarios_m if fecha.weekday() == 5 else horarios_m + horarios_t
            for h in horas:
                base.append({"Fecha": fecha.date(), "Hora": h})
    return pd.DataFrame(base)

def exportar_excel(df):
    df.to_excel("turnos_exportados.xlsx", index=False)
    with open("turnos_exportados.xlsx", "rb") as f:
        st.download_button("Descargar turnos en Excel", f, "turnos_exportados.xlsx")

# --- Interfaz ---
st.title("📅 Turnera Final con Mapa de Calor")

# --- Carga de turnos ---
st.subheader("➕ Agendar nuevo turno")
fecha_turno = st.date_input("Fecha")
dia_semana = fecha_turno.weekday()
horarios_validos = list(range(7, 12)) + list(range(15, 21)) if dia_semana < 5 else list(range(7, 12))
hora_seleccionada = st.selectbox("Hora", [f"{h:02d}:00" for h in horarios_validos])

with st.form("form_turno"):
    paciente = st.text_input("Nombre del paciente")
    email = st.text_input("Correo electrónico")
    observaciones = st.text_area("Observaciones")
    enviar = st.form_submit_button("Guardar turno")

if enviar:
    if paciente and email and observaciones:
        agregar_turno(paciente, email, fecha_turno.isoformat(), hora_seleccionada, observaciones)
        st.success("Turno guardado correctamente.")
    else:
        st.warning("Por favor, completá todos los campos.")

# --- Vista semanal con mapa de calor ---
st.subheader("🟩🟥 Mapa de Calor - Turnos Semanales")

df_turnos = obtener_turnos()
df_base = generar_base_semanal()
df_base["key"] = df_base["Fecha"].astype(str) + " " + df_base["Hora"]
df_turnos["key"] = df_turnos["Fecha"].astype(str) + " " + df_turnos["Hora"]
df_merge = pd.merge(df_base, df_turnos, on="key", how="left")
df_merge["estado"] = df_merge["Paciente"].notnull().map({True: "Ocupado", False: "Libre"})

pivot = df_merge.pivot(index="Hora", columns="Fecha", values="estado").fillna("Libre")

fig, ax = plt.subplots(figsize=(12, 6))
sns.heatmap(pivot.replace({"Libre": 0, "Ocupado": 1}), cmap="RdYlGn_r", linewidths=0.5, linecolor='gray', cbar=False, ax=ax)
ax.set_title("Mapa de calor de turnos (verde: libre / rojo: ocupado)", fontsize=14)
st.pyplot(fig)

# --- Exportar ---
st.subheader("📤 Exportar turnos")
if not df_turnos.empty:
    exportar_excel(df_turnos.drop(columns="ID"))
else:
    st.info("No hay turnos para exportar.")
