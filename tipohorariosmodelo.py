import os
import sqlite3
import sys

def _obtener_conexion_local():
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_path, "HORARIOS.db")
    return sqlite3.connect(db_path, check_same_thread=False)

def obtener_tipos_horarios():
    conn = _obtener_conexion_local()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, tipo, horarios_definidos
        FROM tipohorario
    """)
    filas = cursor.fetchall()
    conn.close()
    return filas

def obtener_tipo_horario_por_id(tipo_id):
    conn = _obtener_conexion_local()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, tipo, horarios_definidos
        FROM tipohorario
        WHERE id = ?
    """, (tipo_id,))
    fila = cursor.fetchone()
    conn.close()
    if not fila:
        return None
    return {
        "id": fila[0],
        "tipo": fila[1],
        "horarios_definidos": fila[2]
    }

def insertar_tipo_horario(datos):
    conn = _obtener_conexion_local()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tipohorario (tipo, horarios_definidos)
        VALUES (?, ?)
    """, (datos.get("tipo"), datos.get("horarios_definidos")))
    conn.commit()
    conn.close()

def modificar_tipo_horario(tipo_id, datos):
    conn = _obtener_conexion_local()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE tipohorario
        SET tipo = ?, horarios_definidos = ?
        WHERE id = ?
    """, (datos.get("tipo"), datos.get("horarios_definidos"), tipo_id))
    conn.commit()
    conn.close()

def eliminar_tipo_horario(tipo_id):
    conn = _obtener_conexion_local()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tipohorario WHERE id = ?", (tipo_id,))
    conn.commit()
    conn.close()