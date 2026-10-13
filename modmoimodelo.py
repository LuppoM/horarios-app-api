import conexion
from principalmodelo import modeloprincipal


class ModMoiModel:

    def __init__(self, conexion_db=None):
        if conexion_db:
            self.conexion_db = conexion_db
        else:
            self.conexion_db = conexion.obtener_conexion()
        self._modelo_principal = modeloprincipal()

    def obtener_numero_semana_personalizado(self, fecha=None):
        return self._modelo_principal.obtener_numero_semana_personalizado(fecha)

    def obtener_datos(self, filtro_columna=None, filtro_valor=None, semana_actual=None):
        """Obtiene el listado completo de operarios desde Supabase (PostgreSQL),
        mostrando sus asignaciones actuales sin filtrar la lista completa.
        """
        try:
            cursor = self.conexion_db.cursor()

            columnas = [
                "id",
                "calificacion_mano_obra",
                "operario",
                "semana",
                "horario_semana",
                "sector_semana",
                "planta_semana"
            ]

            query_base = """
                SELECT 
                    id,
                    calificacion_mano_obra,
                    operario,
                    semana,
                    horario_semana,
                    sector_semana,
                    planta_semana
                FROM modymoi
                WHERE 1=1
            """
            params = []

            if filtro_columna and filtro_valor:
                # Mapeo de columnas para el filtro si vienen con nombres viejos
                col_mapeo = {
                    "horario": "horario_semana",
                    "sector": "sector_semana",
                    "planta": "planta_semana"
                }
                col_filtro = col_mapeo.get(filtro_columna.lower(), filtro_columna)
                query_base += f" AND {col_filtro} ILIKE %s"
                params.append("%" + str(filtro_valor) + "%")

            query_base += " ORDER BY operario ASC"

            cursor.execute(query_base, params)
            filas = cursor.fetchall()

            datos = []
            for f in filas:
                if isinstance(f, dict):
                    datos.append([
                        f.get("id"),
                        f.get("calificacion_mano_obra"),
                        f.get("operario"),
                        f.get("semana"),
                        f.get("horario_semana"),
                        f.get("sector_semana"),
                        f.get("planta_semana")
                    ])
                else:
                    datos.append(list(f))

            return columnas, datos
        except Exception as e:
            print(f"Error en obtener_datos de modymoi: {e}")
            raise Exception(f"Error de SQL: {e}")

    def obtener_datos_finde(self, filtro_columna=None, filtro_valor=None, semana_actual=None):
        """Obtiene las filas registradas en modymoi_finde desde Supabase."""
        try:
            cursor = self.conexion_db.cursor()

            if not semana_actual:
                semana_actual = str(self.obtener_numero_semana_personalizado())

            columnas = [
                "id",
                "id_operario",
                "operario",
                "semana",
                "dia",
                "horario",
                "sector",
                "planta"
            ]

            query_base = """
                SELECT 
                    f.id,
                    f.id_operario,
                    m.operario,
                    f.semana,
                    f.dia,
                    f.horario,
                    f.sector,
                    f.planta
                FROM modymoi_finde f
                INNER JOIN modymoi m ON f.id_operario = m.id
                WHERE f.semana = %s
            """
            params = [str(semana_actual)]

            if filtro_columna and filtro_valor:
                query_base += f" AND f.{filtro_columna} ILIKE %s"
                params.append("%" + str(filtro_valor) + "%")

            query_base += " ORDER BY m.operario ASC, f.dia ASC"
            cursor.execute(query_base, params)

            filas = cursor.fetchall()

            datos = []
            for f in filas:
                if isinstance(f, dict):
                    datos.append([
                        f.get("id"),
                        f.get("id_operario"),
                        f.get("operario"),
                        f.get("semana"),
                        f.get("dia"),
                        f.get("horario"),
                        f.get("sector"),
                        f.get("planta")
                    ])
                else:
                    datos.append(list(f))

            return columnas, datos
        except Exception as e:
            print(f"Error al consultar fin de semana en Supabase: {e}")
            raise Exception(f"Error al consultar fin de semana: {e}")

    def limpiar_semanas_antiguas(self, semana_actual):
        """Limpia automáticamente las asignaciones de semanas anteriores en Supabase."""
        try:
            cursor = self.conexion_db.cursor()
            cursor.execute(
                """
                UPDATE modymoi 
                SET horario_semana = '', sector_semana = '', planta_semana = '' 
                WHERE semana IS NOT NULL 
                  AND TRIM(CAST(semana AS TEXT)) != %s
                """,
                (str(semana_actual),)
            )
            self.conexion_db.commit()
        except Exception as e:
            self.conexion_db.rollback()
            print(f"Error al limpiar semanas antiguas: {e}")

    def eliminar_ot(self, id_ot):
        try:
            cursor = self.conexion_db.cursor()
            cursor.execute("DELETE FROM modymoi WHERE id = %s", (id_ot,))
            self.conexion_db.commit()
        except Exception as e:
            self.conexion_db.rollback()
            raise Exception(f"No se pudo eliminar el registro: {e}")

    def contar_mano_de_obra(self, es_finde=False, semana_actual=None):
        """Cuenta únicamente los registros MOD y MOI de la tabla."""
        try:
            cursor = self.conexion_db.cursor()

            if es_finde:
                if not semana_actual:
                    semana_actual = str(self.obtener_numero_semana_personalizado())
                query = """
                    SELECT m.calificacion_mano_obra 
                    FROM modymoi_finde f
                    INNER JOIN modymoi m ON f.id_operario = m.id
                    WHERE f.semana = %s
                """
                cursor.execute(query, (str(semana_actual),))
            else:
                query = "SELECT calificacion_mano_obra FROM modymoi"
                cursor.execute(query)

            valores = cursor.fetchall()

            mod_count = 0
            moi_count = 0

            for v in valores:
                calif = v.get("calificacion_mano_obra") if isinstance(v, dict) else v[0]
                if calif and str(calif).strip().upper() == "MOD":
                    mod_count += 1
                elif calif and str(calif).strip().upper() == "MOI":
                    moi_count += 1

            return mod_count, moi_count
        except Exception as e:
            print(f"Error al contar mano de obra: {e}")
            return 0, 0

    def cerrar_conexion(self):
        if hasattr(self, 'conexion_db') and self.conexion_db:
            self.conexion_db.close()
