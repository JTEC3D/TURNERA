
import streamlit as st
import sqlite3
import os
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Turnera - Diagnóstico de Guardado", layout="wide")

# --- Base de datos ---
db_filename = "turnos.db"
db_path = os.path.join(os.path.dirname(__file__), db_filename)
st.sidebar.markdown(f"📂 Ruta de la base: `{db_path}`")

try:
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
except Exception as e:
    st.error(f"❌ Error al abrir la base de datos: {e}")

# Funciones
def agregar_turno(paciente, email, fecha, hora, observaciones):
    try:
        c.execute("INSERT INTO turnos (paciente, email, fecha, hora, observaciones) VALUES (?, ?, ?, ?, ?)",
                  (paciente, email, fecha, hora, observaciones))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"❌ Error al guardar en la base: {e}")
        return False

def obtener_turnos():
    try:
        c.execute("SELECT * FROM turnos")
        df = pd.DataFrame(c.fetchall(), columns=["ID", "Paciente", "Email", "Fecha", "Hora", "Observaciones"])
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce").dt.date

        def limpiar_hora(h):
            try:
                return datetime.strptime(str(h).strip()[:5], "%H:%M").strftime("%H:%M")
            except:
                return None

        df["Hora"] = df["Hora"].apply(limpiar_hora)
        df = df.dropna(subset=["Hora"])
        return df
    except Exception as e:
        st.error(f"❌ Error al leer la base de datos: {e}")
        return pd.DataFrame()

# --- Interfaz ---
st.title("🛠️ Turnera - Verificación de Guardado")

# Formulario de carga
st.subheader("➕ Cargar nuevo turno")
fecha = st.date_input("Fecha")
dia_semana = fecha.weekday()
horas_validas = list(range(7, 12)) + list(range(15, 21)) if dia_semana < 5 else list(range(7, 12))
hora = st.selectbox("Hora", [f"{h:02d}:00" for h in horas_validas])
with st.form("form_turno"):
    paciente = st.text_input("Paciente")
    email = st.text_input("Email")
    obs = st.text_area("Observaciones")
    guardar = st.form_submit_button("Guardar turno")

if guardar:
    if paciente and email and obs:
        exito = agregar_turno(paciente, email, fecha.isoformat(), hora, obs)
        if exito:
            st.success("✅ Turno guardado correctamente.")
        else:
            st.error("❌ Algo falló al intentar guardar el turno.")
    else:
        st.warning("⚠️ Completá todos los campos.")

# Mostrar contenido real de la base
df = obtener_turnos()

st.subheader("📋 Turnos guardados en la base de datos:")
st.dataframe(df)

if not df.empty:
    st.markdown(f"🎯 Primer turno: **{df.iloc[0]['Fecha']} {df.iloc[0]['Hora']}**")
else:
    st.info("🔍 No se encontraron turnos en la base.")
