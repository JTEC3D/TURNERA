
import streamlit as st
import sqlite3
import os
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Turnera Final - Año Correcto", layout="wide")

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

# Funciones
def agregar_turno(paciente, email, fecha, hora, observaciones):
    c.execute("INSERT INTO turnos (paciente, email, fecha, hora, observaciones) VALUES (?, ?, ?, ?, ?)",
              (paciente, email, fecha, hora, observaciones))
    conn.commit()

def obtener_turnos():
    c.execute("SELECT * FROM turnos")
    df = pd.DataFrame(c.fetchall(), columns=["ID", "Paciente", "Email", "Fecha", "Hora", "Observaciones"])
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce").dt.date
    df["Hora"] = df["Hora"].astype(str).str.strip().str[:5]
    return df

# --- Interfaz ---
st.title("🗓️ Turnera Final - Año Correcto")

# Carga de turnos
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
        agregar_turno(paciente, email, fecha.isoformat(), hora, obs)
        st.success("✅ Turno guardado correctamente. Recargá la página para verlo en la tabla.")
    else:
        st.warning("⚠️ Completá todos los campos.")

# Vista semanal (2 semanas) con año actual
st.subheader("📅 Tabla semanal (actual + siguiente)")

df = obtener_turnos().dropna()
hoy = datetime.today().date()
year_actual = hoy.year
lunes_actual = hoy - timedelta(days=hoy.weekday())
semanas = [lunes_actual + timedelta(weeks=i) for i in range(2)]
dias = [lunes + timedelta(days=j) for lunes in semanas for j in range(6)]
dias_labels = [f"{d.strftime('%a %d/%m')}" for d in dias]
horarios = [f"{h:02d}:00" for h in range(7, 12)] + [f"{h:02d}:00" for h in range(15, 21)]

tabla = pd.DataFrame(index=horarios, columns=dias_labels)
for d in dias:
    col = d.strftime("%a %d/%m")
    for h in horarios:
        turno = df[(df["Fecha"] == d) & (df["Hora"] == h)]
        tabla.loc[h, col] = turno.iloc[0]["Paciente"] if not turno.empty else "Libre"

# Estilos visibles por HTML
html = "<style>td, th { text-align: center; padding: 8px; font-family: sans-serif; }"
html += "table { border-collapse: collapse; width: 100%; }"
html += "th { font-weight: bold; background-color: #f4d35e; }"
html += "tr:nth-child(even) { background-color: #fff8dc; }"
html += "tr:nth-child(odd) { background-color: #fffae6; }"
html += "td { font-size: 14px; }</style>"
html += tabla.to_html(escape=False, index=True)

st.markdown(html, unsafe_allow_html=True)

# Exportación
st.subheader("📤 Exportar turnos")
if not df.empty:
    export = df.drop(columns=["ID"])
    export.to_excel("turnos_exportados.xlsx", index=False)
    with open("turnos_exportados.xlsx", "rb") as f:
        st.download_button("Descargar Excel", f, "turnos_exportados.xlsx")
else:
    st.info("No hay turnos para exportar.")
