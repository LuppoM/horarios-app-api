import conexion

class ModeloMecanicosWeb:

    def __init__(self):
        self.conexion_db = conexion.obtener_conexion()

    def obtener_mecanicos_disponibles(self):
        """Obtiene el listado completo de personal de mantenimiento desde la tabla modymoi."""
        cursor = self.conexion_db.cursor()
        cursor.execute(
            """
            SELECT id, operario 
            FROM modymoi 
            WHERE LOWER(TRIM("Sector")) LIKE '%mantenimiento%' 
               OR LOWER(TRIM("Sector")) LIKE '%mecanico%'
               OR LOWER(TRIM(calificacion_mano_obra)) = 'moi'
            ORDER BY operario ASC
            """
        )
        filas = cursor.fetchall()
        
        mecanicos = []
        for f in filas:
            if isinstance(f, dict):
                mecanicos.append([f.get("id"), f.get("operario")])
            else:
                mecanicos.append([f[0], f[1]])
        return mecanicos

    def obtener_asignaciones_semana(self, semana):
        """Obtiene las asignaciones actuales de la semana para los mecánicos."""
        cursor = self.conexion_db.cursor()
        sem_val = int(semana) if str(semana).isdigit() else semana
        cursor.execute(
            """
            SELECT id, operario, "Horario", "Sector", "Planta"
            FROM modymoi
            WHERE (semana::text = %s OR semana = %s)
              AND "Horario" IS NOT NULL AND TRIM("Horario") != ''
              AND (
                  LOWER(TRIM("Sector")) LIKE '%mantenimiento%' 
                  OR LOWER(TRIM("Sector")) LIKE '%mecanico%'
                  OR LOWER(TRIM(calificacion_mano_obra)) = 'moi'
              )
            ORDER BY "Horario" ASC, operario ASC
            """,
            (str(semana), sem_val),
        )
        filas = cursor.fetchall()

        datos = []
        for f in filas:
            if isinstance(f, dict):
                datos.append([f.get("id"), f.get("operario"), f.get("Horario"), f.get("Sector"), f.get("Planta")])
            else:
                datos.append([f[0], f[1], f[2], f[3], f[4]])
        return datos

    def guardar_asignaciones_mecanicos(self, semana, registros):
        """
        registros: lista de tuplas/listas -> [[id_mecanico, horario, sector, planta], ...]
        """
        cursor = self.conexion_db.cursor()
        sem_val = int(semana) if str(semana).isdigit() else semana

        # Primero limpiamos las asignaciones viejas de la semana para mecánicos
        cursor.execute(
            """
            UPDATE modymoi
            SET "Horario" = NULL, "Sector" = NULL
            WHERE semana::text = %s
              AND (
                  LOWER(TRIM("Sector")) LIKE '%mantenimiento%' 
                  OR LOWER(TRIM("Sector")) LIKE '%mecanico%'
                  OR LOWER(TRIM(calificacion_mano_obra)) = 'moi'
              )
            """,
            (str(semana),)
        )

        # Insertamos/Actualizamos los nuevos
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
