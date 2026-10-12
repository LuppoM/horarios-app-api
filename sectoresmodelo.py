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

def obtener_sectores():
    conn = _obtener_conexion_local()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, nombre_sector, planta, tipo_horario, requiere_dotacion
        FROM sectores
    """)
    filas = cursor.fetchall()
    conn.close()
    return filas

def obtener_sector_por_id(sector_id):
    conn = _obtener_conexion_local()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, nombre_sector, planta, tipo_horario, requiere_dotacion
        FROM sectores
        WHERE id = ?
    """, (sector_id,))
    fila = cursor.fetchone()
    conn.close()
    if not fila:
        return None
    return {
        "id": fila[0],
        "nombre_sector": fila[1],
        "planta": fila[2],
        "tipo_horario": fila[3],
        "requiere_dotacion": fila[4]
    }

def obtener_tipos_horario():
    conn = _obtener_conexion_local()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT tipo FROM tipohorario ORDER BY tipo ASC")
        filas = cursor.fetchall()
        return [f[0] for f in filas]
    except Exception:
        return ["ROTATIVO", "CENTRAL"]
    finally:
        conn.close()

def insertar_sector(datos):
    conn = _obtener_conexion_local()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sectores (nombre_sector, planta, tipo_horario, requiere_dotacion)
        VALUES (?, ?, ?, ?)
    """, (datos.get("nombre_sector"), datos.get("planta"), datos.get("tipo_horario"), datos.get("requiere_dotacion")))
    conn.commit()
    conn.close()

def modificar_sector(sector_id, datos):
    conn = _obtener_conexion_local()
    cursor = conn.cursor()
    try:
        # Extraemos los valores asegurando compatibilidad con distintas nomenclaturas
        nombre_sector = datos.get("nombre_sector") or datos.get("nombre")
        planta = datos.get("planta")
        tipo_horario = datos.get("tipo_horario")
        
        # Aseguramos que requiere_dotacion sea un entero (1 o 0)
        req_dot = datos.get("requiere_dotacion", 1)
        if isinstance(req_dot, str):
            requiere_dotacion = 1 if req_dot.lower() in ["1", "true", "si", "on"] else 0
        else:
            requiere_dotacion = int(req_dot)

        cursor.execute("""
            UPDATE sectores
            SET nombre_sector = ?, planta = ?, tipo_horario = ?, requiere_dotacion = ?
            WHERE id = ?
        """, (nombre_sector, planta, tipo_horario, requiere_dotacion, sector_id))
        
        conn.commit()
        return True, "Modificación exitosa"
    except Exception as e:
        conn.rollback()
        print(f"Error al modificar sector {sector_id}: {e}")
        return False, str(e)
    finally:
        conn.close()

def eliminar_sector(sector_id):
    conn = _obtener_conexion_local()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sectores WHERE id = ?", (sector_id,))
    conn.commit()
    conn.close()