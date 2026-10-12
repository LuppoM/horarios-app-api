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

class ModeloHChocoFindeWeb:
    def __init__(self):
        self.conexion_db = _obtener_conexion_local()
        self.planta = "Chocolates"

    def obtener_operarios_disponibles(self, semana):
        cursor = self.conexion_db.cursor()
        sem_val = int(semana) if str(semana).isdigit() else semana
        cursor.execute(
            """
            SELECT DISTINCT m.id, m.operario
            FROM modymoi m
            WHERE (m.semana = ? OR m.semana = ?)
              AND (LOWER(TRIM(m.planta)) = 'chocolates' OR m.planta IS NULL OR TRIM(m.planta) = '')
              AND m.horario IS NOT NULL AND TRIM(m.horario) != ''
              AND m.sector IS NOT NULL AND TRIM(m.sector) != ''
            ORDER BY m.operario ASC
            """,
            (str(semana), sem_val),
        )
        return cursor.fetchall()

    def obtener_datos_semana_finde(self, semana):
        cursor = self.conexion_db.cursor()
        sem_val = int(semana) if str(semana).isdigit() else semana
        cursor.execute(
            """
            SELECT f.id_operario, m.operario, f.dia, f.horario, f.sector
            FROM modymoi_finde f
            LEFT JOIN modymoi m ON f.id_operario = m.id
            WHERE (f.semana = ? OR f.semana = ?)
              AND (LOWER(TRIM(f.planta)) = 'chocolates' OR f.planta IS NULL OR TRIM(f.planta) = '')
            ORDER BY f.id ASC
            """,
            (str(semana), sem_val),
        )
        return cursor.fetchall()

    def guardar_datos_finde(self, semana, registros):
        cursor = self.conexion_db.cursor()
        sem_val = int(semana) if str(semana).isdigit() else semana

        # Borrado preciso para esta semana y planta (Chocolates)
        cursor.execute(
            """
            DELETE FROM modymoi_finde
            WHERE semana = ?
              AND (LOWER(TRIM(planta)) = 'chocolates' OR planta IS NULL OR TRIM(planta) = '')
            """,
            (str(semana),),
        )

        for id_op, dia, horario, sector in registros:
            cursor.execute(
                """
                INSERT INTO modymoi_finde (id_operario, semana, dia, horario, sector, planta)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (id_op, sem_val, dia, horario, sector, self.planta),
            )

        self.conexion_db.commit()

    def cerrar_conexion(self):
        if self.conexion_db:
            try:
                self.conexion_db.close()
            except Exception:
                pass