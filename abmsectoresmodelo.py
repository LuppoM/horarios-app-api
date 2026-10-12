import sqlite3

def obtener_tipos_horario(conexion):
    """Consulta la tabla tipohorario y retorna una lista con todos los nombres de 'tipo'."""
    cursor = conexion.cursor()
    try:
        cursor.execute("SELECT tipo FROM tipohorario ORDER BY tipo ASC")
        filas = cursor.fetchall()
        return [f[0] for f in filas]
    except Exception as e:
        print(f"Error al obtener tipos de horario: {e}")
        return []

def insertar_sector(conexion, nombre, planta, tipo_horario, requiere_dotacion):
    cursor = conexion.cursor()
    cursor.execute("""
        INSERT INTO sectores (nombre_sector, planta, tipo_horario, requiere_dotacion)
        VALUES (?, ?, ?, ?)
    """, (nombre, planta, tipo_horario, requiere_dotacion))
    conexion.commit()

def modificar_sector(conexion, sector_id, nombre, planta, tipo_horario, requiere_dotacion):
    cursor = conexion.cursor()
    cursor.execute("""
        UPDATE sectores
        SET nombre_sector = ?, planta = ?, tipo_horario = ?, requiere_dotacion = ?
        WHERE id = ?
    """, (nombre, planta, tipo_horario, requiere_dotacion, sector_id))
    conexion.commit()