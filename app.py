
import streamlit as st
import sqlite3
import os
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Turnera", layout="wide")

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

def agregar_turno(paciente, email, fecha, hora, observaciones):
    c.execute("INSERT INTO turnos (paciente, email, fecha, hora, observaciones) VALUES (?, ?, ?, ?, ?)",
              (paciente, email, fecha, hora, observaciones))
    conn.commit()

def actualizar_turno(turno_id, paciente, email, observaciones):
    c.execute("UPDATE turnos SET paciente = ?, email = ?, observaciones = ? WHERE id = ?",
              (paciente, email, observaciones, turno_id))
    conn.commit()

def eliminar_turno(turno_id):
    c.execute("DELETE FROM turnos WHERE id = ?", (turno_id,))
    conn.commit()

def obtener_turnos():
    c.execute("SELECT * FROM turnos")
    df = pd.DataFrame(c.fetchall(), columns=["ID", "Paciente", "Email", "Fecha", "Hora", "Observaciones"])
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce").dt.date
    def limpiar_hora(h):
        try:
            return datetime.strptime(str(h).strip()[:5], "%H:%M").strftime("%H:%M")
        except:
            return None
    df["Hora"] = df["Hora"].apply(limpiar_hora)
    return df.dropna(subset=["Hora"])

# Carga de turno
st.title("📅 Turnera Profesional")
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

if guardar and paciente and email and obs:
    agregar_turno(paciente, email, fecha.isoformat(), hora, obs)
    st.success("✅ Turno guardado correctamente. Recargá para verlo.")

# Vista semanal
st.subheader("📆 Vista semanal (actual y siguiente)")
df = obtener_turnos()

hoy = datetime.today().date()
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
        tabla.loc[h, col] = turno.iloc[0]["Paciente"] if not turno.empty else ""

# Estilo visual tabla
style = "<style>"
style += "td, th { text-align: center; padding: 8px; font-family: sans-serif; }"
style += "table { border-collapse: collapse; width: 100%; }"
style += "th { font-weight: bold; background-color: #f4d35e; }"
style += "tr:nth-child(even) { background-color: #fff8dc; }"
style += "tr:nth-child(odd) { background-color: #fffae6; }"
style += "td { font-size: 14px; }"
for i, col in enumerate(tabla.columns):
    color = "#fef9c3" if i % 2 == 0 else "#fde68a"
    style += f"td:nth-child({i+2}) {{ background-color: {color}; }}"
style += "</style>"
html = style + tabla.to_html(escape=False, index=True)
st.markdown(html, unsafe_allow_html=True)

# Editor robusto por paciente con varios turnos
st.subheader("✏️ Modificar o eliminar turnos")

if not df.empty:
    nombres = df["Paciente"].unique()
    paciente_sel = st.selectbox("Buscar por paciente", nombres)
    turnos_paciente = df[df["Paciente"] == paciente_sel]

    for i, row in turnos_paciente.iterrows():
        with st.expander(f"🕐 {row['Fecha']} {row['Hora']}"):
            with st.form(f"editar_{row['ID']}"):
                nuevo_paciente = st.text_input("Paciente", value=row["Paciente"], key=f"p_{row['ID']}")
                nuevo_email = st.text_input("Email", value=row["Email"], key=f"e_{row['ID']}")
                nueva_obs = st.text_area("Observaciones", value=row["Observaciones"], key=f"o_{row['ID']}")
                col1, col2 = st.columns(2)
                with col1:
                    guardar_cambio = st.form_submit_button("Guardar cambios")
                with col2:
                    eliminar = st.form_submit_button("Eliminar turno")
                if guardar_cambio:
                    actualizar_turno(row["ID"], nuevo_paciente, nuevo_email, nueva_obs)
                    st.success("✅ Turno actualizado. Recargá la app para ver los cambios.")
                if eliminar:
                    eliminar_turno(row["ID"])
                    st.warning("🗑️ Turno eliminado. Recargá la app para ver los cambios.")
else:
    st.info("No hay turnos cargados.")

# Exportar a Excel
st.subheader("📤 Exportar a Excel")
if not df.empty:
    df.drop(columns=["ID"]).to_excel("turnos_exportados.xlsx", index=False)
    with open("turnos_exportados.xlsx", "rb") as f:
        st.download_button("Descargar Excel", f, "turnos_exportados.xlsx")
else:
    st.info("No hay turnos para exportar.")
