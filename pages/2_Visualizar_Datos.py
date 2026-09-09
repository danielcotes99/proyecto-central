import streamlit as st
import sys, os
import pandas as pd
import io
import base64
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database import cargar_registros, eliminar_registro, actualizar_registro

st.set_page_config(page_title="Visualizar Datos", page_icon="📊", layout="wide")

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
    .subtitulo {  color: #0E1117;
    font-size: 1rem;
    font-weight: 700;
    padding-left: 21px;
    margin-bottom: 24px; 
    }
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

st.markdown('<div class="titulo-pagina">📊 Visualizar y Editar Datos</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitulo">Consulta, filtra y edita los registros de esterilización</div>', unsafe_allow_html=True)

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
    

df = cargar_registros()

if df.empty:
    st.info("No hay registros aún. Ve a **📝 Nuevo Registro** para comenzar.")
    st.stop()

# ─── FILTROS ────────────────────────────────────────────────────────────────
with st.expander("🔍 Filtros", expanded=True):

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        tipos = ["Todas"] + sorted(df["tipo"].dropna().unique().tolist())
        filtro_tipo = st.selectbox("tipo", tipos)

        detalles = ["Todas"] + sorted(df["detalle"].dropna().unique().tolist())
        filtro_detalle = st.selectbox("detalle", detalles)

    with col2:
        operarios = ["Todos"] + sorted(df["operario"].dropna().unique().tolist())
        filtro_operario = st.selectbox("Operario", operarios)

    with col3:

        # convertir columna a datetime
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

        fecha_min = df["fecha"].min()
        fecha_max = df["fecha"].max()

        rango_fechas = st.date_input(
            "Rango de fechas",
            value=(fecha_min, fecha_max),
            min_value=fecha_min,
            max_value=fecha_max
        )

    with col4:
        maquinas = ["Todas"] + sorted(df["maquina"].dropna().unique().tolist())
        filtro_maquina = st.selectbox("Máquina", maquinas)


# -------------------------
# Aplicar filtros
# -------------------------

df_filtrado = df.copy()

if filtro_tipo != "Todas":
    df_filtrado = df_filtrado[df_filtrado["tipo"] == filtro_tipo]


if filtro_detalle != "Todas":
    df_filtrado = df_filtrado[df_filtrado["detalle"] == filtro_detalle]

if filtro_operario != "Todos":
    df_filtrado = df_filtrado[df_filtrado["operario"] == filtro_operario]

if filtro_maquina != "Todas":
    df_filtrado = df_filtrado[df_filtrado["maquina"] == filtro_maquina]


# filtro por rango de fechas
if len(rango_fechas) == 2:

    fecha_inicio = pd.to_datetime(rango_fechas[0])
    fecha_fin = pd.to_datetime(rango_fechas[1])

    df_filtrado = df_filtrado[
        (df_filtrado["fecha"] >= fecha_inicio) &
        (df_filtrado["fecha"] <= fecha_fin)
    ]


st.markdown(f"**{len(df_filtrado)}** registros encontrados")

# ─── TABLA EDITABLE ─────────────────────────────────────────────────────────
st.subheader("✏️ Editar registros")
st.caption("Puedes editar las celdas directamente. Presiona 'Guardar cambios' para confirmar.")

# Crear datetime combinado
df_filtrado["fecha_hora"] = pd.to_datetime(
    df_filtrado["fecha"].astype(str) + " " + df_filtrado["hora"].astype(str),
    errors="coerce"
)

# Ordenar
df_filtrado = df_filtrado.sort_values(by="fecha_hora", ascending=False)

cols_excluir = []
cols_editar = [c for c in df_filtrado.columns if c not in cols_excluir]

df_editable = st.data_editor(
    df_filtrado[cols_editar],
    use_container_width=True,
    hide_index=True,
    num_rows="fixed"
)

# 🔹 Calcular suma de la columna cantidad
total_cantidad = pd.to_numeric(df_editable["cantidad"], errors="coerce").fillna(0).sum()

# 🔹 Mostrar resultado
st.markdown(f"### 🔢 Total cantidad: **{int(total_cantidad)}**")


pagina_protegida()
col_save, col_export = st.columns([1, 1])
with col_save:
    if st.button("💾 Guardar cambios", type="primary", use_container_width=True):
        try:
            import pandas as pd

            errores = []        # ✅ AQUÍ
            actualizados = 0   # ✅ AQUÍ

            for i, row in df_editable.iterrows():
                datos = row.to_dict()

                # 🔹 Convertir timestamps
                for key, value in datos.items():
                    if isinstance(value, pd.Timestamp):
                        if key == "hora":
                            datos[key] = value.strftime("%H:%M:%S")
                        elif key in ["fecha", "vencimiento"]:
                            datos[key] = value.strftime("%Y-%m-%d")
                        else:
                            datos[key] = value.strftime("%Y-%m-%d %H:%M:%S")

                # 🔹 Mapear nombres
                # 🔹 Mapear nombres para SQL
                datos["tipociclo"] = datos.get("tipo_de_ciclo")
                datos["ciclo"] = datos.get("carga")

                # 🔹 FIX para pruebas
                datos["prueba_proteinas"] = datos.get("prueba_de_proteinas_de_arrastre")
                datos["prueba_luminiscencia"] = datos.get("prueba_de_proteinas_de_residuo")

                id_reg = datos.get("id")

                if not id_reg:
                    errores.append(f"Fila {i}: sin ID válido")
                    continue

                try:
                    datos["cantidad"] = int(datos.get("cantidad", 1))
                except:
                    datos["cantidad"] = 1

                try:
                    actualizar_registro(id_reg, datos)
                    actualizados += 1
                except Exception as e:
                    errores.append(f"Fila {i} (ID {id_reg}): {e}")

            if actualizados > 0:
                st.success(f"✅ {actualizados} registros actualizados correctamente.")

            if errores:
                st.warning("⚠️ Algunos registros no se pudieron actualizar:")
                for err in errores:
                    st.write(f"- {err}")

            if actualizados > 0:
                st.rerun()

        except Exception as e:
            st.error(f"❌ Error general al guardar: {e}")
with col_export:
    buffer = io.BytesIO()

    df_filtrado.to_excel(buffer, index=False, engine="openpyxl")

    st.download_button(
        "📥 Exportar a EXCEL",
        data=buffer.getvalue(),
        file_name="registros_esterilizacion.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

# ─── ELIMINAR REGISTRO ──────────────────────────────────────────────────────
st.markdown("---")
st.subheader("🗑️ Eliminar registro")
ids_disponibles = df_filtrado["id"].tolist()

if ids_disponibles:
    col1, col2 = st.columns([2, 1])
    with col1:
        mapa_id_lote = dict(zip(df_filtrado['id'], df_filtrado['lote']))

    id_eliminar = st.selectbox(
        "Selecciona el ID del registro a eliminar",
        ids_disponibles,
        format_func=lambda x: f"ID {x} — {mapa_id_lote.get(x, '(sin lote)')}"
    )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Eliminar", type="secondary", use_container_width=True):
            eliminar_registro(id_eliminar)
            st.warning(f"Registro ID {id_eliminar} eliminado.")
            st.rerun()
