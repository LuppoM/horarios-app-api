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

    def obtener_datos(self, columna=None, filtro=None, semana_actual=None):
        try:
            cursor = self.conexion_db.cursor()

            # nombre que ve el usuario -> columna real (con comillas por las mayúsculas)
            mapa = {
                "id": "id",
                "calificacion_mano_obra": "calificacion_mano_obra",
                "operario": "operario",
                "Horario": '"Horario"',
                "Sector": '"Sector"',
                "Planta": '"Planta"',
                "semana": "semana",
            }
            columnas = list(mapa.keys())

            query = """
                SELECT id, calificacion_mano_obra, operario,
                    "Horario", "Sector", "Planta", semana
                FROM modymoi
                WHERE 1=1
            """
            params = []

            if columna and filtro:
                col_real = mapa.get(columna)
                if col_real:
                    query += f" AND {col_real}::text ILIKE %s"
                    params.append(f"%{filtro}%")

            query += " ORDER BY operario ASC"
            cursor.execute(query, params)

            filas = cursor.fetchall()
            datos = []
            for f in filas:
                if isinstance(f, dict):
                    datos.append([f.get("id"), f.get("calificacion_mano_obra"),
                                f.get("operario"), f.get("Horario"),
                                f.get("Sector"), f.get("Planta"), f.get("semana")])
                else:
                    datos.append(list(f))

            return columnas, datos
        except Exception as e:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            print(f"Error al consultar semana en Supabase: {e}")
            raise Exception(f"Error al consultar semana: {e}")

    def obtener_datos_mecanicos(self, filtro_columna=None, filtro_valor=None, semana_actual=None):
        """Consulta la tabla mecanicos usando sus columnas: id, operario, horario, planta, semana."""
        try:
            cursor = self.conexion_db.cursor()

            if not semana_actual:
                semana_actual = str(self.obtener_numero_semana_personalizado())

            columnas = [
                "id",
                "calificacion_mano_obra",
                "operario",
                "semana",
                "horario_semana",
                "planta_semana"
            ]

            query_base = """
                SELECT 
                    id,
                    'MOI' AS calificacion_mano_obra,
                    operario,
                    semana,
                    COALESCE(horario::text, '') AS horario_semana,
                    COALESCE(planta::text, '') AS planta_semana
                FROM mecanicos
                WHERE (semana::text = %s OR horario IS NOT NULL)
            """
            params = [str(semana_actual)]

            if filtro_columna and filtro_valor:
                col_filtro = filtro_columna
                if filtro_columna.lower() in ["horario", "horario_semana"]:
                    col_filtro = "horario"
                elif filtro_columna.lower() in ["planta", "planta_semana"]:
                    col_filtro = "planta"

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
                        f.get("planta_semana")
                    ])
                else:
                    datos.append(list(f))

            return columnas, datos
        except Exception as e:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            print(f"Error al consultar mecánicos en Supabase: {e}")
            raise Exception(f"Error al consultar mecánicos: {e}")

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
    def actualizar_registro(self, id_registro, calificacion, operario, horario):
        """Actualiza calificacion_mano_obra, operario y "Horario" respetando las mayúsculas de PostgreSQL."""
        cursor = self.conexion_db.cursor()
        try:
            cursor.execute(
                """
                UPDATE modymoi
                SET calificacion_mano_obra = %s,
                    operario = %s,
                    "Horario" = %s
                WHERE id = %s
                """,
                (str(calificacion), str(operario), str(horario), int(id_registro))
            )
            self.conexion_db.commit()
            return True
        except Exception as e:
            print(f"Error al actualizar registro en Supabase: {e}")
            self.conexion_db.rollback()
            return False
        
    def contar_mano_de_obra(self, vista="Semana", semana_actual=None):
        cursor = self.conexion_db.cursor()
        try:
            # Si venía de una transacción fallida previa, reseteamos el estado
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()

            cursor.execute(
                """
                SELECT 
                    COUNT(CASE WHEN calificacion_mano_obra = 'MOD' THEN 1 END),
                    COUNT(CASE WHEN calificacion_mano_obra = 'MOI' THEN 1 END)
                FROM modymoi
                """
            )
            res = cursor.fetchone()
            if res:
                return (res[0] or 0, res[1] or 0)
            return (0, 0)
        except Exception as e:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            print(f"Error contando mano de obra en Supabase: {e}")
            return (0, 0)
        
    def obtener_por_id(self, id_registro):
        """Obtiene un registro específico de modymoi desde Supabase mapeando las columnas exactas."""
        cursor = self.conexion_db.cursor()
        try:
            cursor.execute(
                """
                SELECT id, calificacion_mano_obra, operario, "Horario", "Sector", "Planta", semana 
                FROM modymoi 
                WHERE id = %s
                """,
                (int(id_registro),)
            )
            row = cursor.fetchone()
            if not row:
                return None
            
            # Devuelve un diccionario explícito para que el JS no falle
            if isinstance(row, dict):
                return row
            
            return {
                "id": row[0],
                "calificacion_mano_obra": row[1],
                "operario": row[2],
                "horario": row[3],
                "sector": row[4],
                "planta": row[5],
                "semana": row[6]
            }
        except Exception as e:
            print(f"Error al obtener registro por ID en Supabase: {e}")
            return None
    def cerrar_conexion(self):
        if hasattr(self, 'conexion_db') and self.conexion_db:
            try:
                self.conexion_db.close()
            except Exception:
                pass
