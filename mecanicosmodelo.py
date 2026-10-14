import conexion

class ModeloMecanicosWeb:

    def __init__(self):
        self.conexion_db = conexion.obtener_conexion()

    def obtener_mecanicos_disponibles(self):
        """Obtiene la lista de mecánicos desde la tabla mecanicos."""
        cursor = self.conexion_db.cursor()
        cursor.execute("SELECT id, operario FROM mecanicos ORDER BY operario ASC;")
        filas = cursor.fetchall()
        
        return [[f[0], f[1]] if not isinstance(f, dict) else [f["id"], f["operario"]] for f in filas]

    def obtener_asignaciones_semana(self, semana):
        """Obtiene las asignaciones cargadas para la semana especificada."""
        cursor = self.conexion_db.cursor()
        sem_val = int(semana) if str(semana).isdigit() else semana
        cursor.execute(
            """
            SELECT id, operario, horario, planta
            FROM mecanicos
            WHERE semana = %s AND horario IS NOT NULL AND TRIM(horario) != ''
            ORDER BY horario ASC, operario ASC;
            """,
            (sem_val,)
        )
        filas = cursor.fetchall()
        return [[f[0], f[1], f[2], f[3]] if not isinstance(f, dict) else [f["id"], f["operario"], f["horario"], f["planta"]] for f in filas]

    def guardar_asignaciones_mecanicos(self, semana, registros):
        """
        registros: lista de listas -> [[id_mecanico, horario, planta], ...]
        """
        cursor = self.conexion_db.cursor()
        sem_val = int(semana) if str(semana).isdigit() else semana

        # Limpiamos los horarios de la semana antes de actualizar
        cursor.execute("UPDATE mecanicos SET horario = NULL WHERE semana = %s;", (sem_val,))

        # Guardamos las nuevas asignaciones
        for id_op, horario, planta in registros:
            cursor.execute(
                """
                UPDATE mecanicos
                SET horario = %s, planta = %s, semana = %s
                WHERE id = %s;
                """,
                (horario, planta, sem_val, id_op)
            )

        self.conexion_db.commit()

    def cerrar_conexion(self):
        if hasattr(self, 'conexion_db') and self.conexion_db:
            try:
                self.conexion_db.close()
            except Exception:
                pass
