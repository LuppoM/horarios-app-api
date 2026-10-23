import conexion

class ModeloHGoloFindeWeb:
    def __init__(self, conexion_db=None):
        if conexion_db:
            self.conexion_db = conexion_db
        else:
            self.conexion_db = conexion.obtener_conexion()
        self.planta = "Golosinas"

    def obtener_operarios_disponibles(self, semana=None):
        """Devuelve todos los operarios para asignación de fin de semana (INSERT en modymoi_finde)."""
        cursor = self.conexion_db.cursor()
        try:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()

            # Definimos las plantas que querés incluir (en minúsculas para coincidir con LOWER)
            plantas_filtro = ('chocolates', 'golosinas')  # Cambia 'golosinas' si en la BD se guarda distinto (ej. 'golosinas oenp')

            # Usamos IN %s pasándole la tupla de plantas
            cursor.execute(
                """
                SELECT DISTINCT id, operario
                FROM modymoi
                WHERE operario IS NOT NULL 
                  AND TRIM(operario) != ''
                  AND (LOWER(TRIM("Planta")) IN %s OR "Planta" IS NULL OR TRIM("Planta") = '')
                  AND (%s IS NULL OR semana = %s)
                ORDER BY operario ASC
                """,
                (plantas_filtro, semana, semana)
            )
            filas = cursor.fetchall()

            resultado = []
            for f in filas:
                if isinstance(f, dict):
                    resultado.append((f.get("id"), f.get("operario")))
                else:
                    resultado.append((f[0], f[1]))

            return resultado

        except Exception as e:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            print(f"Error al obtener operarios para fin de semana en Supabase: {e}")
            return []

    def obtener_sectores(self):
        """Obtiene los sectores de la planta Golosinas desde Supabase."""
        cursor = self.conexion_db.cursor()
        try:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()

            cursor.execute(
                """
                SELECT nombre_sector 
                FROM sectores 
                WHERE LOWER(TRIM(planta)) = 'golosinas' 
                ORDER BY nombre_sector ASC
                """
            )
            filas = cursor.fetchall()
            return [f[0] if isinstance(f, (list, tuple)) else f.get("nombre_sector") for f in filas]

        except Exception as e:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            print(f"Error al obtener sectores en Supabase: {e}")
            return []

    def obtener_datos_semana_finde(self, semana):
        """Lee las asignaciones guardadas en la tabla modymoi_finde en Supabase."""
        cursor = self.conexion_db.cursor()
        try:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()

            sem_val = str(semana) if semana else ""

            cursor.execute(
                """
                SELECT f.id_operario, m.operario, f.dia, f.horario, f.sector
                FROM modymoi_finde f
                LEFT JOIN modymoi m ON f.id_operario = m.id
                WHERE f.semana::text = %s
                  AND (LOWER(TRIM(f.planta)) = 'golosinas' OR f.planta IS NULL OR TRIM(f.planta) = '')
                ORDER BY f.id ASC
                """,
                (sem_val,)
            )
            filas = cursor.fetchall()
            
            resultado = []
            for f in filas:
                if isinstance(f, dict):
                    resultado.append([f.get("id_operario"), f.get("operario"), f.get("dia"), f.get("horario"), f.get("sector")])
                else:
                    resultado.append([f[0], f[1], f[2], f[3], f[4]])

            return resultado

        except Exception as e:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            print(f"Error al consultar modymoi_finde en Supabase: {e}")
            return []

    def guardar_datos_finde(self, semana, registros):
        """Borra y reinserta las asignaciones de fin de semana para Golosinas en Supabase."""
        cursor = self.conexion_db.cursor()
        try:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()

            sem_val = int(semana) if str(semana).isdigit() else semana

            # 1. Limpiar registros anteriores de esta semana y esta planta
            cursor.execute(
                """
                DELETE FROM modymoi_finde
                WHERE semana::text = %s
                  AND (LOWER(TRIM(planta)) = 'golosinas' OR planta IS NULL OR TRIM(planta) = '')
                """,
                (str(semana),)
            )

            # 2. Insertar los nuevos registros
            for id_op, dia, horario, sector in registros:
                cursor.execute(
                    """
                    INSERT INTO modymoi_finde (id_operario, semana, dia, horario, sector, planta)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (int(id_op), sem_val, str(dia), str(horario), str(sector), self.planta)
                )

            self.conexion_db.commit()
            return True

        except Exception as e:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            print(f"Error al guardar datos de fin de semana en Supabase: {e}")
            raise Exception(f"Error al guardar en Supabase: {e}")

    def cerrar_conexion(self):
        if hasattr(self, 'conexion_db') and self.conexion_db:
            try:
                self.conexion_db.close()
            except Exception:
                pass
