import streamlit as st
import sys, os
from datetime import date, datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database import insertar_registro
import sqlite3
import platform
import subprocess
import base64
import pytz
from etiqueta_printer import generar_etiqueta_pdf
import hashlib
import json

DB_PATH = "esterilizacion.db"

tz = pytz.timezone("America/Panama")

def hash_registro_preview():
    base = {
        "sede": (sede or "").strip().upper(),
        "entidad": (entidad or "").strip().upper(),
        "procedencia": (procedencia or "").strip().upper(),
        "tipo": (tipo or "").strip().upper(),
        "detalle": (detalle or "").strip().upper(),
        "comentario": (comentario or "").strip().upper(),
        "codigo": str(codigo).strip(),
        "maquina": (maquina or "").strip().upper(),
        "operario": (operario or "").strip().upper(),
        "fecha": str(fecha),   # ✅ se mantiene
        # ❌ NO incluir hora
        "cantidad": int(cantidad),
        "ciclo": (ciclo or "").strip(),
    }

    return hashlib.md5(
        json.dumps(base, sort_keys=True).encode()
    ).hexdigest()

def cargar_opciones(tabla, columna):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = f"""
        SELECT DISTINCT "{columna}"
        FROM {tabla}
        WHERE "{columna}" IS NOT NULL
          AND TRIM("{columna}") != ''
        ORDER BY "{columna}"
    """

    cursor.execute(query)
    opciones = [fila[0] for fila in cursor.fetchall()]
    conn.close()

    return [""] + opciones

def cargar_opciones_filtradas(tabla, columna, columna_filtro=None, valor_filtro=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Convertir índices a nombres
    cursor.execute(f"SELECT * FROM {tabla} LIMIT 0")
    nombres_columnas = [description[0] for description in cursor.description]
    
    if isinstance(columna, int) and columna < len(nombres_columnas):
        columna = nombres_columnas[columna]
    
    if isinstance(columna_filtro, int) and columna_filtro < len(nombres_columnas):
        columna_filtro = nombres_columnas[columna_filtro]
    
    # Resto de la función igual...
    query = f"""
        SELECT DISTINCT "{columna}"
        FROM {tabla}
        WHERE "{columna}" IS NOT NULL
          AND TRIM("{columna}") != ''
    """
    
    if columna_filtro and valor_filtro is not None:
        query += f' AND "{columna_filtro}" = ?'
        cursor.execute(query + f' ORDER BY "{columna}"', (valor_filtro,))
    else:
        cursor.execute(query + f' ORDER BY "{columna}"')
    
    opciones = [fila[0] for fila in cursor.fetchall()]
    conn.close()
    
    return [""] + opciones

def generar_lote(maquina, ciclo, operario, fecha): 
    """
    Genera el código de lote en formato: 400A1EQ-02-03-26-27
    maquina + ciclo + operario + fecha + número único
    """
    import datetime
    
    # Limpiar los valores
    maquina_codigo = str(maquina).replace(" ", "")[:10]  # Máximo 10 caracteres
    ciclo_codigo = str(ciclo).replace(" ", "")[:5]  # Máximo 5 caracteres
    
    # Extraer iniciales del operario (primeras 2 letras)
    operario_codigo = "".join([word[0].upper() for word in str(operario).split() if word])[:2]
    
    # Formato de fecha: DD-MM-YY
    if isinstance(fecha, str):
        fecha_obj = datetime.datetime.strptime(fecha, "%Y-%m-%d")
    else:
        fecha_obj = fecha
    
    fecha_codigo = fecha_obj.strftime("%d%m%y")
    
    # Generar número único basado en timestamp (últimos 4 dígitos de milisegundos)
    timestamp = datetime.datetime.now()
    numero_unico = str(int(timestamp.timestamp() * 1000))[-4:]
    
    # Construir lote: MAQUINA+CICLO+OPERARIO-FECHA-NUMERO
    lote = f"{maquina_codigo}{ciclo_codigo}{operario_codigo}{fecha_codigo}{numero_unico}"
    
    return lote

def obtener_ultimo_ciclo(maquina, fecha):
    """
    Obtiene el último número de ciclo registrado para una máquina en una fecha específica.
    Retorna el siguiente número de ciclo.
    """
    if not maquina or maquina == "":
        return ""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        query = """
            SELECT carga
            FROM registros
            WHERE maquina = ? AND fecha = ?
            ORDER BY id DESC
            LIMIT 1
        """
        cursor.execute(query, (maquina, str(fecha)))
        resultado = cursor.fetchone()
        
        if resultado:
            ultimo_ciclo = resultado[0]
            # Intentar extraer el número del ciclo
            # Asume formatos como "3", "C-3", "003", etc.
            import re
            numeros = re.findall(r'\d+', str(ultimo_ciclo))
            if numeros:
                ultimo_numero = int(numeros[-1])  # Toma el último número encontrado
                siguiente_numero = ultimo_numero
                return str(siguiente_numero)
        
        # Si no hay ciclos previos, empezar en 1
        return "1"
    
    except Exception as e:
        print(f"Error al obtener último ciclo: {e}")
        return ""
    finally:
        conn.close()

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
st.markdown('<div class="subtitulo">Complete todos los campos para registrar un proceso de esterilización</div>', unsafe_allow_html=True)

# Opciones de los selectores — personaliza según tus datos reales
SEDES        = ["HOSPITAL PUNTA PACIFICA"]
ENTIDADES    = cargar_opciones("Listas", "PROCEDENCIA")
#TIPOS        = [""]
EMPAQUES     = cargar_opciones("Listas", "EMPAQUE")
MAQUINAS     = cargar_opciones("Listas", "AUTOCLAVES")
OPERARIOS    = cargar_opciones("Listas", "OPERARIOS")
ESPECIALIDADES = cargar_opciones("Listas", "ESPECIALIDAD")
SERVICIOS    = ["", "USO INTERNO", "USO EXTERNO"]
RESULTADOS   = ["", "SI", "NO"]
PROTEINAS = ["P. PROT. A", "P DE PROT. R", ""]
DETALLE = [""]
TIPOCICLO = ["CICLO 1 - 47min", "CICLO 2 - 57min", "CICLO 3 - 18min", "CICLO 4 - 62min", "CICLO 5 - 27min", "CICLO 6 - 18min", "CICLO 7 - 37min", ""]
CICLOSTERRA = ["STANDARD - 47min", "FLEX - 42min"]
CONFIG_DETALLE = {
    # Casos específicos con procedencia
    ("PACIFICA SALUD", "CENTRAL DE ESTERILIZACION", "BANDEJAS"): ("BANDEJAS", "NOMBRE", None, None),
    ("PACIFICA SALUD", "CENTRAL DE ESTERILIZACION", "INSTRUMENTAL"): ("INSTRUMENTOS", "NOMBRE", None, None),
    ("PACIFICA SALUD", "CENTRAL DE ESTERILIZACION", "PRUEBA"): ("Listas", "PRUEBA", None, None),
    ("PACIFICA SALUD", "CENTRAL DE ESTERILIZACION", "ROBOT"): ("ROBOT", "NOMBRE", None, None),
    ("PACIFICA SALUD", "CENTRAL DE ESTERILIZACION", "MISCELANEOS"): ("MISCELANEO", "NOMBRE", None, None),
    ("PACIFICA SALUD", "CENTRAL DE ESTERILIZACION", "LENTES"): ("LENTES", "NOMBRE", None, None),
    
    # Casos generales con filtro (procedencia = None para búsqueda genérica)
    ("PACIFICA SALUD", None, "BANDEJAS"): ("BANDEJA_DE_AREA", "NOMBRE", "PROCEDENCIA", "procedencia"),
    ("PACIFICA SALUD", None, "INSTRUMENTAL"): ("INSTRUMENTO_DE_AREA", "NOMBRE", "PROCEDENCIA", "procedencia"),
    ("PACIFICA SALUD", None, "INSUMO"): ("INSUMO_DE_AREA", "NOMBRE", "PROCEDENCIA", "procedencia"),
    ("PACIFICA SALUD", None, "MISCELANEOS"): ("MISCELANEOS_DE_AREA", "NOMBRE", "PROCEDENCIA", "procedencia"),
    
    ("MEDICO", None, "BANDEJAS"): ("BANDEJAS_DE_MEDICO", "NOMBRE", "PROCEDENCIA", "procedencia"),
    ("MEDICO", None, "INSTRUMENTAL"): ("INSTRUMENTOS_DE_MEDICO", "NOMBRE", "PROCEDENCIA", "procedencia"),
    ("MEDICO", None, "INSUMO"): ("INSUMO_DE_MEDICO", "NOMBRE", "PROCEDENCIA", "procedencia"),
    
    ("PROVEEDOR EXTERNO", None, "BANDEJAS"): ("BANDEJAS_DE_PE", "NOMBRE", "PROCEDENCIA", "procedencia"),
    ("PROVEEDOR EXTERNO", None, "INSUMO"): ("INSUMO_DE_PE", "NOMBRE", "PROCEDENCIA", "procedencia"),
    ("PROVEEDOR EXTERNO", None, "INSTRUMENTAL"): ("INSTRUMENTOS_DE_PE", "NOMBRE", "PROCEDENCIA", "procedencia"),
    ("PROVEEDOR EXTERNO", None, "LENTES"): ("LENTES_DE_PE", "NOMBRE", "PROCEDENCIA", "procedencia"),
}

MATERIALES = {
    "CONTENEDORES": 365,
    "PAPEL CREPADO": 30,
    "PAPEL MIXTO SENCILLO": 90,
    "PAPEL MIXTO DOBLE": 180,
    "POLIPROPILENO": 90,
    "ROLLOS TYVEK": 365,
    "TELA": 30,
    "N/A (PRUEBA)": 0
}


# ─── SECCIÓN 1: Identificación ──────────────────────────────────────────
st.markdown('<div class="form-section"><h4>🏥 Identificación</h4>', unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    fecha = st.date_input("Fecha *", value=datetime.now(tz).date())
    
with col2:
    hora = st.time_input("Hora *", value=datetime.now(tz).time())
col1, col2, col3 = st.columns(3)
with col1:
    
    sede = st.selectbox("Sede *", SEDES)
with col2:
    entidad = st.selectbox("Entidad *", ENTIDADES)
if entidad == "PACIFICA SALUD":
    PROCEDENCIAS = cargar_opciones("LISTA_AREAS", "PROCEDENCIA") + ["NO ENLISTADO"]

elif entidad == "PROVEEDOR EXTERNO":
    PROCEDENCIAS = cargar_opciones("LISTA_PROVEEDORES", "PROCEDENCIA") + ["NO ENLISTADO"]

elif entidad == "MEDICO":
    PROCEDENCIAS = cargar_opciones("LISTA_MEDICOS", "PROCEDENCIA") + ["NO ENLISTADO"]

else:
    PROCEDENCIAS = [""]
with col3:
    procedencia = st.selectbox("Procedencia *", PROCEDENCIAS)
st.markdown('</div>', unsafe_allow_html=True)

    # ─── SECCIÓN 2: Material ────────────────────────────────────────────────
st.markdown('<div class="form-section"><h4>📦 Material</h4>', unsafe_allow_html=True)
col1, col2, col3 = st.columns(3)
if entidad == "PACIFICA SALUD" and procedencia == "CENTRAL DE ESTERILIZACION":
    TIPOS = ["BANDEJAS", "INSTRUMENTAL", "LENTES", "MISCELANEOS", "ROBOT", "PRUEBA"]

elif entidad == "PROVEEDOR EXTERNO":
    TIPOS = ["BANDEJAS", "INSTRUMENTAL", "INSUMO", "LENTES"]

else:
    TIPOS = ["BANDEJAS", "INSTRUMENTAL", "INSUMO", "MISCELANEOS"]

with col1:
    tipo = st.selectbox("Tipo *", TIPOS)
    cantidad = st.number_input("Cantidad *", min_value=1, max_value=9999, value=1, step=1)
    


clave_especifica = (entidad, procedencia, tipo)
clave_general = (entidad, None, tipo)

if clave_especifica in CONFIG_DETALLE:
    config = CONFIG_DETALLE[clave_especifica]
    tabla, columna, columna_filtro, _ = config
    if columna_filtro is None:
        DETALLE = cargar_opciones(tabla, columna)
    else:
        DETALLE = cargar_opciones_filtradas(tabla, columna, columna_filtro=columna_filtro, valor_filtro=procedencia)
        
elif clave_general in CONFIG_DETALLE:
    config = CONFIG_DETALLE[clave_general]
    tabla, columna, columna_filtro, _ = config
    DETALLE = cargar_opciones_filtradas(tabla, columna, columna_filtro=columna_filtro, valor_filtro=procedencia)
    
else:
    DETALLE = [""]



with col2:
    detalle = st.selectbox("Detalle *", DETALLE + ["NO ENLISTADO"])
    if clave_especifica in CONFIG_DETALLE:
        config = CONFIG_DETALLE[clave_especifica]
        tabla, columna, columna_filtro, _ = config
        if columna_filtro is None:
            CODIGO = cargar_opciones_filtradas(tabla, 1, columna_filtro=0, valor_filtro=detalle)
            UBICACION = cargar_opciones_filtradas(tabla, 2, columna_filtro=0, valor_filtro=detalle)
            
    elif clave_general in CONFIG_DETALLE:
        config = CONFIG_DETALLE[clave_general]
        tabla, columna, columna_filtro, _ = config
        CODIGO = cargar_opciones_filtradas(tabla, 1, columna_filtro=0, valor_filtro=detalle)
        UBICACION = cargar_opciones_filtradas(tabla, 2, columna_filtro=0, valor_filtro=detalle)
        
    else:
        CODIGO = [""]
        UBICACION = [""]

    default_index = next((i for i, val in enumerate(CODIGO) if val != ""), 0)
    default_index_ubicacion = next((i for i, val in enumerate(UBICACION) if val != ""), 0)

    if st.session_state.get("limpiar_comentario", False):
        st.session_state["comentario_input"] = ""
        st.session_state["vencido_input"] = False
        st.session_state["limpiar_comentario"] = False


    comentario = st.text_input("Comentario", value="",key="comentario_input", placeholder="Escribir comentario")

with col1:
    vencido = st.checkbox("VENCIDO", key="vencido_input")


with col3:
    codigo = st.selectbox("Codigo *", CODIGO, index=default_index)
    ubicacion = st.selectbox("Ubicacion *", UBICACION, index=default_index_ubicacion)

    
st.markdown('</div>', unsafe_allow_html=True)

    # ─── SECCIÓN 3: Proceso ─────────────────────────────────────────────────
st.markdown('<div class="form-section"><h4>⚙️ Proceso</h4>', unsafe_allow_html=True)

# Ahora proceso con ciclo automático
col1, col2, col3 = st.columns(3)
with col1:
    if st.session_state.get("limpiar_maquina", False):
            st.session_state["maquina_input"] = []
            st.session_state["limpiar_maquina"] = False

    maquina = st.selectbox("Máquina *", MAQUINAS, key= "maquina_input")
    
    # Detectar cambio de máquina y actualizar ciclo
    if "ultima_maquina" not in st.session_state:
        st.session_state.ultima_maquina = ""
    
    if maquina != st.session_state.ultima_maquina:
        st.session_state.ultima_maquina = maquina
        if maquina:
            st.session_state.ciclo_sugerido = obtener_ultimo_ciclo(maquina, fecha)
        else:
            st.session_state.ciclo_sugerido = ""
    
    
    if tipo == "PRUEBA":
        empaque = st.selectbox("Empaque *", ["N/A"])
    else:
        empaque = st.selectbox("Empaque *", EMPAQUES)

    
    operario = st.selectbox("Operario *", OPERARIOS)
    
    


with col2:

    valor_ciclo = st.session_state.get("ciclo_sugerido", "")
    if tipo == "PRUEBA":
        ciclo = st.text_input("Ciclo *", value="N/A")
    else:
        ciclo = st.text_input("Carga *", value=valor_ciclo, placeholder="Ej: 3")
    

    if tipo == "PRUEBA":
        especialidad = st.selectbox("Especialidad *", ["N/A"])
    else:
        especialidad = st.selectbox("Especialidad *", ESPECIALIDADES)

with col3:
   
    
    # Valor por defecto del ciclo
    if tipo == "PRUEBA":
        tipociclo = st.selectbox("Tipo de ciclo", ["PRUEBA BOWIE-DICK"])
    elif maquina == "100NX":
        tipociclo = st.selectbox("Tipo de ciclo", CICLOSTERRA)
    else:
        tipociclo = st.selectbox("Tipo de ciclo", TIPOCICLO)
    
    if tipo == "PRUEBA":
        servicio_esterilizacion = st.selectbox("Servicio de esterilización *", ["N/A"])
    else:    
        servicio_esterilizacion = st.selectbox("Servicio de esterilización *", SERVICIOS)

    # ─── SECCIÓN 4: Controles de calidad ────────────────────────────────────
st.markdown('<div class="form-section"><h4>🔬 Controles de Calidad</h4>', unsafe_allow_html=True)
if tipo == "PRUEBA":
    RESULTADOS = "N/A"
    PROTEINAS = "N/A"

col1, col2, col3 = st.columns(3)
with col1:
    prueba_temperatura   = st.selectbox("Prueba de temperatura", RESULTADOS)
    prueba_proteinas     = st.selectbox("Prueba de proteinas de arrastre", RESULTADOS)
with col2:
    prueba_luminiscencia = st.selectbox("Prueba de proteinas de residuo", RESULTADOS)
    prueba_biologica     = st.selectbox("Prueba biológica",        RESULTADOS)
with col3:
    indicador_quimico    = st.selectbox("Indicador químico interno",       RESULTADOS)
    indicador_externo    = st.selectbox("Indicador químico externo",       RESULTADOS)
st.markdown('</div>', unsafe_allow_html=True)


with st.form("formulario_registro", clear_on_submit=True):


    
    # ─── BOTÓN DE ENVÍO ──────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    submitted = st.form_submit_button("💾 Guardar Registro", type="primary")



# ─── PROCESAMIENTO ──────────────────────────────────────────────────────────
lote = generar_lote(maquina, ciclo, operario, fecha)
vigencia = MATERIALES.get(empaque, 0)
vencimiento = date.today() + timedelta(days=vigencia)
estado = "SI" if vencido else "NO"
st.session_state["lote"] = lote


if submitted:

    hash_actual = hash_registro_preview()

    duplicado = st.session_state.get("ultimo_hash") == hash_actual

    if duplicado:
        st.warning("⚠️ Este registro ya fue guardado")

    # Validar campos obligatorios
    campos_requeridos = {
        "Sede": sede,
        "Entidad": entidad,
        "Procedencia": procedencia,
        "Tipo": tipo,
        "Detalle": detalle.strip(),
        "Empaque": empaque,
        "Máquina": maquina,
        "Operario": operario,
        "Especialidad": especialidad,
        "Servicio de esterilización": servicio_esterilizacion,
        "Ciclo": ciclo.strip(),
    }
    
    vacios = [k for k, v in campos_requeridos.items() if not v]
    
    if tipo == "ROBOT" and not comentario.strip():
        st.error("⚠️ **Comentario obligatorio:** Debe registrar el número de serie del instrumento en el campo comentario")
    
    elif detalle.strip().upper() == "NO ENLISTADO" and not comentario.strip():
        st.error("⚠️ **Comentario obligatorio:** Artículo no enlistado, debe describir el artículo en el campo comentario")
    
    elif vacios:
        st.error(f"⚠️ Los siguientes campos son obligatorios: **{', '.join(vacios)}**")
    
    else:
        lote = generar_lote(maquina, ciclo, operario, fecha)

        datos = {
            "sede": sede,
            "entidad": entidad,
            "procedencia": procedencia,
            "tipo": tipo,
            "vencido": estado,
            "detalle": detalle.strip(),
            "comentario": comentario,
            "codigo": codigo,
            "ubicacion": ubicacion,
            "tipociclo": tipociclo,
            "empaque": empaque,
            "maquina": maquina,
            "operario": operario,
            "especialidad": especialidad,
            "servicio_esterilizacion": servicio_esterilizacion,
            "fecha": str(fecha),
            "hora": str(hora),
            "cantidad": cantidad,
            "ciclo": ciclo.strip(),
            "lote": lote,
            "vencimiento": vencimiento,
            "prueba_temperatura": prueba_temperatura,
            "prueba_proteinas": prueba_proteinas,
            "prueba_luminiscencia": prueba_luminiscencia,
            "prueba_biologica": prueba_biologica,
            "indicador_quimico": indicador_quimico,
            "indicador_externo": indicador_externo,
        }

        try:
            # 🔥 SOLO guarda si NO es duplicado
            if not duplicado:
                insertar_registro(datos)
                st.session_state.ultimo_hash = hash_actual

            # ✅ SIEMPRE genera salida visual
            st.session_state.ultimo_registro = datos
            st.session_state.registro_guardado = True
            st.session_state["limpiar_comentario"] = True
            st.session_state["limpiar_maquina"] = True
            

            

            

            st.rerun()

        except Exception as e:
            st.error(f"❌ Error al guardar: {e}")
# ─── MOSTRAR ETIQUETA SI HAY REGISTRO GUARDADO ──────────────────────────────
if st.session_state.get("registro_guardado", False):
    datos = st.session_state.ultimo_registro
    tipo = datos.get("tipo", "")
    lote = datos.get("lote", "")
    
    pdf_buffer = generar_etiqueta_pdf(datos, copias=1)
    
    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown('<div class="subtitulo">🏷️ Etiqueta generada</div>', unsafe_allow_html=True)

    with col2:
        st.download_button(
            label="📥 Imprimir Etiqueta",
            data=pdf_buffer,
            file_name=f"{cantidad}_etiqueta_{tipo}_{lote}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    
    
    
 