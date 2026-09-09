import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from database import init_db, cargar_registros
import base64
import pandas as pd

st.set_page_config(
    page_title="Sistema de Esterilización",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)
def get_base64(file):
    with open(file, "rb") as f:
        return base64.b64encode(f.read()).decode()
logo = get_base64("logo.png")
bg = get_base64("fondo.jpg")



# CSS personalizado
st.markdown("""
<style>
header {
    background-color: #2E7D32;
}
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<style>

[data-testid="stSidebar"] {{
    background-color: #0f2537;
    background-image: url("data:image/png;base64,{logo}");
    background-repeat: no-repeat;
    background-position: center 120%;
    background-size: 420px;
    position: relative;
}}

[data-testid="stSidebar"] * {{
    color: #e0f0ff !important;
}}

.metric-card {{
    background: linear-gradient(135deg, #0f2537, #1a3a52);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    border: 1px solid #1e5080;
    color: white;
}}

.metric-card h2 {{
    color: #4fc3f7;
    font-size: 2.5rem;
    margin: 0;
}}

.metric-card p {{
    color: #90caf9;
    margin: 4px 0 0;
    font-size: 0.9rem;
}}

.titulo-principal {{
    background: linear-gradient(135deg, #0f2537, #1a3a52);
    color:  #90caf9;
    font-size: 2rem;
    font-weight: 700;
    border-left: 5px solid #1976d2;
    padding-left: 16px;
    margin-bottom: 4px;
}}

.subtitulo {{
    color: #0E1117;
    font-size: 1rem;
    font-weight: 700;
    padding-left: 21px;
    margin-bottom: 24px;
}}

.sidebar-logo {{
    position: absolute;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    width: 160px;
    opacity: 0.9;
}}
.stApp {{
        background-image: url("data:image/png;base64,{bg}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
.stApp::before {{
    content: "";
    position: fixed;
    inset: 0;
    background: rgba(255,255,255,0.3);
}}

</style>


""", unsafe_allow_html=True)


init_db()

st.markdown('<div class="titulo-principal">🧪CLEAR - Sistema de Esterilización</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitulo">Panel principal — control y trazabilidad de procesos</div>', unsafe_allow_html=True)

# Métricas rápidas
df = cargar_registros()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <h2>{len(df)}</h2>
        <p>Total de registros</p>
    </div>""", unsafe_allow_html=True)

with col2:
    sedes = df["sede"].nunique() if not df.empty else 0
    st.markdown(f"""
    <div class="metric-card">
        <h2>{sedes}</h2>
        <p>Sedes registradas</p>
    </div>""", unsafe_allow_html=True)

with col3:
    hoy = df[df["fecha"] == str(df["fecha"].max())] if not df.empty else df
    st.markdown(f"""
    <div class="metric-card">
        <h2>{len(hoy)}</h2>
        <p>Registros hoy</p>
    </div>""", unsafe_allow_html=True)

with col4:
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

    hoy = pd.Timestamp.today().normalize()

    df_hoy = df[df["fecha"].dt.normalize() == hoy]

    cantidad = int(pd.to_numeric(df_hoy["cantidad"], errors="coerce").sum() or 0)

    st.markdown(f"""
    <div class="metric-card">
        <h2>{cantidad}</h2>
        <p>Paquetes procesados hoy</p>
    </div>""", unsafe_allow_html=True)

st.markdown("---")

# Últimos registros
st.subheader("📋 Últimos registros ingresados")
if df.empty:
    st.info("Aún no hay registros. Ve a **📝 Nuevo Registro** para agregar el primero.")
else:
    cols_mostrar = ["id", "fecha", "hora", "sede", "operario", "maquina", "carga", "tipo"]
    st.dataframe(df[cols_mostrar].tail(10), use_container_width=True, hide_index=True)

# Navegación rápida
st.markdown("---")
st.subheader("🚀 Accesos rápidos")
c1, c2, c3 = st.columns(3)
with c1:
    st.page_link("pages/1_Nuevo_Registro.py", label="📝 Ingresar nuevo registro", use_container_width=True)
with c2:
    st.page_link("pages/2_Visualizar_Datos.py", label="📊 Ver y editar datos", use_container_width=True)
with c3:
    st.page_link("pages/5_REGISTRAR_CARGA_ABORTADA.py", label="❌ Registrar carga abortada", use_container_width=True)

def get_base64(file):
    with open(file, "rb") as f:
        return base64.b64encode(f.read()).decode()
