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
        """Libera a los operarios cuando la planta pasa a una semana nueva.

        - modymoi (carga semanal por UPDATE, mano de obra fija): NO se borran
          filas. Se vacían horario_semana, sector_semana y planta_semana de las
          semanas ANTERIORES y se pasa la fila a la semana actual, así el
          operario aparece libre en obtener_operarios_disponibles(semana_actual).
        - modymoi_finde (carga por INSERT): se borran las filas de semanas
          anteriores.
        - dotacion_teorica_horarios: se borran las filas de semanas anteriores.

        Es idempotente: se puede llamar al iniciar la carga semanal o al abrir
        la app sin riesgo de duplicar efectos.
        """
        try:
            cursor = self.conexion_db.cursor()
            semana_actual = self.obtener_numero_semana_personalizado()

            # 1. Liberar operarios en modymoi (semanas < actual)
            cursor.execute(
                """
                UPDATE modymoi
                SET horario_semana = '',
                    sector_semana = '',
                    planta_semana = '',
                    semana = ?
                WHERE semana IS NOT NULL
                  AND TRIM(semana) != ''
                  AND CAST(TRIM(semana) AS INTEGER) < ?
                """,
                (str(semana_actual), semana_actual),
            )

            # 2. Despejar modymoi_finde (semanas < actual)
            cursor.execute(
                """
                DELETE FROM modymoi_finde
                WHERE semana IS NOT NULL
                  AND CAST(semana AS INTEGER) < ?
                """,
                (semana_actual,),
            )

            # 3. Despejar la dotación teórica (semanas < actual)
            cursor.execute(
                """
                DELETE FROM dotacion_teorica_horarios
                WHERE semana_inicio IS NOT NULL
                  AND CAST(semana_inicio AS INTEGER) < ?
                """,
                (semana_actual,),
            )

            self.conexion_db.commit()
            print(
                f"Liberación semanal completada: operarios libres en la "
                f"semana {semana_actual}."
            )

        except Exception as e:
            self.conexion_db.rollback()
            print(f"Error al liberar semanas anteriores: {e}")

    def vaciar_tabla_finde_por_semana(self, semana):
        """Elimina las filas dinámicas de 'modymoi_finde' correspondientes a una
        semana específica (ideal antes de re-insertar al guardar).
        """
        try:
            cursor = self.conexion_db.cursor()
            cursor.execute(
                "DELETE FROM modymoi_finde WHERE semana = ?", (semana,)
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
                SET horario_semana = '',
                    sector_semana = '',
                    planta_semana = ''
                WHERE 1=1
            """
            params_modymoi = []

            if id_operario is not None:
                sql_modymoi += " AND id=?"
                params_modymoi.append(id_operario)
            if semana is not None:
                sql_modymoi += " AND semana=?"
                params_modymoi.append(semana)

            cursor.execute(sql_modymoi, params_modymoi)

            # 2. Eliminar de modymoi_finde con los mismos parámetros
            sql_finde = "DELETE FROM modymoi_finde WHERE 1=1"
            params_finde = []

            if id_operario is not None:
                sql_finde += " AND id_operario=?"
                params_finde.append(id_operario)
            if semana is not None:
                sql_finde += " AND semana=?"
                params_finde.append(semana)

            cursor.execute(sql_finde, params_finde)

            self.conexion_db.commit()
            print("Operación de limpieza completada con éxito.")
        except Exception as e:
            self.conexion_db.rollback()
            print(f"Error al limpiar operario: {e}")

    # --- MÉTODOS DE NEGOCIO PARA CHOCOLATES ---

    def obtener_sectores_chocolates(self):
        """Obtiene los sectores y tipos de horario para la planta de Chocolates"""
        cursor = self.conexion_db.cursor()
        try:
            cursor.execute(
                "SELECT nombre_sector, tipo_horario, requiere_dotacion FROM sectores WHERE planta='Chocolate'"
            )
            rows = cursor.fetchall()
            return rows if rows else []
        except Exception as e:
            print(f"Error al obtener sectores de chocolates: {e}")
            return []

    def obtener_turnos_por_tipo(self, tipo_horario):
        """Busca los turnos definidos según el tipo de horario"""
        cursor = self.conexion_db.cursor()
        try:
            cursor.execute(
                "SELECT horarios_definidos FROM tipohorario WHERE UPPER(TRIM(tipo)) = ?",
                (tipo_horario.upper(),),
            )
            row = cursor.fetchone()
            if row and row[0]:
                return [t.strip() for t in row[0].split(",")]
        except Exception as e:
            print(f"Error al obtener turnos por tipo: {e}")
        return []

    def obtener_dotacion_teorica(self, semana):
        """Obtiene la dotación teórica por sector y horario para la semana"""
        cursor = self.conexion_db.cursor()
        try:
            cursor.execute(
                """
                SELECT sector, rango_horario, cantidad_operarios
                FROM dotacion_teorica_horarios
                WHERE semana_inicio=? AND planta='Chocolate'
                """,
                (str(semana),),
            )
            resultados = {}
            for sector, rango, cantidad in cursor.fetchall():
                if sector not in resultados:
                    resultados[sector] = {}
                resultados[sector][rango] = cantidad
            return resultados
        except Exception as e:
            print(f"Error al obtener dotación teórica: {e}")
            return {}

    def obtener_datos_semana(self, semana):
        """Devuelve los datos guardados asegurando traer el nombre del operario"""
        cursor = self.conexion_db.cursor()

        cursor.execute(
            """
            SELECT m.id, m.operario, m.horario_semana, m.sector_semana
            FROM modymoi m
            WHERE m.semana=? AND (m.planta_semana='Chocolates' OR m.planta_semana='Chocolate')
            AND m.sector_semana IS NOT NULL AND TRIM(m.sector_semana) != ''
            """,
            (str(semana),),
        )
        rows = cursor.fetchall()

        # Si la columna 'operario' tiene un ID numérico, lo resolvemos con el
        # diccionario de operarios {id: nombre}
        todos_ops = self.obtener_operarios()

        datos_procesados = []
        for r_id, r_op, r_horario, r_sector in rows:
            nombre_a_mostrar = r_op

            if r_op and str(r_op).isdigit() and int(r_op) in todos_ops:
                nombre_a_mostrar = todos_ops[int(r_op)]
            elif not r_op and r_id in todos_ops:
                nombre_a_mostrar = todos_ops[r_id]

            datos_procesados.append(
                (r_id, nombre_a_mostrar, r_horario, r_sector)
            )

        return datos_procesados

    def obtener_operarios_disponibles(self, semana):
        """Filtra y devuelve los operarios que no tienen sector, horario y planta cargados en la semana"""
        cursor = self.conexion_db.cursor()
        sem_val = str(semana).strip()

        cursor.execute(
            """
            SELECT id, operario, horario_semana, sector_semana, planta_semana
            FROM modymoi
            WHERE semana = ?
            """,
            (sem_val,),
        )
        rows = cursor.fetchall()

        disponibles = []
        for id_val, nombre, horario, sector, planta in rows:
            ocupado = bool(
                horario and str(horario).strip()
                and sector and str(sector).strip()
                and planta and str(planta).strip()
            )
            if not ocupado and nombre and str(nombre).strip() != "":
                disponibles.append((id_val, nombre))

        return disponibles

    def obtener_operarios(self):
        """Devuelve todos los operarios válidos ordenados alfabéticamente"""
        cursor = self.conexion_db.cursor()
        cursor.execute(
            "SELECT id, operario FROM modymoi WHERE operario IS NOT NULL AND TRIM(operario) != '' ORDER BY operario ASC"
        )
        rows = cursor.fetchall()
        return {row[0]: row[1] for row in rows}

    def cerrar_conexion(self):
        if self.conexion_db:
            self.conexion_db.close()
