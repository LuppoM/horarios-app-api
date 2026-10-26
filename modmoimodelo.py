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
        """Consulta la tabla modymoi trayendo todos los operarios registrados."""
        cursor = None
        try:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()

            cursor = self.conexion_db.cursor()

            columnas = [
                "id",
                "calificacion_mano_obra",
                "operario",
                "semana",
                "Horario",
                "Sector",
                "Planta"
            ]

            # Traemos todos los operarios. Si semana::text = %s dejaba la tabla vacía, 
            # permitimos que traiga aunque semana sea NULL o diferente.
            query_base = """
                SELECT 
                    id,
                    COALESCE(calificacion_mano_obra::text, 'MOD') AS calificacion_mano_obra,
                    operario,
                    COALESCE(semana::text, '') AS semana,
                    COALESCE("Horario"::text, '') AS "Horario",
                    COALESCE("Sector"::text, '') AS "Sector",
                    COALESCE("Planta"::text, '') AS "Planta"
                FROM modymoi
                WHERE 1=1
            """
            params = []

            if filtro_columna and filtro_valor:
                col_filtro = filtro_columna
                if col_filtro in ["Horario", "Sector", "Planta"]:
                    col_filtro = f'"{col_filtro}"'
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
                        f.get("Horario"),
                        f.get("Sector"),
                        f.get("Planta")
                    ])
                else:
                    datos.append(list(f))

            return columnas, datos

        except Exception as e:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            print(f"Error al consultar modymoi en Supabase: {e}")
            return [
                "id", "calificacion_mano_obra", "operario", "semana", "Horario", "Sector", "Planta"
            ], []
        finally:
            if cursor:
                cursor.close()

    def obtener_datos_mecanicos(self, filtro_columna=None, filtro_valor=None, semana_actual=None):
        """Consulta la tabla mecanicos usando sus columnas: id, operario, horario, planta, semana."""
        cursor = None
        try:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()

            cursor = self.conexion_db.cursor()

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
                    COALESCE(semana::text, '') AS semana,
                    COALESCE(horario::text, '') AS horario_semana,
                    COALESCE(planta::text, '') AS planta_semana
                FROM mecanicos
                WHERE 1=1
            """
            params = []

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
            return ["id", "calificacion_mano_obra", "operario", "semana", "horario_semana", "planta_semana"], []
        finally:
            if cursor:
                cursor.close()

    def obtener_datos_finde(self, filtro_columna=None, filtro_valor=None, semana_actual=None):
        """Consulta la tabla modymoi_finde usando sus columnas minúsculas."""
        cursor = None
        try:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()

            cursor = self.conexion_db.cursor()

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
                    COALESCE(f.semana::text, '') AS semana,
                    COALESCE(f.dia::text, '') AS dia,
                    COALESCE(f.horario::text, '') AS horario,
                    COALESCE(f.sector::text, '') AS sector,
                    COALESCE(f.planta::text, '') AS planta
                FROM modymoi_finde f
                INNER JOIN modymoi m ON f.id_operario = m.id
                WHERE 1=1
            """
            params = []

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
            return ["id", "id_operario", "operario", "semana", "dia", "horario", "sector", "planta"], []
        finally:
            if cursor:
                cursor.close()

    def agregar_registro(self, calificacion, operario):
        """Agrega un nuevo registro insertando únicamente calificacion_mano_obra y operario en Supabase."""
        cursor = None
        try:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()

            cursor = self.conexion_db.cursor()
            cursor.execute(
                """
                INSERT INTO modymoi (calificacion_mano_obra, operario)
                VALUES (%s, %s)
                """,
                (str(calificacion), str(operario))
            )
            self.conexion_db.commit()
            return True
        except Exception as e:
            print(f"Error al agregar registro en Supabase: {e}")
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            return False
        finally:
            if cursor:
                cursor.close()

    def actualizar_registro(self, id_registro, calificacion, operario):
        """Actualiza únicamente calificacion_mano_obra y operario por ID en Supabase."""
        cursor = None
        try:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()

            cursor = self.conexion_db.cursor()
            cursor.execute(
                """
                UPDATE modymoi
                SET calificacion_mano_obra = %s,
                    operario = %s
                WHERE id = %s
                """,
                (str(calificacion), str(operario), int(id_registro))
            )
            self.conexion_db.commit()
            return True
        except Exception as e:
            print(f"Error al actualizar registro en Supabase: {e}")
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            return False
        finally:
            if cursor:
                cursor.close()

    def contar_mano_de_obra(self, vista="Semana", semana_actual=None):
        """Cuenta MOD y MOI dinámicamente según la vista seleccionada."""
        cursor = None
        try:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()

            cursor = self.conexion_db.cursor()

            if vista == "Mecanicos":
                cursor.execute("SELECT COUNT(*) FROM mecanicos;")
                res = cursor.fetchone()
                total = int(res[0]) if res and res[0] else 0
                return (0, total)  # Todos los mecánicos son MOI (Indirecta)

            elif vista == "Fin de Semana":
                cursor.execute("""
                    SELECT 
                        COUNT(CASE WHEN UPPER(TRIM(COALESCE(m.calificacion_mano_obra::text, ''))) = 'MOD' THEN 1 END),
                        COUNT(CASE WHEN UPPER(TRIM(COALESCE(m.calificacion_mano_obra::text, ''))) = 'MOI' THEN 1 END)
                    FROM modymoi_finde f
                    INNER JOIN modymoi m ON f.id_operario = m.id;
                """)
            else:
                # Vista "Semana" por defecto
                cursor.execute("""
                    SELECT 
                        COUNT(CASE WHEN UPPER(TRIM(COALESCE(calificacion_mano_obra::text, ''))) = 'MOD' THEN 1 END),
                        COUNT(CASE WHEN UPPER(TRIM(COALESCE(calificacion_mano_obra::text, ''))) = 'MOI' THEN 1 END)
                    FROM modymoi;
                """)

            res = cursor.fetchone()
            if res:
                return (int(res[0] or 0), int(res[1] or 0))
            return (0, 0)

        except Exception as e:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            print(f"Error contando mano de obra en Supabase ({vista}): {e}")
            return (0, 0)
        finally:
            if cursor:
                cursor.close()

    def eliminar_registro(self, id_registro):
        """Elimina un registro de modymoi por su ID en Supabase."""
        cursor = None
        try:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()

            cursor = self.conexion_db.cursor()
            cursor.execute(
                """
                DELETE FROM modymoi 
                WHERE id = %s
                """,
                (int(id_registro),)
            )
            self.conexion_db.commit()
            return True
        except Exception as e:
            print(f"Error al eliminar registro en Supabase: {e}")
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            return False
        finally:
            if cursor:
                cursor.close()

    def obtener_por_id(self, id_registro):
        """Obtiene un registro específico de modymoi desde Supabase mapeando las columnas exactas."""
        cursor = None
        try:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()

            cursor = self.conexion_db.cursor()
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
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            print(f"Error al obtener registro por ID en Supabase: {e}")
            return None
        finally:
            if cursor:
                cursor.close()

    def cerrar_conexion(self):
        if hasattr(self, 'conexion_db') and self.conexion_db:
            try:
                self.conexion_db.close()
            except Exception:
                pass