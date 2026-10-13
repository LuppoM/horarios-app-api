from datetime import date, timedelta
import os
import sqlite3
import sys

import conexion


def _obtener_conexion_local():
    """Misma base SQLite (HORARIOS.db) que usan hgolomodelo y Hchocomodelo."""
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_path, "HORARIOS.db")
    return sqlite3.connect(db_path)


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

    def eliminar_datos_semanas_anteriores_local(self, semana_actual=None):
        """Limpieza sobre la base SQLite local (HORARIOS.db), que es la que
        leen y escriben las pantallas de Golosinas, Chocolates y Dotación.

        - modymoi: blanquea horario, sector, planta y semana de las filas
          cuya semana sea anterior a la semana activa.
        - modymoi_finde: borra las filas de semanas anteriores.
        - dotacion_teorica_horarios: borra las semanas anteriores.

        Si no se indica semana_actual, usa la semana objetivo real
        (hoy + 7 días), sin depender de lo que se haya tipeado en pantalla.
        """
        if semana_actual is None:
            semana_actual = self.obtener_numero_semana_personalizado(
                date.today() + timedelta(days=7)
            )
        semana_num = int(semana_actual)

        sentencias = [
            (
                "modymoi",
                """
                UPDATE modymoi
                SET horario = '', sector = '', planta = '', semana = ''
                WHERE semana IS NOT NULL
                  AND TRIM(CAST(semana AS TEXT)) GLOB '[0-9]*'
                  AND CAST(TRIM(CAST(semana AS TEXT)) AS INTEGER) < ?
                """,
            ),
            (
                "modymoi_finde",
                """
                DELETE FROM modymoi_finde
                WHERE semana IS NOT NULL
                  AND TRIM(CAST(semana AS TEXT)) GLOB '[0-9]*'
                  AND CAST(TRIM(CAST(semana AS TEXT)) AS INTEGER) < ?
                """,
            ),
            (
                "dotacion_teorica_horarios",
                """
                DELETE FROM dotacion_teorica_horarios
                WHERE semana_inicio IS NOT NULL
                  AND TRIM(CAST(semana_inicio AS TEXT)) GLOB '[0-9]*'
                  AND CAST(TRIM(CAST(semana_inicio AS TEXT)) AS INTEGER) < ?
                """,
            ),
        ]

        conexion_local = _obtener_conexion_local()
        try:
            cursor = conexion_local.cursor()
            for nombre_tabla, sql in sentencias:
                try:
                    cursor.execute(sql, (semana_num,))
                    print(
                        f"[limpieza local] {nombre_tabla}: "
                        f"{cursor.rowcount} fila(s) afectadas (semana < {semana_num})."
                    )
                except Exception as e:
                    print(f"[limpieza local] Error en {nombre_tabla}: {e}")
            conexion_local.commit()
        finally:
            conexion_local.close()

    def eliminar_datos_semanas_anteriores(self, semana_actual=None):
        """Si los registros de modymoi tienen una semana estrictamente anterior a semana_actual,
        blanquea los campos horario_semana, sector_semana, planta_semana y semana en modymoi,
        y borra las filas de modymoi_finde.

        OJO: esta versión trabaja sobre la base remota (PostgreSQL/Supabase).
        """
        try:
            cursor = self.conexion_db.cursor()

            if semana_actual is None:
                semana_actual = self.obtener_numero_semana_personalizado()

            semana_num = int(semana_actual)

            # 1. Blanquear asignaciones usando los nombres de columna REALES de la BD
            cursor.execute(
                """
                UPDATE modymoi
                SET horario_semana = '', 
                    sector_semana = '', 
                    planta_semana = '',
                    semana = ''
                WHERE semana IS NOT NULL 
                  AND TRIM(CAST(semana AS TEXT)) != ''
                  AND CASE 
                        WHEN TRIM(CAST(semana AS TEXT)) ~ '^[0-9]+$' THEN CAST(TRIM(CAST(semana AS TEXT)) AS INTEGER) 
                        ELSE 0 
                      END < %s
                """,
                (semana_num,),
            )

            # 2. Borrar filas de modymoi_finde de semanas anteriores
            cursor.execute(
                """
                DELETE FROM modymoi_finde
                WHERE semana IS NOT NULL 
                  AND CASE 
                        WHEN TRIM(CAST(semana AS TEXT)) ~ '^[0-9]+$' THEN CAST(TRIM(CAST(semana AS TEXT)) AS INTEGER) 
                        ELSE 0 
                      END < %s
                """,
                (semana_num,),
            )

            # 3. Borrar la dotación teórica de semanas anteriores
            cursor.execute(
                """
                DELETE FROM dotacion_teorica_horarios
                WHERE semana_inicio IS NOT NULL 
                  AND CASE 
                        WHEN TRIM(CAST(semana_inicio AS TEXT)) ~ '^[0-9]+$' THEN CAST(TRIM(CAST(semana_inicio AS TEXT)) AS INTEGER) 
                        ELSE 0 
                      END < %s
                """,
                (semana_num,),
            )

            self.conexion_db.commit()
            print(f"Limpieza ejecutada exitosamente en modymoi para la semana {semana_num}.")

        except Exception as e:
            self.conexion_db.rollback()
            print(f"Error al limpiar semanas anteriores en modymoi: {e}")

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
