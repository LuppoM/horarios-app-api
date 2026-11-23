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
    def _filas(self, cursor):
        filas = cursor.fetchall()
        if not filas:
            return []
        if isinstance(filas[0], dict):
            return [tuple(f.values()) for f in filas]
        return filas

    def obtener_sectores_mantenimiento(self, planta=None):
        """Obtiene sectores del área MANTENIMIENTO desde la tabla sectores."""
        cursor = self.conexion_db.cursor()
        try:
            if planta:
                cursor.execute(
                    """
                    SELECT nombre_sector, tipo_horario, requiere_dotacion, planta
                    FROM sectores
                    WHERE LOWER(TRIM(COALESCE(area, ''))) IN ('mantenimiento', 'mecánicos', 'mecanicos')
                      AND LOWER(TRIM(COALESCE(planta, ''))) = LOWER(TRIM(%s))
                    ORDER BY id ASC;
                    """,
                    (planta,)
                )
            else:
                cursor.execute(
                    """
                    SELECT nombre_sector, tipo_horario, requiere_dotacion, planta
                    FROM sectores
                    WHERE LOWER(TRIM(COALESCE(area, ''))) IN ('mantenimiento', 'mecánicos', 'mecanicos')
                    ORDER BY id ASC;
                    """
                )
            return self._filas(cursor)
        except Exception as e:
            print(f"Error al obtener sectores de mantenimiento: {e}")
            return []

    def obtener_turnos_por_tipo(self, tipo_horario):
        """Obtiene los horarios/turnos asociados a un tipo_horario."""
        cursor = self.conexion_db.cursor()
        tipo_norm = str(tipo_horario or "ROTATIVO").strip().upper()
        try:
            cursor.execute(
                """
                SELECT horarios_definidos
                FROM tipos_horario
                WHERE UPPER(TRIM(tipo)) = %s
                LIMIT 1;
                """,
                (tipo_norm,)
            )
            fila = cursor.fetchone()
            if not fila:
                return []
            raw = fila[0] if not isinstance(fila, dict) else fila.get("horarios_definidos")
            if isinstance(raw, list):
                return [str(x).strip() for x in raw if str(x).strip()]
            if isinstance(raw, str):
                # Soporta texto separado por coma, salto de línea o punto y coma
                for sep in ["\n", ";", ","]:
                    if sep in raw:
                        return [p.strip() for p in raw.split(sep) if p.strip()]
                return [raw.strip()] if raw.strip() else []
            return []
        except Exception as e:
            print(f"Error al obtener turnos para tipo {tipo_norm}: {e}")
            return []            