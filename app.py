
import streamlit as st
import sqlite3
import os
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Turnera Mejorada", layout="wide")

# --- Base de datos ---
db_path = os.path.join(os.path.dirname(__file__), "turnos.db")
conn = sqlite3.connect(db_path, check_same_thread=False)
c = conn.cursor()

# Crear tabla si no existe
c.execute('''CREATE TABLE IF NOT EXISTS turnos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paciente TEXT,
    fecha TEXT,
    hora TEXT,
    observaciones TEXT
)''')
conn.commit()

# Verificar y agregar columna 'email' si no existe
c.execute("PRAGMA table_info(turnos)")
columns = [col[1] for col in c.fetchall()]
if "email" not in columns:
    c.execute("ALTER TABLE turnos ADD COLUMN email TEXT")
    conn.commit()

# --- Funciones ---
def agregar_turno(paciente, email, fecha, hora, observaciones):
    c.execute("INSERT INTO turnos (paciente, email, fecha, hora, observaciones) VALUES (?, ?, ?, ?, ?)",
              (paciente, email, fecha, hora, observaciones))
    conn.commit()

def obtener_turnos():
    c.execute("SELECT * FROM turnos ORDER BY fecha, hora")
    return pd.DataFrame(c.fetchall(), columns=["ID", "Paciente", "Email", "Fecha", "Hora", "Observaciones"])

def eliminar_turno(turno_id):
    c.execute("DELETE FROM turnos WHERE id = ?", (turno_id,))
    conn.commit()

def actualizar_turno(turno_id, paciente, email, fecha, hora, observaciones):
    c.execute("UPDATE turnos SET paciente=?, email=?, fecha=?, hora=?, observaciones=? WHERE id=?",
              (paciente, email, fecha, hora, observaciones, turno_id))
    conn.commit()

def generar_turnos_disponibles(desde):
    horarios = [f"{h:02d}:00" for h in list(range(7, 12)) + list(range(15, 21))]
    turnos = []
    for d in range(6):  # lunes a sábado
        dia = desde + timedelta(days=d)
        for hora in horarios:
            if dia.weekday() == 5 and int(hora[:2]) >= 12:
                continue
            turnos.append({"Fecha": dia.date(), "Hora": hora})
    return pd.DataFrame(turnos)

# --- Inicio ---
st.title("🧠 Turnera Mejorada Final (con auto-fix de base de datos)")

# --- Formulario de carga ---
st.subheader("📅 Agendar nuevo turno")
with st.form("form_turno"):
    paciente = st.text_input("Nombre del paciente")
    email = st.text_input("Correo electrónico")
    fecha = st.date_input("Fecha del turno")
    hora = st.time_input("Hora del turno")
    observaciones = st.text_area("Observaciones")
    enviar = st.form_submit_button("Guardar turno")

if enviar:
    if paciente and email and observaciones:
        agregar_turno(paciente, email, fecha.isoformat(), hora.strftime("%H:%M"), observaciones)
        st.success("Turno agendado correctamente")
    else:
        st.warning("Por favor, completá todos los campos obligatorios.")

# --- Cargar datos y mostrar vista semanal ---
df_ocupados = obtener_turnos()
df_ocupados["Fecha"] = pd.to_datetime(df_ocupados["Fecha"])

# Vista semanal
def mostrar_vista_semanal(titulo, desde, key_prefix):
    st.subheader(titulo)
    df_disponibles = generar_turnos_disponibles(desde)
    horas = sorted(df_disponibles["Hora"].unique())
    dias = sorted(df_disponibles["Fecha"].unique())

    header_cols = st.columns(len(dias) + 1)
    header_cols[0].markdown("**Hora**")
    for i, dia in enumerate(dias):
        nombre_dia = dia.strftime("%a %d/%m")
        header_cols[i + 1].markdown(f"**{nombre_dia}**")

    for hora in horas:
        cols = st.columns(len(dias) + 1)
        cols[0].markdown(f"**{hora}**")
        for i, dia in enumerate(dias):
            match = df_ocupados[(df_ocupados["Fecha"].dt.date == dia) & (df_ocupados["Hora"] == hora)]
            if not match.empty:
                paciente = match.iloc[0]["Paciente"]
                turno_id = match.iloc[0]["ID"]
                if cols[i + 1].button(f"{paciente}", key=f"{key_prefix}_{hora}_{dia}"):
                    st.session_state["turno_seleccionado"] = {
                        "id": turno_id,
                        "paciente": paciente,
                        "email": match.iloc[0]["Email"],
                        "fecha": dia,
                        "hora": hora,
                        "observaciones": match.iloc[0]["Observaciones"]
                    }
            else:
                cols[i + 1].markdown('<div style="background-color:#d4edda;padding:8px;border-radius:4px;text-align:center">Libre</div>', unsafe_allow_html=True)

# Mostrar ambas semanas
hoy = datetime.today()
mostrar_vista_semanal("📆 Semana actual", hoy - timedelta(days=hoy.weekday()), "actual")
mostrar_vista_semanal("📆 Semana siguiente", hoy - timedelta(days=hoy.weekday()) + timedelta(days=7), "siguiente")

# Editor de turno seleccionado
if st.session_state.get("turno_seleccionado"):
    turno = st.session_state["turno_seleccionado"]
    st.markdown("---")
    st.subheader("✏️ Editar turno seleccionado")
    with st.form("editar_turno"):
        nuevo_paciente = st.text_input("Paciente", value=turno["paciente"])
        nuevo_email = st.text_input("Correo electrónico", value=turno["email"])
        nueva_fecha = st.date_input("Fecha", value=turno["fecha"])
        nueva_hora = st.time_input("Hora", value=datetime.strptime(turno["hora"], "%H:%M").time())
        nuevas_obs = st.text_area("Observaciones", value=turno["observaciones"])
        guardar = st.form_submit_button("💾 Guardar cambios")
        eliminar = st.form_submit_button("🗑 Eliminar turno")

    if guardar:
        actualizar_turno(turno["id"], nuevo_paciente, nuevo_email, nueva_fecha.isoformat(), nueva_hora.strftime("%H:%M"), nuevas_obs)
        st.success("Turno actualizado correctamente.")
        st.session_state["turno_seleccionado"] = None
        st.experimental_rerun()

    if eliminar:
        eliminar_turno(turno["id"])
        st.warning("Turno eliminado.")
        st.session_state["turno_seleccionado"] = None
        st.experimental_rerun()
