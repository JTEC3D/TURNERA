
import streamlit as st
import sqlite3
import os
import pandas as pd
from datetime import datetime, timedelta, time

st.set_page_config(page_title="Turnera Final Completa", layout="wide")

# --- Base de datos ---
db_path = os.path.join(os.path.dirname(__file__), "turnos.db")
conn = sqlite3.connect(db_path, check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS turnos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paciente TEXT,
    fecha TEXT,
    hora TEXT,
    observaciones TEXT
)''')
conn.commit()

c.execute("PRAGMA table_info(turnos)")
columnas = [col[1] for col in c.fetchall()]
if "email" not in columnas:
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
    horarios_m = [f"{h:02d}:00" for h in list(range(7, 12))]
    horarios_t = [f"{h:02d}:00" for h in list(range(15, 21))]
    turnos = []
    for d in range(6):  # lunes a sábado
        dia = desde + timedelta(days=d)
        if dia.weekday() < 5:  # lunes a viernes
            for h in horarios_m + horarios_t:
                turnos.append({"Fecha": dia.date(), "Hora": h})
        elif dia.weekday() == 5:  # sábado
            for h in horarios_m:
                turnos.append({"Fecha": dia.date(), "Hora": h})
    return pd.DataFrame(turnos)

dias_es = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

# --- Interfaz principal ---
st.title("🧠 Turnera Final con Exportación")

# --- Formulario de carga ---
st.subheader("📅 Agendar nuevo turno")

# Día de la semana seleccionado
fecha_input = st.date_input("Fecha del turno")
dia_semana = fecha_input.weekday()

horarios_validos = []
if dia_semana < 5:  # lunes a viernes
    horarios_validos = list(range(7, 12)) + list(range(15, 21))
elif dia_semana == 5:  # sábado
    horarios_validos = list(range(7, 12))

horario_seleccionado = st.selectbox("Hora del turno", [time(h, 0) for h in horarios_validos])

with st.form("form_turno"):
    paciente = st.text_input("Nombre del paciente")
    email = st.text_input("Correo electrónico")
    observaciones = st.text_area("Observaciones")
    enviar = st.form_submit_button("Guardar turno")

if enviar:
    if paciente and email and observaciones:
        agregar_turno(paciente, email, fecha_input.isoformat(), horario_seleccionado.strftime("%H:%M"), observaciones)
        st.success("Turno agendado correctamente.")
        st.session_state["turno_seleccionado"] = None
    else:
        st.warning("Por favor, completá todos los campos.")

# --- Mostrar vista semanal ---
df_ocupados = obtener_turnos()
df_ocupados["Fecha"] = pd.to_datetime(df_ocupados["Fecha"])

def mostrar_vista_semanal(titulo, desde, key_prefix):
    st.subheader(titulo)
    df_disp = generar_turnos_disponibles(desde)
    horas = sorted(df_disp["Hora"].unique())
    dias = sorted(df_disp["Fecha"].unique())

    header_cols = st.columns(len(dias) + 1)
    header_cols[0].markdown("**Hora**")
    for i, dia in enumerate(dias):
        dia_nombre = dias_es[dia.weekday()]
        header_cols[i + 1].markdown(f"**{dia_nombre} {dia.strftime('%d/%m')}**")

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

hoy = datetime.today()
mostrar_vista_semanal("📆 Semana actual", hoy - timedelta(days=hoy.weekday()), "actual")
mostrar_vista_semanal("📆 Semana siguiente", hoy - timedelta(days=hoy.weekday()) + timedelta(days=7), "siguiente")

# --- Editor de turno seleccionado ---
if st.session_state.get("turno_seleccionado"):
    turno = st.session_state["turno_seleccionado"]
    st.markdown("---")
    st.subheader("✏️ Editar turno seleccionado")
    with st.form("editar_turno"):
        nuevo_paciente = st.text_input("Paciente", value=turno["paciente"])
        nuevo_email = st.text_input("Correo electrónico", value=turno["email"])
        nueva_fecha = st.date_input("Fecha", value=turno["fecha"])
        try:
            nueva_hora = st.time_input("Hora", value=datetime.strptime(turno["hora"], "%H:%M").time())
        except:
            nueva_hora = st.time_input("Hora", value=datetime.strptime("07:00", "%H:%M").time())
        nuevas_obs = st.text_area("Observaciones", value=turno["observaciones"])
        guardar = st.form_submit_button("💾 Guardar cambios")
        eliminar = st.form_submit_button("🗑 Eliminar turno")

    if guardar:
        actualizar_turno(turno["id"], nuevo_paciente, nuevo_email, nueva_fecha.isoformat(), nueva_hora.strftime("%H:%M"), nuevas_obs)
        st.success("Turno actualizado correctamente.")
        st.session_state["turno_seleccionado"] = None

    if eliminar:
        eliminar_turno(turno["id"])
        st.warning("Turno eliminado.")
        st.session_state["turno_seleccionado"] = None

# --- Exportar a Excel ---
st.subheader("📤 Exportar turnos")
if not df_ocupados.empty:
    if st.button("Exportar todos los turnos a Excel"):
        df_export = df_ocupados.drop(columns="ID")
        df_export.to_excel("turnos_exportados.xlsx", index=False)
        with open("turnos_exportados.xlsx", "rb") as f:
            st.download_button("Descargar Excel", data=f, file_name="turnos_exportados.xlsx")
else:
    st.info("No hay turnos cargados.")
