from datetime import date, timedelta
import conexion


class modeloprincipal:

    def __init__(self):
        self.conexion_db = conexion.obtener_conexion()

    def obtener_numero_semana_personalizado(self, fecha=None):
        """Calcula el número de semana bajo la regla de la planta:

        - Si el 1 de enero es Lunes, esa es la Semana 1.
        - Si el 1 de enero NO es Lunes, esa semana incompleta se descarta.
          La Semana 1 comenzará oficialmente en el primer lunes de enero.
        """
        if fecha is None:
            fecha = date.today()

        anio_actual = fecha.year
        primer_dia_anio = date(anio_actual, 1, 1)

        if primer_dia_anio.weekday() == 0:
            inicio_semana_1 = primer_dia_anio
        else:
            dias_hasta_lunes = (7 - primer_dia_anio.weekday()) % 7
            inicio_semana_1 = primer_dia_anio + timedelta(
                days=dias_hasta_lunes
            )

        if fecha < inicio_semana_1:
            anio_anterior = anio_actual - 1
            primer_dia_anterior = date(anio_anterior, 1, 1)

            if primer_dia_anterior.weekday() == 0:
                inicio_anterior = primer_dia_anterior
            else:
                dias_hasta_lunes = (7 - primer_dia_anterior.weekday()) % 7
                inicio_anterior = primer_dia_anterior + timedelta(
                    days=dias_hasta_lunes
                )

            diferencia_dias = (fecha - inicio_anterior).days
            return (diferencia_dias // 7) + 1

        diferencia_dias = (fecha - inicio_semana_1).days
        return (diferencia_dias // 7) + 1

    def eliminar_datos_semanas_anteriores(self):
        """Aplica la misma lógica a las tablas de planificación:

        - En 'modymoi': Blanquea campos para semanas <= semana_actual.
        - En 'modymoi_finde': Elimina filas completas para semanas <= semana_actual.
        - En 'dotacion_teorica_horarios': Elimina la dotación teórica para semanas <= semana_actual.
        """
        try:
            cursor = self.conexion_db.cursor()
            semana_actual = self.obtener_numero_semana_personalizado()

            # 1. Blanquear modymoi (semana actual e inferiores)
            cursor.execute(
                """
                UPDATE modymoi
                SET "Horario" = '', 
                    "Sector" = '', 
                    "Planta" = ''
                WHERE semana IS NOT NULL 
                  AND TRIM(semana) != ''
                  AND CAST(TRIM(semana) AS INTEGER) <= %s
            """,
                (semana_actual,),
            )

            # 2. Borrar de modymoi_finde filtrando exactamente por la misma condición
            cursor.execute(
                """
                DELETE FROM modymoi_finde
                WHERE semana IS NOT NULL 
                  AND CAST(semana AS INTEGER) <= %s
            """,
                (semana_actual,),
            )

            # 3. Borrar la dotación teórica de los horarios para semanas pasadas o actuales
            cursor.execute(
                """
                DELETE FROM dotacion_teorica_horarios
                WHERE semana_inicio IS NOT NULL 
                  AND CAST(semana_inicio AS INTEGER) <= %s
            """,
                (semana_actual,),
            )

            self.conexion_db.commit()
            print(
                f"Limpieza basada en semana {semana_actual} completada con"
                " éxito en todas las tablas."
            )

        except Exception as e:
            self.conexion_db.rollback()
            print(f"Error al limpiar semanas anteriores: {e}")

    def vaciar_tabla_finde_por_semana(self, semana):
        """Elimina las filas dinámicas de 'modymoi_finde' correspondientes a una
        semana específica (ideal antes de re-insertar al guardar).
        """
        try:
            cursor = self.conexion_db.cursor()
            cursor.execute(
                "DELETE FROM modymoi_finde WHERE semana = %s", (str(semana),)
            )
            self.conexion_db.commit()
            print(f"Registros de fin de semana purgados para semana {semana}.")
        except Exception as e:
            self.conexion_db.rollback()
            print(f"Error al purgar semana {semana} en 'modymoi_finde': {e}")

    def limpiar_operario(self, id_operario=None, semana=None):
        """Resetea 'modymoi' y borra las filas de 'modymoi_finde' respetando los
        filtros de ID y/o semana.
        """
        try:
            cursor = self.conexion_db.cursor()

            # 1. Resetear modymoi
            sql_modymoi = """
                UPDATE modymoi 
                SET "Horario" = '', 
                    "Sector" = '', 
                    "Planta" = '' 
                WHERE 1=1
            """
            params_modymoi = []

            if id_operario is not None:
                sql_modymoi += " AND id=%s"
                params_modymoi.append(id_operario)
            if semana is not None:
                sql_modymoi += " AND semana=%s"
                params_modymoi.append(str(semana))

            cursor.execute(sql_modymoi, params_modymoi)

            # 2. Eliminar de modymoi_finde con los mismos parámetros
            sql_finde = "DELETE FROM modymoi_finde WHERE 1=1"
            params_finde = []

            if id_operario is not None:
                sql_finde += " AND id_operario=%s"
                params_finde.append(id_operario)
            if semana is not None:
                sql_finde += " AND semana=%s"
                params_finde.append(str(semana))

            cursor.execute(sql_finde, params_finde)

            self.conexion_db.commit()
            print("Operación de limpieza completada con éxito.")

        except Exception as e:
            self.conexion_db.rollback()
            print(f"Error al limpiar operario: {e}")

    def cerrar_conexion(self):
        if self.conexion_db:
            self.conexion_db.close()
