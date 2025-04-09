
import streamlit as st
import sqlite3
import os
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import calendar

st.set_page_config(page_title="Gestión de Turnos", layout="wide")

# Base de datos
db_path = os.path.join(os.path.dirname(__file__), "turnos.db")
conn = sqlite3.connect(db_path, check_same_thread=False)
c = conn.cursor()

try:
    c.execute('''CREATE TABLE IF NOT EXISTS turnos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paciente TEXT,
        fecha TEXT,
        hora TEXT,
        observaciones TEXT
    )''')
    conn.commit()
except Exception as e:
    st.error(f"Error creando la base de datos: {e}")

# Funciones
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

# Interfaz
st.title("🧠 Gestión de Turnos - Psicología")
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📅 Agendar nuevo turno")
    with st.form("form_turno"):
        paciente = st.text_input("Nombre del paciente")
        fecha = st.date_input("Fecha del turno")
        hora = st.time_input("Hora del turno")
        observaciones = st.text_area("Observaciones")
        enviar = st.form_submit_button("Guardar turno")

    if enviar:
        if paciente and observaciones:
            agregar_turno(paciente, fecha.isoformat(), hora.strftime("%H:%M"), observaciones)
            st.success("Turno agendado correctamente")
        else:
            st.warning("Por favor, completá el nombre del paciente y observaciones.")

# Obtener datos
try:
    turnos = obtener_turnos()
    df = pd.DataFrame(turnos, columns=["ID", "Paciente", "Fecha", "Hora", "Observaciones"])
    df["Fecha"] = pd.to_datetime(df["Fecha"])
except Exception as e:
    st.error(f"No se pudieron obtener los turnos: {e}")
    df = pd.DataFrame(columns=["ID", "Paciente", "Fecha", "Hora", "Observaciones"])

# Calendario interactivo
with col2:
    st.subheader("🗓️ Turnos del mes")
    hoy = datetime.today()
    year, month = hoy.year, hoy.month
    _, last_day = calendar.monthrange(year, month)
    dias_mes = pd.date_range(f"{year}-{month:02d}-01", f"{year}-{month:02d}-{last_day}")
    eventos = df[df["Fecha"].dt.month == month]

    if not eventos.empty:
        tooltip = []
        color = []
        for day in dias_mes:
            turnos_dia = eventos[eventos["Fecha"].dt.date == day.date()]
            if not turnos_dia.empty:
                detalles = [f"• {row['Hora']} - {row['Paciente']}" for _, row in turnos_dia.iterrows()]
                tooltip.append(f"{day.strftime('%d/%m/%Y')}<br>" + "<br>".join(detalles))
                color.append(1)
            else:
                tooltip.append(day.strftime('%d/%m/%Y'))
                color.append(0)

        fig = go.Figure(data=go.Heatmap(
            z=[color],
            x=[d.day for d in dias_mes],
            y=[""],
            text=[tooltip],
            hoverinfo="text",
            showscale=False,
            colorscale=[[0, 'white'], [1, 'lightblue']]
        ))

        fig.update_layout(
            height=200,
            margin=dict(t=0, b=0),
            yaxis=dict(showticklabels=False),
            xaxis=dict(title=f"{calendar.month_name[month]} {year}")
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay turnos agendados este mes.")

# Filtro por fecha
st.subheader("🔎 Turnos por fecha")
fecha_filtro = st.date_input("Seleccionar fecha", datetime.today())
filtrados = df[df["Fecha"].dt.date == fecha_filtro]

if not filtrados.empty:
    for _, row in filtrados.iterrows():
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

# Exportar
st.subheader("📤 Exportar turnos")
if not df.empty:
    if st.button("Exportar todos los turnos a Excel"):
        df_export = df.drop(columns="ID")
        df_export.to_excel("turnos_exportados.xlsx", index=False)
        with open("turnos_exportados.xlsx", "rb") as f:
            st.download_button("Descargar Excel", data=f, file_name="turnos_exportados.xlsx")
else:
    st.info("No hay datos para exportar.")
