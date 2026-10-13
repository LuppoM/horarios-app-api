# hgolomodelo.py
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

class ModeloHGoloWeb:
    def __init__(self):
        self.conexion_db = _obtener_conexion_local()
        self.operarios_dict = {}
        self.cargar_operarios()

    def cargar_operarios(self):
        cursor = self.conexion_db.cursor()
        cursor.execute("SELECT id, operario FROM modymoi ORDER BY operario ASC")
        rows = cursor.fetchall()
        self.operarios_dict = {row[0]: row[1] for row in rows if row[1]}

    def obtener_operarios(self):
        return self.operarios_dict

    def obtener_sectores_golosinas(self):
        cursor = self.conexion_db.cursor()
        try:
            cursor.execute(
                "SELECT nombre_sector, tipo_horario, requiere_dotacion FROM sectores WHERE planta='Golosinas'"
            )
            return cursor.fetchall() or []
        except Exception as e:
            print(f"Error al obtener sectores: {e}")
            return []

    def obtener_turnos_por_tipo(self, tipo_horario):
        cursor = self.conexion_db.cursor()
        try:
            cursor.execute(
                "SELECT horarios_definidos FROM tipohorario WHERE UPPER(TRIM(tipo)) = ?",
                (tipo_horario.upper(),)
            )
            row = cursor.fetchone()
            if row and row[0]:
                return [t.strip() for t in row[0].split(",")]
        except Exception as e:
            print(f"Error al obtener turnos: {e}")
        return []

    def obtener_dotacion_teorica(self, semana):
        cursor = self.conexion_db.cursor()
        try:
            cursor.execute(
                """
                    SELECT sector, rango_horario, cantidad_operarios
                    FROM dotacion_teorica_horarios
                    WHERE semana_inicio=? AND planta='Golosinas'
                """,
                (str(semana),),
            )
            resultados = {}
            for sector, rango, cantidad in cursor.fetchall():
                if sector not in resultados:
                    resultados[sector] = {}
                resultados[sector][rango] = cantidad
            return resultados
        except Exception as e:
            print(f"Error dotación teórica: {e}")
            return {}

           def obtener_operarios_disponibles(self, semana):
        cursor = self.conexion_db.cursor()
        cursor.execute("""
            SELECT id, operario
            FROM modymoi
            WHERE operario IS NOT NULL AND TRIM(operario) != ''
              AND NOT (
                  semana = ?
                  AND sector IS NOT NULL AND TRIM(sector) != ''
                  AND LOWER(TRIM(planta)) NOT IN ('golosinas', 'golosina')
              )
            ORDER BY operario ASC
        """, (str(semana),))
        return cursor.fetchall()

    def obtener_datos_semana(self, semana):
        cursor = self.conexion_db.cursor()
        cursor.execute(
            """
                SELECT id, operario, horario, sector
                FROM modymoi
                WHERE semana=? AND LOWER(TRIM(planta)) = 'golosinas'
                  AND sector IS NOT NULL AND TRIM(sector) != ''
            """,
            (str(semana),),
        )
        return cursor.fetchall()

    def guardar_datos_semana(self, semana, registros_pantalla):
        cursor = self.conexion_db.cursor()
        sem_val = str(semana).strip()

        cursor.execute(
            """
            SELECT id 
            FROM modymoi 
            WHERE semana = ? AND LOWER(TRIM(planta)) = 'golosinas'
            """,
            (sem_val,),
        )
        ids_previos_en_bd = set(row[0] for row in cursor.fetchall())
        ids_actuales_en_pantalla = set(r[0] for r in registros_pantalla)
        ids_a_limpiar = ids_previos_en_bd - ids_actuales_en_pantalla

        for id_old in ids_a_limpiar:
            cursor.execute(
                "UPDATE modymoi SET horario='', sector='', planta='' WHERE id=?",
                (id_old,)
            )

        for id_op, operario_nombre, turno, sector in registros_pantalla:
            cursor.execute(
                """
                    UPDATE modymoi
                    SET operario=?, horario=?, sector=?, planta='Golosinas', semana=?
                    WHERE id=?
                """,
                (operario_nombre, turno, sector, sem_val, id_op),
            )

        self.conexion_db.commit()

    def cerrar_conexion(self):
        if self.conexion_db:
            self.conexion_db.close()
