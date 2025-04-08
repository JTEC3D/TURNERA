
import streamlit as st
import sqlite3
import os
from datetime import datetime
import pandas as pd

# --- Configuración de la app ---
st.set_page_config(page_title="Gestión de Turnos", layout="centered")

# --- Ruta segura para la base de datos ---
db_path = os.path.join(os.path.dirname(__file__), "turnos.db")
conn = sqlite3.connect(db_path, check_same_thread=False)
c = conn.cursor()

# --- Crear tabla de turnos si no existe ---
c.execute('''CREATE TABLE IF NOT EXISTS turnos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paciente TEXT,
                fecha TEXT,
                hora TEXT,
                observaciones TEXT
            )''')
conn.commit()

# --- Funciones auxiliares ---
def agregar_turno(paciente, fecha, hora, observaciones):
    c.execute("INSERT INTO turnos (paciente, fecha, hora, observaciones) VALUES (?, ?, ?, ?)",
              (paciente, fecha, hora, observaciones))
    conn.commit()

def obtener_turnos():
    c.execute("SELECT * FROM turnos ORDER BY fecha, hora")
    return c.fetchall()

def eliminar_turno(turno_id):
    c.execute("DELETE FROM turnos WHERE id = ?", (turno_id,))
    conn.commit()

def actualizar_turno(turno_id, paciente, fecha, hora, observaciones):
    c.execute("UPDATE turnos SET paciente=?, fecha=?, hora=?, observaciones=? WHERE id=?",
              (paciente, fecha, hora, observaciones, turno_id))
    conn.commit()

# --- Interfaz principal ---
st.title("🧠 Gestión de Turnos - Psicología")

st.subheader("📅 Agendar nuevo turno")
with st.form("form_turno"):
    paciente = st.text_input("Nombre del paciente")
    fecha = st.date_input("Fecha del turno")
    hora = st.time_input("Hora del turno")
    observaciones = st.text_area("Observaciones")
    enviar = st.form_submit_button("Guardar turno")

if enviar:
    agregar_turno(paciente, fecha.isoformat(), hora.strftime("%H:%M"), observaciones)
    st.success("Turno agendado correctamente")

st.subheader("🔎 Filtrar turnos por fecha")
fecha_filtro = st.date_input("Seleccionar fecha para ver turnos", datetime.today())

st.subheader("📋 Turnos agendados")
turnos = obtener_turnos()

# Convertir a DataFrame
df = pd.DataFrame(turnos, columns=["ID", "Paciente", "Fecha", "Hora", "Observaciones"])
df["Fecha"] = pd.to_datetime(df["Fecha"])
turnos_filtrados = df[df["Fecha"] == pd.to_datetime(fecha_filtro)]

if not turnos_filtrados.empty:
    for _, row in turnos_filtrados.iterrows():
        with st.expander(f"{row['Paciente']} - {row['Fecha'].date()} {row['Hora']}"):
            nuevo_paciente = st.text_input(f"Paciente_{row['ID']}", value=row['Paciente'], key=f"pac_{row['ID']}")
            nueva_fecha = st.date_input(f"Fecha_{row['ID']}", value=row['Fecha'].date(), key=f"fec_{row['ID']}")
            nueva_hora = st.time_input(f"Hora_{row['ID']}", value=datetime.strptime(row['Hora'], "%H:%M").time(), key=f"hor_{row['ID']}")
            nuevas_obs = st.text_area(f"Observaciones_{row['ID']}", value=row['Observaciones'], key=f"obs_{row['ID']}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Guardar cambios", key=f"edit_{row['ID']}"):
                    actualizar_turno(row['ID'], nuevo_paciente, nueva_fecha.isoformat(), nueva_hora.strftime("%H:%M"), nuevas_obs)
                    st.success("Turno actualizado")
            with col2:
                if st.button("🗑 Eliminar", key=f"del_{row['ID']}"):
                    eliminar_turno(row['ID'])
                    st.warning("Turno eliminado")
else:
    st.info("No hay turnos para la fecha seleccionada.")

# Exportar a Excel
st.subheader("📤 Exportar turnos")
if st.button("Exportar todos los turnos a Excel"):
    df_export = df.drop(columns="ID")
    df_export.to_excel("turnos_exportados.xlsx", index=False)
    with open("turnos_exportados.xlsx", "rb") as f:
        st.download_button("Descargar Excel", data=f, file_name="turnos_exportados.xlsx")
