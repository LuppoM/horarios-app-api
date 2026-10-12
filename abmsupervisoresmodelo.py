import sqlite3

def insertar_supervisor(conexion, nombre, email, planta):
    cursor = conexion.cursor()
    cursor.execute("""
        INSERT INTO supervisores (nombre, email, planta)
        VALUES (?, ?, ?)
    """, (nombre, email, planta))
    conexion.commit()

def modificar_supervisor(conexion, supervisor_id, nombre, email, planta):
    cursor = conexion.cursor()
    cursor.execute("""
        UPDATE supervisores
        SET nombre = ?, email = ?, planta = ?
        WHERE id = ?
    """, (nombre, email, planta, supervisor_id))
    conexion.commit()