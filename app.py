
import streamlit as st
import sqlite3
import os
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Turnera Editable", layout="wide")

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

# --- Funciones ---
def obtener_turnos():
    c.execute("SELECT * FROM turnos ORDER BY fecha, hora")
    return pd.DataFrame(c.fetchall(), columns=["ID", "Paciente", "Fecha", "Hora", "Observaciones"])

def eliminar_turno(turno_id):
    c.execute("DELETE FROM turnos WHERE id = ?", (turno_id,))
    conn.commit()

def actualizar_turno(turno_id, paciente, fecha, hora, observaciones):
    c.execute("UPDATE turnos SET paciente=?, fecha=?, hora=?, observaciones=? WHERE id=?",
              (paciente, fecha, hora, observaciones, turno_id))
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

# Obtener datos
df_ocupados = obtener_turnos()
df_ocupados["Fecha"] = pd.to_datetime(df_ocupados["Fecha"])

# Semana actual
hoy = datetime.today()
lunes_actual = hoy - timedelta(days=hoy.weekday())
df_actual = generar_turnos_disponibles(lunes_actual)

st.title("📅 Turnera - Vista Semanal + Editor al Clic")

seleccionado = st.session_state.get("turno_seleccionado", None)

# Mostrar tabla con botones clicables
st.subheader("Semana actual")

horas = sorted(df_actual["Hora"].unique())
dias = sorted(df_actual["Fecha"].unique())
tabla = {}

for hora in horas:
    cols = st.columns(len(dias) + 1)
    cols[0].markdown(f"**{hora}**")
    for i, dia in enumerate(dias):
        match = df_ocupados[(df_ocupados["Fecha"].dt.date == dia) & (df_ocupados["Hora"] == hora)]
        if not match.empty:
            paciente = match.iloc[0]["Paciente"]
            turno_id = match.iloc[0]["ID"]
            if cols[i + 1].button(f"{paciente}", key=f"{hora}_{dia}"):
                st.session_state["turno_seleccionado"] = {
                    "id": turno_id,
                    "paciente": paciente,
                    "fecha": dia,
                    "hora": hora,
                    "observaciones": match.iloc[0]["Observaciones"]
                }
        else:
            cols[i + 1].markdown('<div style="background-color:#d4edda;padding:8px;border-radius:4px;text-align:center">Libre</div>', unsafe_allow_html=True)

# Editor si hay uno seleccionado
if st.session_state.get("turno_seleccionado"):
    turno = st.session_state["turno_seleccionado"]
    st.markdown("---")
    st.subheader("✏️ Editar turno seleccionado")
    with st.form("editar_turno"):
        nuevo_paciente = st.text_input("Paciente", value=turno["paciente"])
        nueva_fecha = st.date_input("Fecha", value=turno["fecha"])
        nueva_hora = st.time_input("Hora", value=datetime.strptime(turno["hora"], "%H:%M").time())
        nuevas_obs = st.text_area("Observaciones", value=turno["observaciones"])
        guardar = st.form_submit_button("💾 Guardar cambios")
        eliminar = st.form_submit_button("🗑 Eliminar turno")

    if guardar:
        actualizar_turno(turno["id"], nuevo_paciente, nueva_fecha.isoformat(), nueva_hora.strftime("%H:%M"), nuevas_obs)
        st.success("Turno actualizado correctamente.")
        st.session_state["turno_seleccionado"] = None
        st.experimental_rerun()

    if eliminar:
        eliminar_turno(turno["id"])
        st.warning("Turno eliminado.")
        st.session_state["turno_seleccionado"] = None
        st.experimental_rerun()
