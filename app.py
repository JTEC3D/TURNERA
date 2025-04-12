
import streamlit as st
import sqlite3
import os
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Turnera - Tabla Estética", layout="wide")

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

# Interfaz
st.title("🗓️ Turnera - Tabla Semanal Estética")

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
        st.success("✅ Turno guardado correctamente.")
    else:
        st.warning("⚠️ Completá todos los campos.")

# Vista semanal en tabla
st.subheader("📅 Tabla semanal de turnos (2 semanas)")

df = obtener_turnos()
df = df.dropna()

hoy = datetime.today().date()
semanas = [hoy - timedelta(days=hoy.weekday()) + timedelta(days=7 * i) for i in range(2)]
dias = [sem + timedelta(days=d) for sem in semanas for d in range(6)]
dias_labels = [f"<b>{d.strftime('%a %d/%m')}</b>" for d in dias]

horarios = [f"<b>{h:02d}:00</b>" for h in range(7, 12)] + [f"<b>{h:02d}:00</b>" for h in range(15, 21)]
tabla = pd.DataFrame(index=horarios, columns=dias_labels)

for i, d in enumerate(dias):
    col = f"<b>{d.strftime('%a %d/%m')}</b>"
    for h in horarios:
        hora_limpia = h.replace("<b>", "").replace("</b>", "")
        turno = df[(df["Fecha"] == d) & (df["Hora"] == hora_limpia)]
        if not turno.empty:
            tabla.loc[h, col] = turno.iloc[0]["Paciente"]
        else:
            tabla.loc[h, col] = "Libre"

# Estilos
def estilo_tabla(df):
    estilos = []
    colores = ["#FFF8DC", "#FFFAE6"]  # dos tonos pastel amarillos
    for i in range(len(df)):
        estilo_fila = [{'background-color': colores[i % 2], 'text-align': 'center'} for _ in df.columns]
        estilos.append(estilo_fila)
    return pd.DataFrame(estilos, columns=df.columns)

st.write("Visualización semanal (actual + siguiente):")

st.dataframe(tabla.style
             .apply(estilo_tabla, axis=None)
             .set_properties(**{'text-align': 'center'})
             .set_table_styles([{
                 'selector': 'th',
                 'props': [('font-weight', 'bold'), ('text-align', 'center')]
             }]),
             use_container_width=True,
             height=480)

# Exportación
st.subheader("📤 Exportar turnos")
if not df.empty:
    export = df.drop(columns=["ID"])
    export.to_excel("turnos_exportados.xlsx", index=False)
    with open("turnos_exportados.xlsx", "rb") as f:
        st.download_button("Descargar Excel", f, "turnos_exportados.xlsx")
else:
    st.info("No hay turnos para exportar.")
