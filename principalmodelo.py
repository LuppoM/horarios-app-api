from datetime import date, datetime, timedelta
import conexion


class modeloprincipal:

    def __init__(self, conexion_db=None):
        if conexion_db:
            self.conexion_db = conexion_db
        else:
            self.conexion_db = conexion.obtener_conexion()

    def obtener_numero_semana_personalizado(self, fecha=None):
        """Calcula el número de semana de producción personalizado.
        Ajusta según las reglas operativas internas.
        """
        if fecha is None:
            fecha = date.today()
        elif isinstance(fecha, datetime):
            fecha = fecha.date()

        # Si el día es domingo, la semana operativa empieza/corresponde al lunes siguiente
        if fecha.weekday() == 6:
            fecha_ajustada = fecha + timedelta(days=1)
        else:
            fecha_ajustada = fecha

        # Obtiene el número de semana ISO de la fecha
        return fecha_ajustada.isocalendar()[1]

    def eliminar_datos_semanas_anteriores(self, semana_actual=None):
        """Limpieza remota sobre Supabase (PostgreSQL).
        Blanquea "Horario", "Sector" y "Planta" en la tabla modymoi ÚNICAMENTE
        para las semanas estrictamente ANTERIORES (< semana_actual).
        """
        try:
            cursor = self.conexion_db.cursor()

            if semana_actual is None:
                semana_actual = self.obtener_numero_semana_personalizado()

            semana_num = int(semana_actual)

            # 1. Blanquear puestos en la tabla modymoi para semanas estrictamente anteriores (<)
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

            # 2. Eliminar asignaciones registradas del fin de semana para semanas estrictamente anteriores (<)
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

            self.conexion_db.commit()
            print(f"Limpieza ejecutada exitosamente en Supabase para semanas anteriores a la semana {semana_num}.")

        except Exception as e:
            if hasattr(self, 'conexion_db') and self.conexion_db:
                self.conexion_db.rollback()
            print(f"Error al limpiar semanas anteriores en Supabase: {e}")

    def cerrar_conexion(self):
        if hasattr(self, 'conexion_db') and self.conexion_db:
            try:
                self.conexion_db.close()
            except Exception:
                pass
