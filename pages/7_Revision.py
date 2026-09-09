import streamlit as st
import sys, os
import io
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sqlite3

import base64
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database import cargar_registros
from datetime import datetime, time, timedelta
from openpyxl.utils import column_index_from_string

db_path = "esterilizacion.db"
def normalizar_hora(valor):
    """
    Convierte el valor crudo de una celda de turno en un objeto datetime.time.
    Soporta: datetime, time, fracción decimal de Excel (0-1), enteros tipo 700/1900,
    y strings tipo '07:00', '7:00 AM', '19', etc.
    Devuelve None si no puede interpretarlo.
    """
    if valor is None:
        return None
 
    if isinstance(valor, datetime):
        return valor.time()
 
    if isinstance(valor, time):
        return valor
 
    if isinstance(valor, (int, float)):
        # Fracción de día típica de Excel (ej. 0.29166 = 07:00)
        if 0 <= valor < 1:
            total_minutos = round(valor * 24 * 60)
            return time(hour=(total_minutos // 60) % 24, minute=total_minutos % 60)
        # Formato tipo 700 -> 07:00, 1900 -> 19:00
        valor_str = str(int(valor)).zfill(4)
        try:
            return time(hour=int(valor_str[:2]) % 24, minute=int(valor_str[2:]))
        except ValueError:
            return None
 
    if isinstance(valor, str):
        valor = valor.strip()
        if not valor:
            return None
        for fmt in (
    "%H:%M",
    "%H:%M:%S",
    "%H:%M:%S.%f",
    "%I:%M %p",
    "%I %p",
):
            try:
                return datetime.strptime(valor, fmt).time()
            except ValueError:
                continue
        # Último intento: solo un número como texto ("7")
        try:
            h = int(valor)
            return time(hour=h % 24, minute=0)
        except ValueError:
            return None
 
    return None
 
 
# ---------------------------------------------------------------------------
# 2. Lectura del Excel y armado de la tabla de turnos
# ---------------------------------------------------------------------------
def cargar_turnos_desde_excel(
    archivo,
    mes,
    anio,
    fila_dias=4,
    col_inicio_dias="B",
    col_fin_dias="AF",
    fila_inicio_colab=5,
    fila_fin_colab=12,
    col_colaboradores="A",
):
    """
    Lee la (única) hoja del Excel y devuelve un DataFrame "largo" (tidy) con columnas:
    colaborador, dia, fecha, hora_inicio, hora_fin, turno (texto legible).
 
    mes y anio se usan para construir la columna 'fecha' completa, ya que el Excel
    solo trae el número de día en la fila 4.
    """
    df_raw = pd.read_excel(archivo, header=None, engine="openpyxl")
 
    # Convertir referencias de fila/columna (1-index, letras) a índices 0-index
    fila_dias_idx = fila_dias - 1
    fila_colab_ini_idx = fila_inicio_colab - 1
    fila_colab_fin_idx = fila_fin_colab - 1
    col_ini_idx = column_index_from_string(col_inicio_dias) - 1
    col_fin_idx = column_index_from_string(col_fin_dias) - 1
    col_colab_idx = column_index_from_string(col_colaboradores) - 1
 
    dias = df_raw.iloc[fila_dias_idx, col_ini_idx : col_fin_idx + 1].tolist()
 
    registros = []
    for fila_idx in range(fila_colab_ini_idx, fila_colab_fin_idx + 1):
        if fila_idx >= df_raw.shape[0]:
            break
        nombre = df_raw.iloc[fila_idx, col_colab_idx]
        if pd.isna(nombre) or str(nombre).strip() == "":
            continue
        nombre = str(nombre).strip()
 
        for j, dia in enumerate(dias):
            if pd.isna(dia):
                continue
            try:
                dia_num = int(dia)
            except (ValueError, TypeError):
                continue
 
            col_idx = col_ini_idx + j
            valor = df_raw.iloc[fila_idx, col_idx]
            if pd.isna(valor) or str(valor).strip() == "":
                continue
 
            try:
                fecha = datetime(anio, mes, dia_num).date()
            except ValueError:
                # Día que no existe en ese mes/año (ej. 31 de febrero); se omite
                continue
 
            # Día libre: se marca como "L"/"l" en la celda
            if str(valor).strip().upper() == "L":
                registros.append(
                    {
                        "colaborador": nombre,
                        "dia": dia_num,
                        "fecha": fecha,
                        "hora_inicio": None,
                        "hora_fin": None,
                        "turno": "Libre",
                    }
                )
                continue
 
            hora_inicio = normalizar_hora(valor)
            if hora_inicio is None:
                # No se pudo interpretar la celda; se guarda el valor crudo para revisión
                registros.append(
                    {
                        "colaborador": nombre,
                        "dia": dia_num,
                        "fecha": fecha,
                        "hora_inicio": None,
                        "hora_fin": None,
                        "turno": f"⚠ valor no reconocido: {valor}",
                    }
                )
                continue
 
            # Turno de 8 horas exactas, con rollover si cruza medianoche
            hora_fin_dt = (
                datetime.combine(datetime.today(), hora_inicio)
                + pd.Timedelta(hours=8)
            ).time()
 
            registros.append(
                {
                    "colaborador": nombre,
                    "dia": dia_num,
                    "fecha": fecha,
                    "hora_inicio": hora_inicio,
                    "hora_fin": hora_fin_dt,
                    "turno": f"{hora_inicio.strftime('%H:%M')} - {hora_fin_dt.strftime('%H:%M')}",
                }
            )
 
    return pd.DataFrame(registros)
 
 
# ---------------------------------------------------------------------------
# 3. Interfaz Streamlit
# ---------------------------------------------------------------------------
MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]
 
 
def mostrar_carga_turnos():
    st.subheader("Carga de turnos de colaboradores")
 
    archivo = st.file_uploader(
        "Sube el archivo Excel de turnos", type=["xlsx", "xls"], key="turnos_uploader"
    )
 
    if archivo is None:
        st.info("Sube un archivo para continuar.")
        return
 
    col1, col2 = st.columns(2)
    with col1:
        mes_nombre = st.selectbox("Mes", MESES, index=datetime.today().month - 1)
    with col2:
        anio = st.number_input(
            "Año", min_value=2020, max_value=2100, value=datetime.today().year, step=1
        )
 
    mes_num = MESES.index(mes_nombre) + 1
 
    if st.button("Procesar turnos"):
        with st.spinner("Procesando..."):
            try:
                df_turnos = cargar_turnos_desde_excel(archivo, mes=mes_num, anio=int(anio))
            except Exception as e:
                st.error(f"No se pudo procesar el archivo: {e}")
                return
 
        if df_turnos.empty:
            st.warning("No se encontraron turnos con la estructura esperada.")
            return
 
        st.session_state["df_turnos"] = df_turnos
        st.session_state["mes_turnos"] = f"{mes_nombre} {anio}"
 
    if "df_turnos" in st.session_state:
        st.markdown(f"**Turnos - {st.session_state['mes_turnos']}**")
 
        # Tabla pivote: colaboradores en filas, días en columnas
        tabla_pivote = st.session_state["df_turnos"].pivot_table(
            index="colaborador", columns="dia", values="turno", aggfunc="first"
        )
        # Ordenar columnas de días numéricamente
        tabla_pivote = tabla_pivote.reindex(sorted(tabla_pivote.columns), axis=1)
 
        st.dataframe(tabla_pivote, use_container_width=True)
 
        with st.expander("Ver datos en formato largo (para depuración / carga a BD)"):
            st.dataframe(st.session_state["df_turnos"], use_container_width=True)
 
 
# ---------------------------------------------------------------------------
# 4. Reparto de 'cantidad' (tabla registros) entre colaboradores de turno
# ---------------------------------------------------------------------------
def calcular_reparto_cantidad(
    db_path,
    df_turnos,
    tabla_registros="registros",
    col_cantidad="cantidad",
    col_fecha_registros="fecha",
    col_hora_registros="hora",
    col_colaborador="colaborador",
    col_fecha_turnos="fecha",
    col_hora_inicio="hora_inicio",
    duracion_turno_horas=8,
):
    """
    Suma 'cantidad' de la tabla 'registros' (en SQLite) por HORA específica
    (columna 'fecha' + columna 'hora'), y le otorga el total completo de esa
    hora a CADA colaborador que tenía turno cubriendo esa hora exacta, según
    el DataFrame df_turnos (tal como lo devuelve cargar_turnos_desde_excel,
    normalmente tomado de st.session_state['df_turnos']). No se divide entre
    colaboradores: si dos personas cubrían la misma hora, ambas reciben el
    total completo de esa hora.
 
    Cada turno (definido por su hora_inicio y la fecha en que empieza) se
    expande a las `duracion_turno_horas` horas que cubre, gestionando el
    cambio de día para el turno nocturno (ej. 22:00-06:00 cubre horas 22 y 23
    del día en que empieza, y 0 a 5 del día siguiente).
 
    Devuelve (df_resultado, horas_sin_turno):
      - df_resultado: colaborador, cantidad_atribuida
      - horas_sin_turno: lista de (fecha, hora) con cantidad en registros pero
        sin ningún colaborador de turno en esa hora exacta
    """
    conn = sqlite3.connect(db_path)
    try:
        query = f"""
            SELECT
                {col_fecha_registros} AS fecha,
                {col_hora_registros} AS hora,
                {col_cantidad} AS cantidad
            FROM {tabla_registros}
            WHERE {col_cantidad} IS NOT NULL
        """
        df_reg = pd.read_sql_query(query, conn)
    finally:
        conn.close()
 
    if df_reg.empty or df_turnos is None or df_turnos.empty:
        return pd.DataFrame(columns=["colaborador", "cantidad_atribuida"]), []
 
    # Normalizar fecha y hora de cada registro (la hora puede venir como
    # entero, time, o texto '06:00', igual que en los turnos)
    df_reg["fecha"] = pd.to_datetime(df_reg["fecha"]).dt.date
    df_reg["hora_int"] = df_reg["hora"].apply(
        lambda v: normalizar_hora(v).hour if normalizar_hora(v) is not None else None
    )
    filas_invalidas = df_reg["hora_int"].isna().sum()
    df_reg = df_reg.dropna(subset=["hora_int"])
    if df_reg.empty:
        return pd.DataFrame(columns=["colaborador", "cantidad_atribuida"]), []
    df_reg["hora_int"] = df_reg["hora_int"].astype(int)
 
    # Total de cantidad por (fecha, hora) exacta
    df_totales = (
        df_reg.groupby(["fecha", "hora_int"])["cantidad"]
        .sum()
        .reset_index()
        .rename(columns={"cantidad": "cantidad_total"})
    )
 
    # Expandir cada turno a las horas puntuales que cubre (gestiona cambio de día)
    filas_turno_hora = []
    df_turnos_validos = df_turnos.dropna(subset=[col_hora_inicio])
    for _, row in df_turnos_validos.iterrows():
        hora_inicio = row[col_hora_inicio]
        fecha_inicio = row[col_fecha_turnos]
        if pd.isna(hora_inicio) or pd.isna(fecha_inicio):
            continue
        # fecha_inicio puede venir como date o Timestamp; normalizar a date
        if hasattr(fecha_inicio, "date") and not isinstance(fecha_inicio, datetime):
            pass
        if isinstance(fecha_inicio, pd.Timestamp):
            fecha_inicio = fecha_inicio.date()
 
        dt_inicio = datetime.combine(fecha_inicio, hora_inicio)
        for h in range(duracion_turno_horas):
            dt_hora = dt_inicio + timedelta(hours=h)
            filas_turno_hora.append(
                {
                    "colaborador": row[col_colaborador],
                    "fecha": dt_hora.date(),
                    "hora_int": dt_hora.hour,
                }
            )
 
    if not filas_turno_hora:
        return pd.DataFrame(columns=["colaborador", "cantidad_atribuida"]), []
 
    df_turno_horas = pd.DataFrame(filas_turno_hora).drop_duplicates()
 
    # Cruzar: cada colaborador de turno en esa hora recibe el total COMPLETO de esa hora
    df_detalle = df_turno_horas.merge(df_totales, on=["fecha", "hora_int"], how="inner")
 
    # Horas con cantidad pero sin ningún colaborador de turno (para avisar)
    horas_con_turno = set(zip(df_detalle["fecha"], df_detalle["hora_int"]))
    horas_totales = set(zip(df_totales["fecha"], df_totales["hora_int"]))
    horas_sin_turno = sorted(horas_totales - horas_con_turno)
 
    df_resultado = (
        df_detalle.groupby("colaborador")["cantidad_total"]
        .sum()
        .reset_index()
        .rename(columns={"cantidad_total": "cantidad_atribuida"})
        .sort_values("cantidad_atribuida", ascending=False)
        .reset_index(drop=True)
    )
 
    return df_resultado, horas_sin_turno
 
 
def mostrar_reparto_cantidad(db_path, tabla_registros="registros"):
    st.subheader("Reparto de cantidad por colaborador (por hora)")
 
    df_turnos = st.session_state.get("df_turnos")
    if df_turnos is None or df_turnos.empty:
        st.info(
            "Primero sube y procesa el Excel de turnos (sección de carga de turnos) "
            "para poder calcular el reparto."
        )
        return
 
    df_resultado, horas_sin_turno = calcular_reparto_cantidad(
        db_path, df_turnos=df_turnos, tabla_registros=tabla_registros
    )
 
    if df_resultado.empty:
        st.warning(
            "No hay coincidencias entre 'registros' y los turnos cargados por fecha/hora. "
            "Verifica que ambos estén en el mismo rango y que la columna 'hora' de "
            "registros tenga un formato reconocible."
        )
        return
 
    st.dataframe(df_resultado, use_container_width=True)
    st.caption(f"Total general (con posible doble conteo si hay turnos solapados): {df_resultado['cantidad_atribuida'].sum():,.2f}")
 
    if horas_sin_turno:
        detalle = ", ".join(f"{f} {h}:00" for f, h in horas_sin_turno[:10])
        extra = "..." if len(horas_sin_turno) > 10 else ""
        st.warning(
            f"Hay {len(horas_sin_turno)} hora(s) con cantidad en 'registros' "
            f"pero sin ningún colaborador de turno en ese momento exacto: {detalle}{extra}"
        )
 

def get_base64(file):
    with open(file, "rb") as f:
        return base64.b64encode(f.read()).decode()
logo = get_base64("logo.png")
bg = get_base64("fondo.jpg")

st.set_page_config(page_title="Nuevo Registro", page_icon="📝", layout="wide")

# CSS

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #0f2537; }
    [data-testid="stSidebar"] * { color: #e0f0ff !important; }

    .form-section {
        background: #e0f0ff;
        border-radius: 10px;
        padding: 20px 24px;
        margin-bottom: 16px;
        border-left: 4px solid #1976d2;
    }
    .form-section h4 {
        color: #0f2537;
        margin: 0 0 14px 0;
        font-size: 1rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .titulo-pagina {
        background:   #e0f0ff;
        color:  #0f2537;
        font-size: 2rem;
        font-weight: 700;
        border-left: 5px solid #1976d2;
        padding-left: 16px;
        margin-bottom: 4px;
    }
    .subtitulo { color:  #0f2537; font-size: 1.3rem; font-weight: 700; padding-left: 21px; margin-bottom: 24px; }

   [data-testid="stWidgetLabel"] p {
    font-size: 15px !important;
    font-weight: 700;
    color: #0f2537;
    }

    /* Botón principal */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #1565c0, #1976d2);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 12px 40px;
        font-size: 1rem;
        font-weight: 600;
        width: 100%;
        transition: all 0.2s;
    }
    div.stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #0d47a1, #1565c0);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(21, 101, 192, 0.4);
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

st.markdown('<div class="titulo-pagina">📝 Nuevo Registro</div>', unsafe_allow_html=True)
 
 
if __name__ == "__main__":
    mostrar_carga_turnos()
    mostrar_reparto_cantidad(db_path= db_path)

