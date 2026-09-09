import streamlit as st
import sys, os
import io
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import base64
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database import cargar_registros

st.set_page_config(page_title="Dashboard", page_icon="📈", layout="wide")

def pagina_protegida():
    

    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False

    if not st.session_state.auth_ok:
        password = st.text_input("Ingresa la contraseña", type="password")

        if st.button("Entrar"):
            if password == "Hpp2026/":  # <-- cambia esto
                st.session_state.auth_ok = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta")

        st.stop()

    # Contenido protegido


def generar_excel_indicadores(df, mes_seleccionado):
    df["mes"] = df["fecha"].dt.to_period("M").astype(str)
    df_mes = df[df["mes"] == mes_seleccionado].copy()

    wb = Workbook()
    ws = wb.active
    ws.title = "Indicadores"

    # Estilos
    header_font = Font(name="Arial", bold=True, size=12, color="FFFFFF")
    header_fill = PatternFill("solid", start_color="2F5496")
    label_font = Font(name="Arial", bold=True, size=11)
    value_font = Font(name="Arial", size=11)
    center = Alignment(horizontal="center", vertical="center")
    left = Alignment(horizontal="left", vertical="center")
    thin = Side(style="thin", color="B0B0B0")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # A1: Título
    ws["A1"] = "Indicadores"
    ws["A1"].font = Font(name="Arial", bold=True, size=14, color="FFFFFF")
    ws["A1"].fill = PatternFill("solid", start_color="2F5496")
    ws["A1"].alignment = center
    ws.merge_cells("A1:B1")
    ws.row_dimensions[1].height = 28

    indicadores = [
        "Paquetes esterilizados por vencimiento",
        "Total de paquetes esterilizados",
        "Total de cargas canceladas",
        "Total de cargas realizadas",
        "Total de pruebas biológicas realizadas en autoclave 400A",
        "Total de pruebas biológicas realizadas en autoclave 400B",
        "Total de pruebas biológicas realizadas en Sterrad 100NX",
        "Total de pruebas Bowie-Dick realizadas",
    ]

    # Cálculos en Python (los valores se escriben como números en B)
    # 1. Paquetes vencidos
    val1 = int(df_mes["vencido"].str.upper().eq("SI").sum()) if "vencido" in df_mes.columns else 0

    # 2. Total paquetes esterilizados
    val2 = int(df_mes["cantidad"].sum()) if "cantidad" in df_mes.columns else 0

    # 3. Cargas canceladas (combinaciones únicas de fecha, maquina, carga con CICLO CANCELADO)
    if "Estado_del_Ciclo" in df_mes.columns:
        canceladas = df_mes[df_mes["Estado_del_Ciclo"].str.upper() == "CICLO CANCELADO"]
        val3 = int(canceladas.drop_duplicates(subset=["fecha", "maquina", "carga"]).shape[0])
    else:
        val3 = 0

    # 4. Total cargas realizadas (combinaciones únicas fecha, maquina, carga)
    cols_carga = [c for c in ["fecha", "maquina", "carga"] if c in df_mes.columns]
    val4 = int(df_mes.drop_duplicates(subset=cols_carga).shape[0]) if cols_carga else 0

    # 5. Pruebas biológicas 400A
    if "prueba_biologica" in df_mes.columns and "maquina" in df_mes.columns:
        df_400a = df_mes[df_mes["maquina"].str.upper() == "400A"]
        df_bio_400a = df_400a[df_400a["prueba_biologica"].str.upper() == "SI"]
        val5 = int(df_bio_400a.drop_duplicates(subset=["fecha", "maquina", "carga"]).shape[0])
    else:
        val5 = 0

    # 6. Pruebas biológicas 400B
    if "prueba_biologica" in df_mes.columns and "maquina" in df_mes.columns:
        df_400b = df_mes[df_mes["maquina"].str.upper() == "400B"]
        df_bio_400b = df_400b[df_400b["prueba_biologica"].str.upper() == "SI"]
        val6 = int(df_bio_400b.drop_duplicates(subset=["fecha", "maquina", "carga"]).shape[0])
    else:
        val6 = 0

    # 7. Pruebas biológicas Sterrad 100NX
    if "prueba_biologica" in df_mes.columns and "maquina" in df_mes.columns:
        df_sterrad = df_mes[df_mes["maquina"].str.upper() == "100NX"]
        df_bio_sterrad = df_sterrad[df_sterrad["prueba_biologica"].str.upper() == "SI"]
        val7 = int(df_bio_sterrad.drop_duplicates(subset=["fecha", "maquina", "carga"]).shape[0])
    else:
        val7 = 0

    # 8. Pruebas Bowie-Dick
    if "detalle" in df_mes.columns:
        val8 = int(df_mes["detalle"].str.upper().eq("PRUEBA DE BOWIE DICK (DART TEST)").sum())
    else:
        val8 = 0

    valores = [val1, val2, val3, val4, val5, val6, val7, val8]

    label_fill_odd  = PatternFill("solid", start_color="DCE6F1")
    label_fill_even = PatternFill("solid", start_color="FFFFFF")

    for i, (label, valor) in enumerate(zip(indicadores, valores), start=2):
        fill = label_fill_odd if i % 2 == 0 else label_fill_even
        ws[f"A{i}"] = label
        ws[f"A{i}"].font = label_font
        ws[f"A{i}"].fill = fill
        ws[f"A{i}"].alignment = left
        ws[f"A{i}"].border = border

        ws[f"B{i}"] = valor
        ws[f"B{i}"].font = value_font
        ws[f"B{i}"].fill = fill
        ws[f"B{i}"].alignment = center
        ws[f"B{i}"].border = border
        ws.row_dimensions[i].height = 22

    ws.column_dimensions["A"].width = 58
    ws.column_dimensions["B"].width = 14

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf

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
    .subtitulo { color:  #0f2537; font-size: 1.8rem; font-weight: 700; padding-left: 21px; margin-bottom: 24px; }
    .kpi-box {
        background: linear-gradient(135deg, #0f2537, #1a3a52);
        border-radius: 10px; padding: 16px; text-align: center;
        border: 1px solid #1e5080;
    }
    .kpi-box h3 { color: #4fc3f7; font-size: 2rem; margin: 0; }
    .kpi-box p  { color: #90caf9; margin: 4px 0 0; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)
def get_base64(file):
    with open(file, "rb") as f:
        return base64.b64encode(f.read()).decode()
logo = get_base64("logo.png")
bg = get_base64("fondo.jpg")
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

st.markdown('<div class="titulo-pagina">📈 Indicadores</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitulo">Análisis visual de los procesos de esterilización</div>', unsafe_allow_html=True)

df = cargar_registros()

df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

hoy = pd.Timestamp.today().normalize()

df_hoy = df[df["fecha"].dt.normalize() == hoy]

cantidadhoy = int(pd.to_numeric(df_hoy["cantidad"], errors="coerce").sum() or 0)

df_400A = df[
    (df["fecha"].dt.normalize() == hoy) &
    (df["maquina"] == "400A")
]

ciclo400A = int(pd.to_numeric(df_400A["carga"], errors="coerce").nunique() or 0)

df_400B = df[
    (df["fecha"].dt.normalize() == hoy) &
    (df["maquina"] == "400B")
]

ciclo400B = int(pd.to_numeric(df_400B["carga"], errors="coerce").nunique() or 0)

df_100NX = df[
    (df["fecha"].dt.normalize() == hoy) &
    (df["maquina"] == "100NX")
]

ciclo100NX = int(pd.to_numeric(df_100NX["carga"], errors="coerce").nunique() or 0)



if df.empty:
    st.info("No hay datos para mostrar. Ve a **📝 Nuevo Registro** para comenzar.")
    st.stop()

# Convertir fecha
df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

# ─── KPIs ───────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
kpis = [
    (len(df),                          "Total registros"),
    (ciclo400A,                        "Cargas 400A"),
    (ciclo400B,                        "Cargas 400B"),
    (ciclo100NX,                       "Cargas 100NX"),
    (cantidadhoy,                      "Paquetes procesados hoy")

]
for col, (val, label) in zip([c1, c2, c3, c4, c5], kpis):
    with col:
        st.markdown(f'<div class="kpi-box"><h3>{val}</h3><p>{label}</p></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── GRÁFICAS FILA 1 ────────────────────────────────────────────────────────
df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
df["mes"] = df["fecha"].dt.to_period("M").astype(str)

cols = st.columns(1)

with cols[0]:
    # Asegurar formato interno correcto
    df["mes"] = pd.to_datetime(df["fecha"], errors="coerce").dt.to_period("M").astype(str)

    # Crear lista de meses únicos
    meses = sorted(df["mes"].dropna().unique())

    # Crear etiquetas bonitas
    meses_dict = {
        mes: pd.to_datetime(mes).strftime("%B %Y").capitalize()
        for mes in meses
    }

    # Invertir diccionario para el selectbox
    labels = list(meses_dict.values())
    valores = list(meses_dict.keys())

    # Mes actual
    mes_actual = str(pd.Timestamp.today().to_period("M"))

    if mes_actual in valores:
        index_default = valores.index(mes_actual)
    else:
        index_default = 0

    # Selectbox muestra bonito pero guarda valor real
    mes_label = st.selectbox(
        "Selecciona un mes",
        labels,
        index=index_default
    )

    mes_seleccionado = valores[labels.index(mes_label)]

    # Filtrar
    df_filtrado = df[df["mes"] == mes_seleccionado]
    # Buscar índice del mes actual (si existe)
    excel_buf = generar_excel_indicadores(df, mes_seleccionado)

    st.download_button(
        label="📥 Exportar indicadores a Excel",
        data=excel_buf,
        file_name=f"indicadores_{mes_seleccionado}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ) 

    st.markdown('<div class="subtitulo">PAQUETES ESTERILIZADOS POR MAQUINA</div>', unsafe_allow_html=True)

    # 🔥 convertir y sumar correctamente
    df_group = (
        df_filtrado
        .assign(cantidad=pd.to_numeric(df_filtrado["cantidad"], errors="coerce"))
        .groupby("maquina", as_index=False)["cantidad"]
        .sum()
    )

    fig = px.bar(
        df_group,
        x="maquina",
        y="cantidad",
        color="maquina",
        color_discrete_sequence=px.colors.qualitative.Prism  # mejor para categorías
    )
    fig.update_traces(width=0.5) 
    fig.update_traces(
    texttemplate='%{y}',   # 👈 valor de Y
    textposition='outside'
    )
    fig.update_layout(
        showlegend=False,
        plot_bgcolor="black",
        xaxis_title="Maquina",
        yaxis_title="Paquetes"
    )

    st.plotly_chart(fig, use_container_width=True)
    st.markdown('<div class="subtitulo">DISTRIBUCION POR TIPO DE MATERIAL</div>', unsafe_allow_html=True)
    df_group2 = (
        df_filtrado
        .assign(cantidad=pd.to_numeric(df_filtrado["cantidad"], errors="coerce"))
        .groupby("tipo", as_index=False)["cantidad"]
        .sum()
    )
    fig2 = px.pie(
        df_group2,
        names="tipo", values="cantidad",
        color_discrete_sequence=px.colors.sequential.Turbo,
        hole=0.4
    )
    fig2.update_layout(showlegend=True)
    st.plotly_chart(fig2, use_container_width=True)
    
    st.markdown('<div class="subtitulo">PRUEBAS BIOLOGICAS POR MES</div>', unsafe_allow_html=True)

    df_pb = df_filtrado[
        df_filtrado["prueba_biologica"].astype(str).str.strip().str.upper() == "SI"
    ].copy()

    # Normalizar fecha
    df_pb["fecha"] = pd.to_datetime(df_pb["fecha"], errors="coerce").dt.normalize()

    # 🔥 eliminar duplicados por fecha + carga + maquina
    df_pb_unicos = df_pb.drop_duplicates(subset=["fecha", "carga", "maquina"])

    # Contar
    df_group = df_pb_unicos.groupby("maquina", as_index=False).size()
    df_group = df_group.rename(columns={"size": "prueba_biologica"})

    fig3 = px.bar(
        df_group,
        x="maquina",
        y="prueba_biologica",
        color="maquina",
        color_discrete_sequence=px.colors.qualitative.Prism
    )

    fig3.update_traces(width=0.5) 
    fig3.update_traces(
    texttemplate='%{y}',   # 👈 valor de Y
    textposition='outside'
    )

    fig3.update_layout(
        showlegend=False,
        plot_bgcolor="black",
        xaxis_title="Maquina",
        yaxis_title="Pruebas biológicas"
    )

    st.plotly_chart(fig3, use_container_width=True)

     # 🔥 FILTRO BOWIE DICK
    df_bd = df_filtrado[
        df_filtrado["detalle"].astype(str).str.strip().str.upper() == "PRUEBA DE BOWIE DICK (DART TEST)"
    ]

    st.markdown('<div class="subtitulo">PRUEBA BOWIE DICK POR MAQUINA</div>', unsafe_allow_html=True)

    # 🔥 contar pruebas (no sumar cantidad)
    df_group = (
        df_bd.groupby("maquina", as_index=False)
        .size()
        .rename(columns={"size": "detalle"})
    )

    fig4 = px.bar(
        df_group,
        x="maquina",
        y="detalle",
        color="maquina",
        color_discrete_sequence=px.colors.qualitative.Prism
    )
    fig4.update_traces(width=0.3) 
    fig4.update_traces(
    texttemplate='%{y}',   # 👈 valor de Y
    textposition='outside'
    )

    fig4.update_layout(
        showlegend=False,
        plot_bgcolor="black",
        xaxis_title="detalle",
        yaxis_title="Pruebas Bowie Dick"
    )

    st.plotly_chart(fig4, use_container_width=True)

# ─── GRÁFICAS FILA 2 ────────────────────────────────────────────────────────
col2, col3 = st.columns(2)

with col2:
    st.subheader("Evolución de registros en el tiempo")
    df_tiempo = (
    df.groupby(df["fecha"].dt.to_period("D").astype(str))["cantidad"]
    .sum()
    .reset_index()
)
    fig3 = px.line(df_tiempo, x="fecha", y="cantidad", markers=True,
                   color_discrete_sequence=["#1976d2"])
    fig3.update_layout(plot_bgcolor="white", xaxis_title="Fecha", yaxis_title="Registros")
    st.plotly_chart(fig3, use_container_width=True)

pagina_protegida()
with col3:
    st.subheader("Registros por operario")
    top_op = df_filtrado.groupby("operario").size().reset_index(name="cantidad")

    top_op["cantidad"] = top_op["cantidad"].astype(float)
    # Ajuste especial para DAYAN PINEDA
    top_op.loc[top_op["operario"] == "DAYAN PINEDA", "cantidad"] = (
        top_op.loc[top_op["operario"] == "DAYAN PINEDA", "cantidad"] * 0.64
    )

    top_op = top_op.sort_values("cantidad", ascending=True).tail(10)

    fig4 = px.bar(top_op, y="operario", x="cantidad", orientation="h",
                  color="cantidad", color_continuous_scale="Blues",
                  text="cantidad")

    fig4.update_traces(
        texttemplate='%{text:.2f}',   # muestra el valor con 2 decimales
        textposition='outside'
    )

    fig4.update_layout(plot_bgcolor="white", showlegend=False, xaxis_title="Registros", yaxis_title="")
    st.plotly_chart(fig4, use_container_width=True)
# ─── GRÁFICA FILA 3: Controles de calidad ───────────────────────────────────
