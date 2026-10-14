import conexion


class ModeloMecanicosWeb:

    def __init__(self):
        self.conexion_db = conexion.obtener_conexion()

    def obtener_mecanicos_asignados(self, semana):
        cursor = self.conexion_db.cursor()
        sem_val = int(semana) if str(semana).isdigit() else semana
        cursor.execute(
            """
            SELECT m.id, m.operario, m."Horario", m."Sector", m."Planta"
            FROM modymoi m
            WHERE (m.semana::text = %s OR m.semana = %s)
              AND (
                LOWER(TRIM(m."Sector")) LIKE '%%mantenimiento%%' 
                OR LOWER(TRIM(m."Sector")) LIKE '%%mecanico%%'
                OR LOWER(TRIM(m.calificacion_mano_obra)) = 'moi'
              )
            ORDER BY m.operario ASC
            """,
            (str(semana), sem_val),
        )
        filas = cursor.fetchall()

        datos = []
        for f in filas:
            if isinstance(f, dict):
                datos.append([
                    f.get("id"),
                    f.get("operario"),
                    f.get("Horario"),
                    f.get("Sector"),
                    f.get("Planta")
                ])
            else:
                datos.append([f[0], f[1], f[2], f[3], f[4]])
        return datos

    def guardar_asignaciones_mecanicos(self, semana, registros):
        """
        registros: lista de listas -> [[id_mecanico, horario, sector, planta], ...]
        """
        cursor = self.conexion_db.cursor()
        sem_val = int(semana) if str(semana).isdigit() else semana

        for id_op, horario, sector, planta in registros:
            cursor.execute(
                """
                UPDATE modymoi
                SET "Horario" = %s,
                    "Sector" = %s,
                    "Planta" = %s,
                    semana = %s
                WHERE id = %s
                """,
                (horario, sector, planta, sem_val, id_op),
            )

        self.conexion_db.commit()

    def cerrar_conexion(self):
        if hasattr(self, 'conexion_db') and self.conexion_db:
            try:
                self.conexion_db.close()
            except Exception:
                pass
