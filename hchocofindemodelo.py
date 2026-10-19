import conexion

class ModeloHChocoFindeWeb:
    def __init__(self, conexion_db=None):
        if conexion_db:
            self.conexion_db = conexion_db
        else:
            self.conexion_db = conexion.obtener_conexion_supabase()
        self.planta = "Chocolates"

    def obtener_operarios_disponibles(self, semana):
        """Obtiene los operarios disponibles para Chocolates desde Supabase."""
        cursor = self.conexion_db.cursor()
        try:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()

            sem_val = str(semana) if semana else ""

            # Filtra operarios que pertenecen a Chocolates y no tienen Sector asignado
            cursor.execute(
                """
                SELECT DISTINCT m.id, m.operario
                FROM modymoi m
                WHERE m.semana::text = %s
                  AND (LOWER(TRIM(m."Planta")) = 'chocolates' OR m."Planta" IS NULL OR TRIM(m."Planta") = '')
                  AND (m."Sector" IS NULL OR TRIM(m."Sector") = '')
                ORDER BY m.operario ASC
                """,
                (sem_val,)
            )
            filas = cursor.fetchall()
            return [(f[0], f[1]) if isinstance(f, (list, tuple)) else (f.get("id"), f.get("operario")) for f in filas]

        except Exception as e:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            print(f"Error al obtener operarios disponibles en Supabase: {e}")
            return []

    def obtener_sectores(self):
        """Obtiene los sectores de la planta Chocolates desde Supabase."""
        cursor = self.conexion_db.cursor()
        try:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()

            cursor.execute(
                """
                SELECT nombre_sector 
                FROM sectores 
                WHERE LOWER(TRIM(planta)) = 'chocolates' 
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
        """Lee las asignaciones guardadas de Chocolates en la tabla modymoi_finde en Supabase."""
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
                  AND (LOWER(TRIM(f.planta)) = 'chocolates' OR f.planta IS NULL OR TRIM(f.planta) = '')
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
        """Borra y reinserta las asignaciones de fin de semana para Chocolates en Supabase."""
        cursor = self.conexion_db.cursor()
        try:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()

            sem_val = int(semana) if str(semana).isdigit() else semana

            # 1. Limpiar registros anteriores de esta semana para Chocolates
            cursor.execute(
                """
                DELETE FROM modymoi_finde
                WHERE semana::text = %s
                  AND (LOWER(TRIM(planta)) = 'chocolates' OR planta IS NULL OR TRIM(planta) = '')
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