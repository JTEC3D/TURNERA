
import streamlit as st
import sqlite3
import os
import pandas as pd
import calendar
from datetime import datetime, timedelta
import plotly.graph_objects as go

st.set_page_config(page_title="Turnera - Calendario Visual", layout="wide")

# Configuración base de datos
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

def obtener_turnos():
    c.execute("SELECT * FROM turnos ORDER BY fecha, hora")
    return c.fetchall()

# Obtener turnos
df = pd.DataFrame(obtener_turnos(), columns=["ID", "Paciente", "Fecha", "Hora", "Observaciones"])
df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")

# Generar calendario visual
st.title("📅 Vista mensual de turnos estilo calendario")

hoy = datetime.today()
year, month = hoy.year, hoy.month
primer_dia_mes = datetime(year, month, 1)
dia_inicio = primer_dia_mes - timedelta(days=primer_dia_mes.weekday())  # lunes anterior

dias = []
x_pos = []
y_pos = []
hover_texts = []

for semana in range(6):
    for dia in range(7):
        fecha_actual = dia_inicio + timedelta(days=semana * 7 + dia)
        dias.append(str(fecha_actual.day))
        x_pos.append(dia)
        y_pos.append(-semana)
        turnos_dia = df[df["Fecha"].dt.date == fecha_actual.date()]
        if not turnos_dia.empty:
            detalle = "<br>".join(f"{row['Hora']} - {row['Paciente']}" for _, row in turnos_dia.iterrows())
            hover_texts.append(f"{fecha_actual.strftime('%d/%m/%Y')}<br>{detalle}")
        else:
            hover_texts.append(fecha_actual.strftime('%d/%m/%Y'))

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=x_pos,
    y=y_pos,
    mode="text",
    text=dias,
    textfont=dict(size=16),
    hoverinfo="text",
    hovertext=hover_texts,
))

fig.update_layout(
    title=f"Turnos de {calendar.month_name[month]} {year}",
    xaxis=dict(
        tickmode="array",
        tickvals=list(range(7)),
        ticktext=["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
        showgrid=False,
        zeroline=False
    ),
    yaxis=dict(showgrid=False, zeroline=False, visible=False),
    height=450,
    margin=dict(t=10, b=10),
    plot_bgcolor="white"
)

st.plotly_chart(fig, use_container_width=True)
