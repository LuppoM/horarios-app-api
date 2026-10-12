import sqlite3
import sqlite3

def insertar_tipo_horario(conexion, tipo, horarios):
    cursor = conexion.cursor()
    cursor.execute("""
        INSERT INTO tipohorario (tipo, horarios_definidos)
        VALUES (?, ?)
    """, (tipo, horarios))
    conexion.commit()

def modificar_tipo_horario(conexion, tipo_id, tipo, horarios):
    cursor = conexion.cursor()
    cursor.execute("""
        UPDATE tipohorario
        SET tipo = ?, horarios_definidos = ?
        WHERE id = ?
    """, (tipo, horarios, tipo_id))
    conexion.commit()