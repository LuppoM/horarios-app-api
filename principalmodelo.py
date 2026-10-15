from datetime import date, datetime, timedelta
import conexion


class modeloprincipal:

    def __init__(self, conexion_db=None):
        if conexion_db:
            self.conexion_db = conexion_db
        else:
            self.conexion_db = conexion.obtener_conexion()

    def obtener_numero_semana_personalizado(self, fecha=None):
        """Calcula el número de semana de producción personalizado."""
        if fecha is None:
            fecha = date.today()
        elif isinstance(fecha, datetime):
            fecha = fecha.date()

        if fecha.weekday() == 6:
            fecha_ajustada = fecha + timedelta(days=1)
        else:
            fecha_ajustada = fecha

        return fecha_ajustada.isocalendar()[1]

    def eliminar_datos_semanas_anteriores(self, semana_actual=None):
        """Limpieza remota sobre Supabase (PostgreSQL).
        Blanquea asignaciones y limites teoricos de semanas estrictamente ANTERIORES (< semana_actual).
        """
        try:
            cursor = self.conexion_db.cursor()

            if semana_actual is None:
                semana_actual = self.obtener_numero_semana_personalizado()

            semana_num = int(semana_actual)

            # 1. Blanquear puestos en la tabla modymoi para semanas anteriores (<)
            cursor.execute(
                """
                UPDATE modymoi
                SET "Horario" = '', 
                    "Sector" = '', 
                    "Planta" = ''
                WHERE semana IS NOT NULL 
                  AND TRIM(CAST(semana AS TEXT)) != ''
                  AND (
                    CASE 
                      WHEN TRIM(CAST(semana AS TEXT)) ~ '^[0-9]+$' 
                      THEN CAST(TRIM(CAST(semana AS TEXT)) AS INTEGER) 
                      ELSE 0 
                    END
                  ) < %s
                """,
                (semana_num,),
            )

            # 2. Eliminar asignaciones registradas del fin de semana para semanas anteriores (<)
            cursor.execute(
                """
                DELETE FROM modymoi_finde
                WHERE semana IS NOT NULL 
                  AND (
                    CASE 
                      WHEN TRIM(CAST(semana AS TEXT)) ~ '^[0-9]+$' 
                      THEN CAST(TRIM(CAST(semana AS TEXT)) AS INTEGER) 
                      ELSE 0 
                    END
                  ) < %s
                """,
                (semana_num,),
            )

            # 3. Eliminar limites de dotacion programada/teorica de semanas anteriores (<)
            cursor.execute(
                """
                DELETE FROM dotacion_teorica_horarios
                WHERE semana_inicio IS NOT NULL 
                  AND (
                    CASE 
                      WHEN TRIM(CAST(semana_inicio AS TEXT)) ~ '^[0-9]+$' 
                      THEN CAST(TRIM(CAST(semana_inicio AS TEXT)) AS INTEGER) 
                      ELSE 0 
                    END
                  ) < %s
                """,
                (semana_num,),
            )

            self.conexion_db.commit()
            print(f"Limpieza ejecutada exitosamente para semanas anteriores a la semana {semana_num}.")

        except Exception as e:
            if hasattr(self, 'conexion_db') and self.conexion_db:
                self.conexion_db.rollback()
            print(f"Error al limpiar semanas anteriores en Supabase: {e}")

    # =========================================================================
    # MÉTODOS PARA LA TABLA dotacion_teorica_horarios
    # =========================================================================

    def obtener_dotacion_teorica(self, semana=None):
        """
        Obtiene los registros de dotación teórica/programada para la semana especificada.
        Si no se pasa semana, calcula la semana actual de producción.
        """
        if semana is None:
            semana = self.obtener_numero_semana_personalizado()

        try:
            cursor = self.conexion_db.cursor()
            query = """
                SELECT id, sector, "06:00 a 14:00", "14:00 a 22:00", "22:00 a 06:00", semana_inicio, planta
                FROM dotacion_teorica_horarios
                WHERE (
                    CASE 
                      WHEN TRIM(CAST(semana_inicio AS TEXT)) ~ '^[0-9]+$' 
                      THEN CAST(TRIM(CAST(semana_inicio AS TEXT)) AS INTEGER) 
                      ELSE 0 
                    END
                ) = %s
                ORDER BY id ASC;
            """
            cursor.execute(query, (int(semana),))
            filas = cursor.fetchall()

            dotaciones = []
            for f in filas:
                dotaciones.append({
                    "id": f[0],
                    "sector": f[1],
                    "turno_06_14": f[2],
                    "turno_14_22": f[3],
                    "turno_22_06": f[4],
                    "semana_inicio": f[5],
                    "planta": f[6] if len(f) > 6 else ""
                })
            return dotaciones

        except Exception as e:
            print(f"Error al obtener dotación teórica para la semana {semana}: {e}")
            return []

    def guardar_dotacion_lote(self, lista_dotaciones, semana=None):
        """
        Guarda o actualiza masivamente los registros de dotación programada para una semana.
        lista_dotaciones: list[dict] -> [{'sector': 'PLANTA DE PASTA', 't06_14': 10, 't14_22': 1, 't22_06': 1, 'planta': 'Chocolates'}, ...]
        """
        if semana is None:
            semana = self.obtener_numero_semana_personalizado()

        try:
            cursor = self.conexion_db.cursor()
            for item in lista_dotaciones:
                query = """
                    INSERT INTO dotacion_teorica_horarios 
                        (sector, "06:00 a 14:00", "14:00 a 22:00", "22:00 a 06:00", semana_inicio, planta)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (sector, semana_inicio) 
                    DO UPDATE SET 
                        "06:00 a 14:00" = EXCLUDED."06:00 a 14:00",
                        "14:00 a 22:00" = EXCLUDED."14:00 a 22:00",
                        "22:00 a 06:00" = EXCLUDED."22:00 a 06:00",
                        planta = EXCLUDED.planta;
                """
                cursor.execute(query, (
                    item.get('sector'),
                    item.get('t06_14', 0),
                    item.get('t14_22', 0),
                    item.get('t22_06', 0),
                    str(semana),
                    item.get('planta', '')
                ))
            self.conexion_db.commit()
            return True

        except Exception as e:
            if hasattr(self, 'conexion_db') and self.conexion_db:
                self.conexion_db.rollback()
            print(f"Error al guardar lote de dotación teórica: {e}")
            return False

    def cerrar_conexion(self):
        if hasattr(self, 'conexion_db') and self.conexion_db:
            try:
                self.conexion_db.close()
            except Exception:
                pass
