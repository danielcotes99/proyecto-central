import streamlit as st
import sys, os
import pandas as pd
import base64
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database import cargar_registros


st.set_page_config(page_title="REGISTRAR CICLO ABORTADO", page_icon="❌", layout="wide")


st.markdown("""
<style>
header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #0f2537; }
    [data-testid="stSidebar"] * { color: #e0f0ff !important; }
    .titulo-pagina {
        background:   #e0f0ff;
        color:  #0f2537;
        font-size: 2rem;
        font-weight: 700;
        border-left: 5px solid #1976d2;
        padding-left: 16px;
        margin-bottom: 4px;
    }
    .subtitulo {  
        color: #0E1117;
        font-size: 1rem;
        font-weight: 700;
        padding-left: 21px;
        margin-bottom: 24px; 
    }
    
     [data-testid="stWidgetLabel"] p {
    font-size: 15px !important;
    font-weight: 700;
    color: #0f2537;
    }
    .warning-box {
        background-color: #fff3e0;
        border-left: 4px solid #ff9800;
        padding: 15px;
        margin: 20px 0;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

def get_base64(file):
    try:
        with open(file, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return ""

# Cargar imágenes si existen
logo = get_base64("logo.png")
bg = get_base64("fondo.jpg")

if logo and bg:
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
        [data-testid="stSidebar"] * {{ color: #e0f0ff !important; }}

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

st.markdown('<div class="titulo-pagina">❌ REGISTRAR CICLO ABORTADO</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitulo">Marca ciclos completos como cancelados de forma masiva</div>', unsafe_allow_html=True)

# Cargar datos
df = cargar_registros()

if df.empty:
    st.warning("No hay registros en la base de datos.")
    st.stop()

# Convertir fecha a datetime
df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce").dt.normalize()

# ─── SECCIÓN: SELECCIÓN DE CICLO ────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="titulo-pagina">🎯 Paso 1: Seleccionar carga a cancelar</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    # Fecha
    fechas_disponibles = sorted(df["fecha"].dropna().unique())
    
    if fechas_disponibles:
        fecha_cancelar = st.date_input(
            "📅 Fecha del ciclo",
            value=fechas_disponibles[-1],  # Última fecha por defecto
            min_value=fechas_disponibles[0],
            max_value=fechas_disponibles[-1],
            key="fecha_cancelar"
        )
    else:
        st.error("No hay fechas disponibles")
        st.stop()
fecha_cancelar = pd.to_datetime(fecha_cancelar).normalize()
with col2:
    # Filtrar máquinas disponibles para la fecha seleccionada
    df_fecha = df[df["fecha"] == fecha_cancelar]
    
    if not df_fecha.empty:
        maquinas_disponibles = sorted(df_fecha["maquina"].dropna().unique().tolist())
        maquina_cancelar = st.selectbox(
            "🔧 Máquina",
            maquinas_disponibles,
            key="maquina_cancelar"
        )
    else:
        st.warning("No hay registros para esta fecha")
        st.stop()

with col3:
    # Filtrar ciclos disponibles para fecha y máquina
    df_fecha_maq = df_fecha[df_fecha["maquina"] == maquina_cancelar]
    
    if not df_fecha_maq.empty:
        # Excluir ciclos ya cancelados
        ciclos_activos = df_fecha_maq[df_fecha_maq["Estado_del_Ciclo"] != "CICLO CANCELADO"]
        
        if not ciclos_activos.empty:
            ciclos_disponibles = sorted(
            pd.to_numeric(ciclos_activos["carga"], errors="coerce")
            .astype("Int64")
            .dropna()
            .unique()
            .tolist()
        )
            ciclo_cancelar = st.selectbox(
                "🔄 carga",
                ciclos_disponibles,
                key="ciclo_cancelar"
            )
        else:
            st.warning("Todas las cargas de esta fecha/máquina ya están canceladass")
            st.stop()
    else:
        st.warning("No hay registros para esta máquina en la fecha seleccionada")
        st.stop()

# ─── SECCIÓN: VISTA PREVIA ──────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="titulo-pagina">🔍 Paso 2: Vista previa de registros afectados</div>', unsafe_allow_html=True)

df["carga"] = pd.to_numeric(df["carga"], errors="coerce").astype("Int64")
fecha_cancelar = pd.to_datetime(fecha_cancelar).normalize()
registros_a_cancelar = df[
    (df["fecha"] == fecha_cancelar) &
    (df["maquina"] == maquina_cancelar) &
    (df["carga"] == ciclo_cancelar)
]

# Tabla de vista previa
st.markdown('<div class="subtitulo">📊 Detalles de los registros</div>', unsafe_allow_html=True)

# Columnas importantes para mostrar
columnas_mostrar = ["id", "lote", "detalle", "operario", "cantidad", "fecha", "hora", "carga"]
columnas_disponibles = [col for col in columnas_mostrar if col in registros_a_cancelar.columns]

st.dataframe(
    registros_a_cancelar[columnas_disponibles],
    use_container_width=True,
    hide_index=True
)

# ─── SECCIÓN: CONFIRMACIÓN ──────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="titulo-pagina">⚡ Paso 3: Confirmar ciclo abortado</div>', unsafe_allow_html=True)

# Checkbox de confirmación
confirmacion = st.checkbox(
    f"✅ Confirmo que quiero cancelar el ciclo **{ciclo_cancelar}** de la máquina **{maquina_cancelar}** del **{fecha_cancelar.strftime('%d/%m/%Y')}** ({len(registros_a_cancelar)} registros)",
    key="confirmacion_cancelar"
)

col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])

with col_btn1:
    if st.button(
        "❌ CANCELAR CICLO",
        type="primary",
        disabled=not confirmacion,
        use_container_width=True
    ):
        try:
            import sqlite3
            conn = sqlite3.connect("esterilizacion.db")
            cursor = conn.cursor()
            
            # Actualizar columna ciclo para todos los registros
            ids_afectados = registros_a_cancelar["id"].tolist()
            
            for id_reg in ids_afectados:
                cursor.execute("""
                    UPDATE registros 
                    SET  Estado_del_Ciclo = 'CICLO CANCELADO'
                    WHERE id = ?
                """, (id_reg,))
            
            conn.commit()
            conn.close()
            
            # Mensaje de éxito
            st.success(f"""
            ✅ **Ciclo cancelado exitosamente**
            
            - **Registros afectados:** {len(ids_afectados)}
            - **Fecha:** {fecha_cancelar.strftime('%d/%m/%Y')}
            - **Máquina:** {maquina_cancelar}
            - **Ciclo original:** {ciclo_cancelar}
            - **Nuevo estado:** CICLO CANCELADO
            """)
            
            st.balloons()
            
            # Log de la acción (opcional - podrías guardar esto en una tabla de logs)
            st.info(f"📝 Acción registrada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Esperar antes de recargar
            import time
            time.sleep(2)
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Error al cancelar ciclo: {e}")
            st.error("Por favor, contacta al administrador del sistema.")

with col_btn2:
    if st.button("🔄 Limpiar selección", use_container_width=True):
        st.rerun()

# ─── SECCIÓN: HISTORIAL DE CICLOS CANCELADOS ────────────────────────────────
st.markdown("---")
st.markdown('<div class="titulo-pagina">📜 Historial de ciclos abortados</div>', unsafe_allow_html=True)

with st.expander("Ver ciclos abortados", expanded=False):
    # Filtrar registros con ciclos cancelados
    ciclos_cancelados = df[df["Estado_del_Ciclo"] == "CICLO CANCELADO"]
    
    if not ciclos_cancelados.empty:
        # Agrupar por fecha y máquina
        resumen_cancelados = ciclos_cancelados.groupby(
            ["fecha", "maquina"]
        ).size().reset_index(name="cantidad_registros")
        
        st.markdown(f"**Total de registros con ciclos abortados:** {len(ciclos_cancelados)}")
        
        st.dataframe(
            resumen_cancelados.sort_values("fecha", ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                "fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                "maquina": "Máquina",
                "cantidad_registros": "Registros Cancelados"
            }
        )
        
        # Opción de exportar
        if st.button("📥 Exportar historial completo"):
            import io
            buffer = io.BytesIO()
            ciclos_cancelados.to_excel(buffer, index=False, engine="openpyxl")
            
            st.download_button(
                "📥 Descargar Excel",
                data=buffer.getvalue(),
                file_name=f"ciclos_cancelados_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.info("No hay ciclos abortados en el sistema.")
