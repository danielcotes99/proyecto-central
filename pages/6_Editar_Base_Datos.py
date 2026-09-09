import streamlit as st
import sys, os
import sqlite3
import pandas as pd
import base64
import hashlib
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


st.set_page_config(page_title="Editar Base de Datos", page_icon="🗄️", layout="wide")


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
        background: #e3f2fd;
        color: #0d47a1;
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

st.markdown('<div class="titulo-pagina">🗄️ Editar Base de Datos</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitulo">Gestión de catálogos de referencia</div>', unsafe_allow_html=True)

# Conectar a la base de datos
DB_PATH = "esterilizacion.db"

def obtener_tablas_disponibles():
    """Obtiene lista de todas las tablas disponibles en la BD"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            AND name NOT IN ('registros', 'sqlite_sequence')
            ORDER BY name
        """)
        
        tablas = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return tablas
    except Exception as e:
        st.error(f"Error al obtener tablas: {e}")
        return []

def verificar_estructura_tabla(tabla):
    """Verifica que la tabla tenga las 4 columnas requeridas"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(f"PRAGMA table_info({tabla})")
        columnas = [col[1].upper() for col in cursor.fetchall()]
        
        conn.close()
        
        # Verificar que tenga exactamente las 4 columnas (en cualquier orden)
        columnas_requeridas = {'NOMBRE', 'CODIGO', 'UBICACION', 'PROCEDENCIA'}
        columnas_actuales = set(columnas)
        
        return columnas_requeridas.issubset(columnas_actuales)
    except Exception as e:
        return False

def obtener_datos_tabla(tabla):
    """Obtiene todos los datos de una tabla"""
    try:
        conn = sqlite3.connect(DB_PATH)
        
        # Solo seleccionar las 4 columnas requeridas
        query = f"SELECT NOMBRE, CODIGO, UBICACION, PROCEDENCIA FROM {tabla} ORDER BY CODIGO"
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error al obtener datos: {e}")
        return pd.DataFrame()

def obtener_valores_procedencia(tabla):
    """Obtiene valores únicos de la columna PROCEDENCIA"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT DISTINCT PROCEDENCIA FROM {tabla} WHERE PROCEDENCIA IS NOT NULL AND PROCEDENCIA != '' ORDER BY PROCEDENCIA")
        valores = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return valores
    except Exception as e:
        return []

def insertar_entrada(tabla, nombre, codigo, ubicacion, procedencia):
    """Inserta nueva entrada en la tabla seleccionada"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Insertar en las 4 columnas
        cursor.execute(f"""
            INSERT INTO {tabla} (NOMBRE, CODIGO, UBICACION, PROCEDENCIA)
            VALUES (?, ?, ?, ?)
        """, (nombre, codigo, ubicacion if ubicacion else '', procedencia))
        
        conn.commit()
        conn.close()
        return True, "✅ Entrada agregada exitosamente"
        
    except sqlite3.IntegrityError:
        return False, "❌ El código ya existe en esta tabla. Usa un código único."
    except Exception as e:
        return False, f"❌ Error al insertar: {str(e)}"

def eliminar_entrada(tabla, codigo):
    """Elimina una entrada de la tabla por código"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(f"DELETE FROM {tabla} WHERE NOMBRE = ?", (codigo,))
        
        conn.commit()
        conn.close()
        return True, "✅ Entrada eliminada exitosamente"
        
    except Exception as e:
        return False, f"❌ Error al eliminar: {str(e)}"

def actualizar_entrada(tabla, codigo_original, nombre, codigo_nuevo, ubicacion, procedencia):
    """Actualiza una entrada existente"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        if cursor.rowcount == 0:
            return False, "⚠️ No se encontró el registro a actualizar"
        else:
            cursor.execute(f"""
                UPDATE {tabla} 
                SET NOMBRE = ?, CODIGO = ?, UBICACION = ?, PROCEDENCIA = ?
                WHERE NOMBRE = ?
            """, (nombre, codigo_nuevo, ubicacion if ubicacion else '', procedencia, codigo_original))
            
            conn.commit()
            conn.close()
            return True, "✅ Entrada actualizada exitosamente"
        
    except sqlite3.IntegrityError:
        return False, "❌ El nuevo código ya existe. Usa un código único."
    except Exception as e:
        return False, f"❌ Error al actualizar: {str(e)}"

if "mostrar_input_procedencia" not in st.session_state:
    st.session_state.mostrar_input_procedencia = False

def actualizar_procedencia():
    st.session_state.mostrar_input_procedencia = (
        st.session_state.procedencia_select == "+ Agregar nuevo..."
    )


def pagina_protegida():
    st.title("🔒 Página protegida")

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
    st.success("Acceso concedido")
pagina_protegida()


# ─── SELECTOR DE TABLA ──────────────────────────────────────────────────────
st.markdown('<div class="titulo-pagina">🗄️ 📋 Paso 1: Selecciona la tabla</div>', unsafe_allow_html=True)

tablas_disponibles = obtener_tablas_disponibles()

if not tablas_disponibles:
    st.warning("⚠️ No se encontraron tablas en la base de datos")
    st.stop()

# Filtrar solo tablas con estructura correcta
tablas_validas = [t for t in tablas_disponibles if verificar_estructura_tabla(t)]

if not tablas_validas:
    st.error("❌ No hay tablas con la estructura correcta (NOMBRE, CODIGO, UBICACION, PROCEDENCIA)")
    st.stop()

col_tabla, col_info = st.columns([2, 3])

with col_tabla:
    tabla_seleccionada = st.selectbox(
        "Tabla a editar:",
        tablas_validas,
        help="Selecciona la tabla donde deseas agregar o editar entradas"
    )


# ─── FORMULARIO DE NUEVA ENTRADA ────────────────────────────────────────────
st.markdown('<div class="titulo-pagina">➕ Paso 2: Agregar nueva entrada</div>', unsafe_allow_html=True)


# Obtener valores existentes de PROCEDENCIA
valores_procedencia = obtener_valores_procedencia(tabla_seleccionada)

# Inicializar estado
if "procedencia_select" not in st.session_state:
    st.session_state.procedencia_select = ""

if "procedencia_nueva" not in st.session_state:
    st.session_state.procedencia_nueva = ""

modo_procedencia = st.radio(
        "🏢 PROCEDENCIA *",
        ["Existente", "Nueva"],
        horizontal=True
)

with st.form("formulario_nueva_entrada", clear_on_submit=True):
    col1, col2 = st.columns(2)
    
    with col1:
        nombre = st.text_input(
            "📝 NOMBRE *",
            placeholder="Ej: Bandeja Cirugía General"
        )
        
        codigo = st.text_input(
            "🔢 CODIGO *",
            placeholder="Ej: BAN-CG-001"
        )
    
    with col2:
        ubicacion = st.text_input(
            "📍 UBICACION",
            placeholder="Ej: EST-A-15 (Opcional)"
        )

        procedencia = (
            st.selectbox("Procedencia", [""] + valores_procedencia)
            if modo_procedencia == "Existente"
            else st.text_input("Nueva procedencia")
        )

    st.markdown("---")

    submitted = st.form_submit_button(
        "💾 Guardar",
        type="primary",
        use_container_width=True
    )

# Procesar formulario
if submitted:
    # Validar solo campos obligatorios (nombre, codigo, procedencia)
    if not nombre or not procedencia:
        st.error("⚠️ Los campos NOMBRE, CODIGO y PROCEDENCIA son obligatorios")
    else:
        # Insertar en la base de datos
        exito, mensaje = insertar_entrada(
            tabla_seleccionada,
            nombre,
            codigo,
            ubicacion,
            procedencia
        )
        
        if exito:
            st.success(mensaje)
            st.balloons()
            
            # Mostrar resumen
            st.info(f"""
            **Nueva entrada agregada a:** `{tabla_seleccionada}`
            
            - **NOMBRE:** {nombre}
            - **CODIGO:** {codigo}
            - **UBICACION:** {ubicacion if ubicacion else '(vacío)'}
            - **PROCEDENCIA:** {procedencia}
            """)
            
            import time
            time.sleep(2)
            st.rerun()
        else:
            st.error(mensaje)

# ─── TABLA ACTUAL ───────────────────────────────────────────────────────────
st.markdown('<div class="titulo-pagina">📊 Datos actuales en la tabla seleccionada </div>', unsafe_allow_html=True)


df_mostrar = obtener_datos_tabla(tabla_seleccionada)

if not df_mostrar.empty:
    st.caption(f"Total de registros: {len(df_mostrar)}")
    
    # Configurar visualización
    column_config = {
        "NOMBRE": st.column_config.TextColumn("NOMBRE", width="large"),
        "CODIGO": st.column_config.TextColumn("CODIGO", width="medium"),
        "UBICACION": st.column_config.TextColumn("UBICACION", width="medium"),
        "PROCEDENCIA": st.column_config.TextColumn("PROCEDENCIA", width="medium")
    }
    
    st.dataframe(
        df_mostrar,
        use_container_width=True,
        hide_index=True,
        column_config=column_config
    )
    
    # Exportar
    col_export, col_space = st.columns([1, 3])
    
    with col_export:
        import io
        buffer = io.BytesIO()
        df_mostrar.to_excel(buffer, index=False, engine="openpyxl")
        
        st.download_button(
            label="📥 Exportar a Excel",
            data=buffer.getvalue(),
            file_name=f"{tabla_seleccionada}_{pd.Timestamp.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

else:
    st.info("La tabla está vacía. Agrega la primera entrada usando el formulario.")

# ─── EDITAR/ELIMINAR ────────────────────────────────────────────────────────

st.markdown('<div class="titulo-pagina">✏️ Editar o Eliminar Entradas </div>', unsafe_allow_html=True)

with st.expander("🔧 Gestionar entradas existentes", expanded=False):
    if not df_mostrar.empty:
        # Selector de entrada a editar
        entrada_seleccionada = st.selectbox(
            "Selecciona una entrada por código:",
            df_mostrar['NOMBRE'].tolist(),
            format_func=lambda x: f"{x} - {df_mostrar.loc[df_mostrar['NOMBRE'] == x, 'PROCEDENCIA'].iloc[0]}"
            if not df_mostrar.loc[df_mostrar['NOMBRE'] == x].empty
            
            else f"{x} - (sin nombre)"
        )
        
        if entrada_seleccionada:
            # Obtener datos actuales
            datos_actuales = df_mostrar[df_mostrar['NOMBRE'] == entrada_seleccionada].iloc[0]
            
            tab1, tab2 = st.tabs(["✏️ Editar", "🗑️ Eliminar"])
            
            # TAB EDITAR
            with tab1:
                with st.form("form_editar"):
                    st.caption("Edita los campos y presiona 'Actualizar'")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        nuevo_nombre = st.text_input(
                            "NOMBRE *",
                            value=datos_actuales['NOMBRE']
                        )
                        nuevo_codigo = st.text_input(
                            "CODIGO *",
                            value=datos_actuales['CODIGO']
                        )
                    
                    with col2:
                        nueva_ubicacion = st.text_input(
                            "UBICACION",
                            value=datos_actuales['UBICACION'] if datos_actuales['UBICACION'] else ''
                        )
                        
                        # Combobox para edición de PROCEDENCIA
                        valores_proc_edit = obtener_valores_procedencia(tabla_seleccionada)
                        
                        # Agregar valor actual si no está en la lista
                        if datos_actuales['PROCEDENCIA'] not in valores_proc_edit:
                            valores_proc_edit = [datos_actuales['PROCEDENCIA']] + valores_proc_edit
                        
                        nueva_procedencia_sel = st.selectbox(
                            "PROCEDENCIA *",
                            options=valores_proc_edit + ["+ Agregar nuevo..."],
                            index=valores_proc_edit.index(datos_actuales['PROCEDENCIA']) if datos_actuales['PROCEDENCIA'] in valores_proc_edit else 0
                        )
                        
                        if nueva_procedencia_sel == "+ Agregar nuevo...":
                            nueva_procedencia = st.text_input(
                                "Nueva PROCEDENCIA:",
                                placeholder="Escribe nueva procedencia",
                                label_visibility="collapsed",
                                key="nueva_procedencia_edit"
                            )
                        else:
                            nueva_procedencia = nueva_procedencia_sel
                    
                    if st.form_submit_button("💾 Actualizar", type="primary"):
                        if not nuevo_nombre or not nuevo_codigo or not nueva_procedencia:
                            st.error("⚠️ NOMBRE, CODIGO y PROCEDENCIA son obligatorios")
                        else:
                            exito, mensaje = actualizar_entrada(
                                tabla_seleccionada,
                                entrada_seleccionada,  # código original
                                nuevo_nombre,
                                nuevo_codigo,
                                nueva_ubicacion,
                                nueva_procedencia
                            )
                            
                            if exito:
                                st.success(mensaje)
                                import time
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(mensaje)
            
            # TAB ELIMINAR
            with tab2:
                st.warning(f"""
                **¿Estás seguro de eliminar esta entrada?**
                
                - **CODIGO:** {datos_actuales['CODIGO']}
                - **NOMBRE:** {datos_actuales['NOMBRE']}
                - **PROCEDENCIA:** {datos_actuales['PROCEDENCIA']}
                
                ⚠️ Esta acción no se puede deshacer.
                """)
                
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    if st.button("🗑️ Confirmar Eliminación", type="secondary", use_container_width=True):
                        exito, mensaje = eliminar_entrada(tabla_seleccionada, entrada_seleccionada)
                        
                        if exito:
                            st.success(mensaje)
                            import time
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(mensaje)
    else:
        st.info("No hay entradas para editar")
