import streamlit as st
import sys, os
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database import cargar_registros

st.set_page_config(page_title="Dashboard", page_icon="📈", layout="wide")

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #0f2537; }
    [data-testid="stSidebar"] * { color: #e0f0ff !important; }
    .titulo-pagina {
        color: #0f2537; font-size: 1.8rem; font-weight: 700;
        border-left: 5px solid #1976d2; padding-left: 16px; margin-bottom: 4px;
    }
    .subtitulo { color: #546e7a; padding-left: 21px; margin-bottom: 24px; }
    .kpi-box {
        background: linear-gradient(135deg, #0f2537, #1a3a52);
        border-radius: 10px; padding: 16px; text-align: center;
        border: 1px solid #1e5080;
    }
    .kpi-box h3 { color: #4fc3f7; font-size: 2rem; margin: 0; }
    .kpi-box p  { color: #90caf9; margin: 4px 0 0; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="titulo-pagina">📈 Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitulo">Análisis visual de los procesos de esterilización</div>', unsafe_allow_html=True)

df = cargar_registros()

if df.empty:
    st.info("No hay datos para mostrar. Ve a **📝 Nuevo Registro** para comenzar.")
    st.stop()

# Convertir fecha
df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

# ─── KPIs ───────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
kpis = [
    (len(df),                          "Total registros"),
    (df["sede"].nunique(),             "Sedes"),
    (df["operario"].nunique(),         "Operarios"),
    (int(df["cantidad"].sum()),        "Unidades procesadas"),
    (df["ciclo"].nunique(),            "Ciclos únicos"),
]
for col, (val, label) in zip([c1, c2, c3, c4, c5], kpis):
    with col:
        st.markdown(f'<div class="kpi-box"><h3>{val}</h3><p>{label}</p></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── GRÁFICAS FILA 1 ────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("Registros por sede")
    fig = px.bar(
        df.groupby("sede").size().reset_index(name="cantidad"),
        x="sede", y="cantidad", color="sede",
        color_discrete_sequence=px.colors.sequential.Blues_r
    )
    fig.update_layout(showlegend=False, plot_bgcolor="white", xaxis_title="", yaxis_title="Registros")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Distribución por tipo de material")
    fig2 = px.pie(
        df.groupby("tipo").size().reset_index(name="cantidad"),
        names="tipo", values="cantidad",
        color_discrete_sequence=px.colors.sequential.Blues_r,
        hole=0.4
    )
    fig2.update_layout(showlegend=True)
    st.plotly_chart(fig2, use_container_width=True)

# ─── GRÁFICAS FILA 2 ────────────────────────────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    st.subheader("Evolución de registros en el tiempo")
    df_tiempo = df.groupby(df["fecha"].dt.to_period("D").astype(str)).size().reset_index(name="registros")
    fig3 = px.line(df_tiempo, x="fecha", y="registros", markers=True,
                   color_discrete_sequence=["#1976d2"])
    fig3.update_layout(plot_bgcolor="white", xaxis_title="Fecha", yaxis_title="Registros")
    st.plotly_chart(fig3, use_container_width=True)

with col4:
    st.subheader("Registros por operario")
    top_op = df.groupby("operario").size().reset_index(name="registros").sort_values("registros", ascending=True).tail(10)
    fig4 = px.bar(top_op, y="operario", x="registros", orientation="h",
                  color="registros", color_continuous_scale="Blues")
    fig4.update_layout(plot_bgcolor="white", showlegend=False, xaxis_title="Registros", yaxis_title="")
    st.plotly_chart(fig4, use_container_width=True)

# ─── GRÁFICA FILA 3: Controles de calidad ───────────────────────────────────
st.markdown("---")
st.subheader("🔬 Resumen de controles de calidad")

pruebas = ["prueba_temperatura", "prueba_proteinas", "prueba_luminiscencia",
           "prueba_biologica", "indicador_quimico", "indicador_externo"]

labels_pruebas = ["Temperatura", "Proteínas", "Luminiscencia",
                  "Biológica", "Indicador Químico", "Indicador Externo"]

aprobados = []
rechazados = []
pendientes = []

for col in pruebas:
    if col in df.columns:
        aprobados.append(df[col].str.contains("Aprobado", na=False).sum())
        rechazados.append(df[col].str.contains("Rechazado", na=False).sum())
        pendientes.append(df[col].str.contains("Pendiente", na=False).sum())
    else:
        aprobados.append(0); rechazados.append(0); pendientes.append(0)

fig5 = go.Figure(data=[
    go.Bar(name="✅ Aprobado",  x=labels_pruebas, y=aprobados,  marker_color="#43a047"),
    go.Bar(name="❌ Rechazado", x=labels_pruebas, y=rechazados, marker_color="#e53935"),
    go.Bar(name="⏳ Pendiente", x=labels_pruebas, y=pendientes, marker_color="#fb8c00"),
])
fig5.update_layout(barmode="group", plot_bgcolor="white",
                   xaxis_title="", yaxis_title="Cantidad", legend_title="Resultado")
st.plotly_chart(fig5, use_container_width=True)
