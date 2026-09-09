import sqlite3
import pandas as pd
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "esterilizacion.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sede TEXT,
            entidad TEXT,
            procedencia TEXT,
            tipo TEXT,
            detalle TEXT,
            comentario TEXT,
            codigo INTEGER,
            ubicacion TEXT,    
            empaque TEXT,
            maquina TEXT,
            operario TEXT,
            especialidad TEXT,
            servicio_esterilizacion TEXT,
            fecha TEXT,
            hora TEXT,
            cantidad INTEGER,
            tipo_de_ciclo TEXT,
            carga TEXT,
            lote TEXT,
            vencimiento TEXT,
            prueba_temperatura TEXT,
            prueba_de_proteinas_de_arrastre TEXT,
            prueba_de_proteinas_de_residuo TEXT,
            prueba_biologica TEXT,
            indicador_quimico TEXT,
            indicador_externo TEXT,
            vencido TEXT,
            Estado_del_Ciclo TEXT,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    con.commit()
    con.close()
def insertar_registro(datos: dict):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO registros (
            sede, entidad, procedencia, tipo, detalle, comentario, codigo, ubicacion, empaque,
            maquina, operario, especialidad, servicio_esterilizacion,
            fecha, hora, cantidad, tipo_de_ciclo, carga, lote, vencimiento,
            prueba_temperatura, prueba_de_proteinas_de_arrastre, prueba_de_proteinas_de_residuo,
            prueba_biologica, indicador_quimico, indicador_externo, vencido
        ) VALUES (
            :sede, :entidad, :procedencia, :tipo, :detalle, :comentario, :codigo, :ubicacion, :empaque,
            :maquina, :operario, :especialidad, :servicio_esterilizacion,
            :fecha, :hora, :cantidad, :tipociclo, :ciclo, :lote, :vencimiento,
            :prueba_temperatura, :prueba_proteinas, :prueba_luminiscencia,
            :prueba_biologica, :indicador_quimico, :indicador_externo, :vencido
        )
    """, datos)
    con.commit()
    con.close()

def cargar_registros():
    con = get_connection()
    df = pd.read_sql("SELECT * FROM registros ORDER BY fecha_registro DESC", con)
    con.close()
    return df

def eliminar_registro(id: int):
    con = get_connection()
    cur = con.cursor()
    cur.execute("DELETE FROM registros WHERE id = ?", (id,))
    con.commit()
    con.close()

def actualizar_registro(id: int, datos: dict):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        UPDATE registros SET
            sede=:sede, entidad=:entidad, procedencia=:procedencia,
            tipo=:tipo, detalle=:detalle, comentario=:comentario, codigo=:codigo, ubicacion=:ubicacion, empaque=:empaque,
            maquina=:maquina, operario=:operario, especialidad=:especialidad,
            servicio_esterilizacion=:servicio_esterilizacion,
            fecha=:fecha, hora=:hora, cantidad=:cantidad, tipo_de_ciclo=:tipociclo, carga=:ciclo, lote=:lote, vencimiento=:vencimiento,
            prueba_temperatura=:prueba_temperatura,
            prueba_de_proteinas_de_arrastre=:prueba_proteinas,
            prueba_de_proteinas_de_residuo=:prueba_luminiscencia,
            prueba_biologica=:prueba_biologica,
            indicador_quimico=:indicador_quimico,
            indicador_externo=:indicador_externo,
            vencido =:vencido
        WHERE id=:id
    """, {**datos, "id": id})
    con.commit()
    con.close()

# Inicializa la BD al importar
init_db()
