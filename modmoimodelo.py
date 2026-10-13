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

    def limpiar_semanas_anteriores(self, semana_actual=None):
        """Ejecuta la limpieza sobre Supabase reutilizando la conexión activa."""
        try:
            self._modelo_principal.conexion_db = self.conexion_db
            self._modelo_principal.eliminar_datos_semanas_anteriores(semana_actual=semana_actual)
        except Exception as e:
            print(f"Error al ejecutar limpieza desde ModMoiModel: {e}")

    def obtener_datos(self, filtro_columna=None, filtro_valor=None, semana_actual=None):
        """Obtiene la lista de operarios desde Supabase leyendo las columnas con mayúscula inicial
        'Horario', 'Sector', 'Planta' de la tabla modymoi.
        """
        try:
            # Ejecutamos la limpieza automática antes de consultar
            self.limpiar_semanas_anteriores(semana_actual=semana_actual)

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
                    COALESCE("Horario"::text, '') AS horario_semana,
                    COALESCE("Sector"::text, '') AS sector_semana,
                    COALESCE("Planta"::text, '') AS planta_semana
                FROM modymoi
                WHERE 1=1
            """
            params = []

            if filtro_columna and filtro_valor:
                col_filtro = filtro_columna
                if filtro_columna.lower() in ["horario", "horario_semana"]:
                    col_filtro = '"Horario"'
                elif filtro_columna.lower() in ["sector", "sector_semana"]:
                    col_filtro = '"Sector"'
                elif filtro_columna.lower() in ["planta", "planta_semana"]:
                    col_filtro = '"Planta"'

                query_base += f" AND {col_filtro}::text ILIKE %s"
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
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            print(f"Error en obtener_datos de modymoi: {e}")
            raise Exception(f"Error de SQL: {e}")

    def obtener_datos_finde(self, filtro_columna=None, filtro_valor=None, semana_actual=None):
        """Consulta la tabla modymoi_finde usando sus columnas minúsculas."""
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
                WHERE f.semana::text = %s
            """
            params = [str(semana_actual)]

            if filtro_columna and filtro_valor:
                query_base += f" AND f.{filtro_columna}::text ILIKE %s"
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
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            print(f"Error al consultar fin de semana en Supabase: {e}")
            raise Exception(f"Error al consultar fin de semana: {e}")

    def contar_mano_de_obra(self, es_finde=False, semana_actual=None):
        try:
            cursor = self.conexion_db.cursor()

            if es_finde:
                if not semana_actual:
                    semana_actual = str(self.obtener_numero_semana_personalizado())
                query = """
                    SELECT m.calificacion_mano_obra 
                    FROM modymoi_finde f
                    INNER JOIN modymoi m ON f.id_operario = m.id
                    WHERE f.semana::text = %s
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
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            print(f"Error al contar mano de obra: {e}")
            return 0, 0

    def cerrar_conexion(self):
        if hasattr(self, 'conexion_db') and self.conexion_db:
            self.conexion_db.close()
