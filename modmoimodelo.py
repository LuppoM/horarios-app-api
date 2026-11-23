import conexion
from principalmodelo import modeloprincipal


class ModMoiModel:

    # Mapeo exacto según los valores de 'area' (y 'usuario') en la tabla usuarios
    MAPA_TABLA_POR_AREA = {
        "produccion": "modymoi",
        "producción": "modymoi",
        "mantenimiento": "mecanicos",
        "mecanicos": "mecanicos",
        "mecánicos": "mecanicos",
        "calidad": "analistascalidad",
        "analistascalidad": "analistascalidad",
        "deposito materia prima": "depositomp",
        "depósito materia prima": "depositomp",
        "depositomp": "depositomp",
        "deposito mp": "depositomp",
        "depósito mp": "depositomp",
        "deposito producto terminado": "depositopt",
        "depósito producto terminado": "depositopt",
        "depositopt": "depositopt",
        "deposito pt": "depositopt",
        "depósito pt": "depositopt",
    }

    TABLAS_AREA_MOI = ("mecanicos", "analistascalidad", "depositomp", "depositopt")
    TODAS_LAS_TABLAS = ("modymoi", "mecanicos", "analistascalidad", "depositomp", "depositopt")

    def __init__(self, conexion_db=None):
        if conexion_db:
            self.conexion_db = conexion_db
        else:
            self.conexion_db = conexion.obtener_conexion()

        self._modelo_principal = modeloprincipal(self.conexion_db)

    def _es_admin(self, area=None):
        if not area:
            return False
        return str(area).strip().lower() in {"admin", "administrador", "todos", "*"}

    def _es_produccion(self, area=None):
        if not area:
            return True  # Compatibilidad si no se envía área
        return str(area).strip().lower() in {"produccion", "producción"}

    def _resolver_tabla_por_area(self, area=None):
        """Devuelve la tabla asignada al área del usuario (o 'ALL' si es admin)."""
        if self._es_admin(area):
            return "ALL"
        if not area:
            return "modymoi"
        clave = str(area).strip().lower()
        return self.MAPA_TABLA_POR_AREA.get(clave, "modymoi")

    def obtener_numero_semana_personalizado(self, fecha=None):
        return self._modelo_principal.obtener_numero_semana_personalizado(fecha)

    def limpiar_semanas_anteriores(self, semana_actual=None):
        """Ejecuta la limpieza sobre Supabase reutilizando la conexión activa."""
        try:
            self._modelo_principal.conexion_db = self.conexion_db
            self._modelo_principal.eliminar_datos_semanas_anteriores(semana_actual=semana_actual)
        except Exception as e:
            print(f"Error al ejecutar limpieza desde ModMoiModel: {e}")

    def obtener_datos(self, filtro_columna=None, filtro_valor=None, semana_actual=None, area=None, vista="Semana"):
        """
        Selecciona la consulta según el usuario (area) y la vista:
        - produccion -> modymoi (Semana) o modymoi_finde (Fin de Semana)
        - mantenimiento -> mecanicos
        - calidad -> analistascalidad
        - depositomp -> depositomp
        - depositopt -> depositopt
        - admin -> modymoi_finde (Fin de Semana), tabla específica o las 5 tablas unificadas (Semana)
        """
        vista_norm = str(vista or "Semana").strip().lower()
        tabla = self._resolver_tabla_por_area(area)

        # 1. Vista Fin de Semana: solo habilitada para Producción y Admin
        if vista_norm == "fin de semana":
            if self._es_admin(area) or self._es_produccion(area):
                return self.obtener_datos_finde(
                    filtro_columna=filtro_columna,
                    filtro_valor=filtro_valor,
                    semana_actual=semana_actual,
                    area=area,
                )
            return self._obtener_datos_tabla_area_moi(
                nombre_tabla=tabla,
                filtro_columna=filtro_columna,
                filtro_valor=filtro_valor,
                semana_actual=semana_actual,
            )

        # 2. Usuario Admin: puede consultar una vista específica o todas juntas
        if tabla == "ALL":
            vistas_especificas_admin = {
                "mecanicos": "mecanicos",
                "mecánicos": "mecanicos",
                "calidad": "analistascalidad",
                "depositomp": "depositomp",
                "deposito mp": "depositomp",
                "deposito materia prima": "depositomp",
                "depositopt": "depositopt",
                "deposito pt": "depositopt",
                "deposito producto terminado": "depositopt",
            }
            if vista_norm in vistas_especificas_admin:
                return self._obtener_datos_tabla_area_moi(
                    nombre_tabla=vistas_especificas_admin[vista_norm],
                    filtro_columna=filtro_columna,
                    filtro_valor=filtro_valor,
                    semana_actual=semana_actual,
                )
            return self._obtener_datos_todas_las_areas(
                filtro_columna=filtro_columna,
                filtro_valor=filtro_valor,
                semana_actual=semana_actual,
            )

        # 3. Usuarios de áreas MOI (mantenimiento, calidad, depositomp, depositopt)
        if tabla != "modymoi":
            return self._obtener_datos_tabla_area_moi(
                nombre_tabla=tabla,
                filtro_columna=filtro_columna,
                filtro_valor=filtro_valor,
                semana_actual=semana_actual,
            )

        # 4. Usuario Producción -> tabla modymoi
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
                "Planta",
                "origen_tabla"
            ]

            query_base = """
                SELECT 
                    id,
                    COALESCE(calificacion_mano_obra::text, 'MOD') AS calificacion_mano_obra,
                    operario,
                    COALESCE(semana::text, '') AS semana,
                    COALESCE("Horario"::text, '') AS "Horario",
                    COALESCE("Sector"::text, '') AS "Sector",
                    COALESCE("Planta"::text, '') AS "Planta",
                    'modymoi' AS origen_tabla
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
                        f.get("Planta"),
                        f.get("origen_tabla", "modymoi")
                    ])
                else:
                    datos.append(list(f))

            return columnas, datos

        except Exception as e:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            print(f"Error al consultar modymoi en Supabase: {e}")
            return [
                "id", "calificacion_mano_obra", "operario", "semana", "Horario", "Sector", "Planta", "origen_tabla"
            ], []
        finally:
            if cursor:
                cursor.close()

    def _obtener_datos_todas_las_areas(self, filtro_columna=None, filtro_valor=None, semana_actual=None):
        """Unifica las 5 tablas (modymoi + 4 áreas MOI) exclusivamente para admin."""
        columnas = [
            "id",
            "calificacion_mano_obra",
            "operario",
            "semana",
            "Horario",
            "Sector",
            "Planta",
            "origen_tabla"
        ]

        cursor = None
        try:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()

            cursor = self.conexion_db.cursor()

            query_base = """
                SELECT * FROM (
                    SELECT 
                        id,
                        COALESCE(calificacion_mano_obra::text, 'MOD') AS calificacion_mano_obra,
                        operario,
                        COALESCE(semana::text, '') AS semana,
                        COALESCE("Horario"::text, '') AS "Horario",
                        COALESCE("Sector"::text, '') AS "Sector",
                        COALESCE("Planta"::text, '') AS "Planta",
                        'modymoi' AS origen_tabla
                    FROM modymoi
                    UNION ALL
                    SELECT 
                        id,
                        'MOI' AS calificacion_mano_obra,
                        operario,
                        COALESCE(semana::text, '') AS semana,
                        COALESCE(horario::text, '') AS "Horario",
                        COALESCE(sector::text, '') AS "Sector",
                        COALESCE(planta::text, '') AS "Planta",
                        'mecanicos' AS origen_tabla
                    FROM mecanicos
                    UNION ALL
                    SELECT 
                        id,
                        'MOI' AS calificacion_mano_obra,
                        operario,
                        COALESCE(semana::text, '') AS semana,
                        COALESCE(horario::text, '') AS "Horario",
                        COALESCE(sector::text, '') AS "Sector",
                        COALESCE(planta::text, '') AS "Planta",
                        'analistascalidad' AS origen_tabla
                    FROM analistascalidad
                    UNION ALL
                    SELECT 
                        id,
                        'MOI' AS calificacion_mano_obra,
                        operario,
                        COALESCE(semana::text, '') AS semana,
                        COALESCE(horario::text, '') AS "Horario",
                        COALESCE(sector::text, '') AS "Sector",
                        COALESCE(planta::text, '') AS "Planta",
                        'depositomp' AS origen_tabla
                    FROM depositomp
                    UNION ALL
                    SELECT 
                        id,
                        'MOI' AS calificacion_mano_obra,
                        operario,
                        COALESCE(semana::text, '') AS semana,
                        COALESCE(horario::text, '') AS "Horario",
                        COALESCE(sector::text, '') AS "Sector",
                        COALESCE(planta::text, '') AS "Planta",
                        'depositopt' AS origen_tabla
                    FROM depositopt
                ) AS unificado
                WHERE 1=1
            """
            params = []

            if filtro_columna and filtro_valor:
                col_map = {
                    "id": "id",
                    "calificacion_mano_obra": "calificacion_mano_obra",
                    "operario": "operario",
                    "semana": "semana",
                    "horario": '"Horario"',
                    "horario_semana": '"Horario"',
                    "sector": '"Sector"',
                    "sector_semana": '"Sector"',
                    "planta": '"Planta"',
                    "planta_semana": '"Planta"',
                    "origen_tabla": "origen_tabla",
                    "area": "origen_tabla",
                }
                col_filtro = col_map.get(filtro_columna.lower())
                if col_filtro:
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
                        f.get("Planta"),
                        f.get("origen_tabla")
                    ])
                else:
                    datos.append(list(f))

            return columnas, datos
        except Exception as e:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            print(f"Error al consultar todas las áreas en Supabase: {e}")
            return columnas, []
        finally:
            if cursor:
                cursor.close()

    def _obtener_datos_tabla_area_moi(self, nombre_tabla, filtro_columna=None, filtro_valor=None, semana_actual=None):
        """
        Consulta genérica para las tablas MOI de áreas específicas:
        mecanicos, analistascalidad, depositomp y depositopt.
        """
        if nombre_tabla not in self.TABLAS_AREA_MOI:
            raise ValueError(f"Tabla MOI no permitida: {nombre_tabla}")

        columnas = [
            "id",
            "calificacion_mano_obra",
            "operario",
            "semana",
            "Horario",
            "Sector",
            "Planta",
            "origen_tabla"
        ]

        cursor = None
        try:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()

            cursor = self.conexion_db.cursor()

            query_base = f"""
                SELECT 
                    id,
                    'MOI' AS calificacion_mano_obra,
                    operario,
                    COALESCE(semana::text, '') AS semana,
                    COALESCE(horario::text, '') AS "Horario",
                    COALESCE(sector::text, '') AS "Sector",
                    COALESCE(planta::text, '') AS "Planta",
                    '{nombre_tabla}' AS origen_tabla
                FROM {nombre_tabla}
                WHERE 1=1
            """
            params = []

            if filtro_columna and filtro_valor:
                col_map = {
                    "horario": "horario",
                    "horario_semana": "horario",
                    "sector": "sector",
                    "sector_semana": "sector",
                    "planta": "planta",
                    "planta_semana": "planta",
                    "operario": "operario",
                    "semana": "semana",
                    "id": "id"
                }
                col_filtro = col_map.get(filtro_columna.lower())
                if col_filtro:
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
                        f.get("Planta"),
                        f.get("origen_tabla", nombre_tabla)
                    ])
                else:
                    datos.append(list(f))

            return columnas, datos
        except Exception as e:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            print(f"Error al consultar {nombre_tabla} en Supabase: {e}")
            return columnas, []
        finally:
            if cursor:
                cursor.close()

    def obtener_datos_mecanicos(self, filtro_columna=None, filtro_valor=None, semana_actual=None):
        return self._obtener_datos_tabla_area_moi("mecanicos", filtro_columna, filtro_valor, semana_actual)

    def obtener_datos_analistas_calidad(self, filtro_columna=None, filtro_valor=None, semana_actual=None):
        return self._obtener_datos_tabla_area_moi("analistascalidad", filtro_columna, filtro_valor, semana_actual)

    def obtener_datos_deposito_mp(self, filtro_columna=None, filtro_valor=None, semana_actual=None):
        return self._obtener_datos_tabla_area_moi("depositomp", filtro_columna, filtro_valor, semana_actual)

    def obtener_datos_deposito_pt(self, filtro_columna=None, filtro_valor=None, semana_actual=None):
        return self._obtener_datos_tabla_area_moi("depositopt", filtro_columna, filtro_valor, semana_actual)

    def obtener_datos_finde(self, filtro_columna=None, filtro_valor=None, semana_actual=None, area=None):
        """Consulta modymoi_finde únicamente si el usuario es producción o admin."""
        columnas = ["id", "id_operario", "operario", "semana", "dia", "horario", "sector", "planta"]
        if area and not (self._es_admin(area) or self._es_produccion(area)):
            return columnas, []

        cursor = None
        try:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()

            cursor = self.conexion_db.cursor()

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
            return columnas, []
        finally:
            if cursor:
                cursor.close()

    def _resolver_tabla_escritura(self, area=None, origen_tabla=None, vista=None):
        """Resuelve la tabla concreta para INSERT/UPDATE/DELETE según el área del usuario y la vista."""
        tabla_usuario = self._resolver_tabla_por_area(area)

        # Si NO es admin, forzamos estrictamente la tabla de su área
        if tabla_usuario != "ALL":
            return tabla_usuario

        # Si ES admin, priorizamos origen_tabla explícita
        if origen_tabla and str(origen_tabla).strip().lower() in self.TODAS_LAS_TABLAS:
            return str(origen_tabla).strip().lower()

        # Si ES admin y viene la vista seleccionada en el combo
        if vista:
            vistas_admin = {
                "mecanicos": "mecanicos",
                "mecánicos": "mecanicos",
                "calidad": "analistascalidad",
                "depositomp": "depositomp",
                "deposito mp": "depositomp",
                "deposito materia prima": "depositomp",
                "depositopt": "depositopt",
                "deposito pt": "depositopt",
                "deposito producto terminado": "depositopt",
            }
            v_norm = str(vista).strip().lower()
            if v_norm in vistas_admin:
                return vistas_admin[v_norm]

        return "modymoi"

    def agregar_registro(self, calificacion, operario, area=None, origen_tabla=None, vista=None):
        """Agrega un operario en la tabla correspondiente al área del usuario."""
        tabla = self._resolver_tabla_escritura(area=area, origen_tabla=origen_tabla, vista=vista)
        cursor = None
        try:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()

            cursor = self.conexion_db.cursor()
            if tabla == "modymoi":
                cursor.execute(
                    """
                    INSERT INTO modymoi (calificacion_mano_obra, operario)
                    VALUES (%s, %s)
                    """,
                    (str(calificacion), str(operario))
                )
            else:
                cursor.execute(
                    f"""
                    INSERT INTO {tabla} (operario)
                    VALUES (%s)
                    """,
                    (str(operario),)
                )
            self.conexion_db.commit()
            return True
        except Exception as e:
            print(f"Error al agregar registro en {tabla} (Supabase): {e}")
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            return False
        finally:
            if cursor:
                cursor.close()

    def actualizar_registro(self, id_registro, calificacion, operario, area=None, origen_tabla=None, vista=None):
        """Actualiza el operario por ID en la tabla correspondiente al área del usuario."""
        tabla = self._resolver_tabla_escritura(area=area, origen_tabla=origen_tabla, vista=vista)
        cursor = None
        try:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()

            cursor = self.conexion_db.cursor()
            if tabla == "modymoi":
                cursor.execute(
                    """
                    UPDATE modymoi
                    SET calificacion_mano_obra = %s,
                        operario = %s
                    WHERE id = %s
                    """,
                    (str(calificacion), str(operario), int(id_registro))
                )
            else:
                cursor.execute(
                    f"""
                    UPDATE {tabla}
                    SET operario = %s
                    WHERE id = %s
                    """,
                    (str(operario), int(id_registro))
                )
            self.conexion_db.commit()
            return True
        except Exception as e:
            print(f"Error al actualizar registro en {tabla} (Supabase): {e}")
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            return False
        finally:
            if cursor:
                cursor.close()

    def contar_mano_de_obra(self, vista="Semana", semana_actual=None, area=None):
        """Cuenta MOD y MOI dinámicamente según el área del usuario y la vista."""
        cursor = None
        try:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()

            cursor = self.conexion_db.cursor()
            vista_norm = (vista or "Semana").strip().lower()
            tabla_usuario = self._resolver_tabla_por_area(area)

            if vista_norm == "fin de semana" and (tabla_usuario in {"ALL", "modymoi"}):
                cursor.execute("""
                    SELECT 
                        COUNT(CASE WHEN UPPER(TRIM(COALESCE(m.calificacion_mano_obra::text, ''))) = 'MOD' THEN 1 END),
                        COUNT(CASE WHEN UPPER(TRIM(COALESCE(m.calificacion_mano_obra::text, ''))) = 'MOI' THEN 1 END)
                    FROM modymoi_finde f
                    INNER JOIN modymoi m ON f.id_operario = m.id;
                """)
                res = cursor.fetchone()
                return (int(res[0] or 0), int(res[1] or 0)) if res else (0, 0)

            if tabla_usuario == "ALL":
                vistas_especificas = {
                    "mecanicos": "mecanicos",
                    "mecánicos": "mecanicos",
                    "calidad": "analistascalidad",
                    "depositomp": "depositomp",
                    "deposito mp": "depositomp",
                    "deposito materia prima": "depositomp",
                    "depositopt": "depositopt",
                    "deposito pt": "depositopt",
                    "deposito producto terminado": "depositopt",
                }
                if vista_norm in vistas_especificas:
                    t = vistas_especificas[vista_norm]
                    cursor.execute(f"SELECT COUNT(*) FROM {t};")
                    res = cursor.fetchone()
                    return (0, int(res[0] or 0) if res else 0)

                cursor.execute("""
                    SELECT 
                        COUNT(CASE WHEN UPPER(TRIM(COALESCE(calificacion_mano_obra::text, ''))) = 'MOD' THEN 1 END),
                        COUNT(CASE WHEN UPPER(TRIM(COALESCE(calificacion_mano_obra::text, ''))) = 'MOI' THEN 1 END)
                    FROM modymoi;
                """)
                res_prod = cursor.fetchone()
                mod_total = int(res_prod[0] or 0) if res_prod else 0
                moi_total = int(res_prod[1] or 0) if res_prod else 0

                for t_moi in self.TABLAS_AREA_MOI:
                    cursor.execute(f"SELECT COUNT(*) FROM {t_moi};")
                    r = cursor.fetchone()
                    moi_total += int(r[0] or 0) if r else 0

                return (mod_total, moi_total)

            if tabla_usuario != "modymoi":
                cursor.execute(f"SELECT COUNT(*) FROM {tabla_usuario};")
                res = cursor.fetchone()
                total = int(res[0]) if res and res[0] else 0
                return (0, total)

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
            print(f"Error contando mano de obra en Supabase (area={area}, vista={vista}): {e}")
            return (0, 0)
        finally:
            if cursor:
                cursor.close()

    def eliminar_registro(self, id_registro, area=None, origen_tabla=None, vista=None):
        """Elimina un registro por su ID en la tabla correspondiente al área del usuario."""
        tabla = self._resolver_tabla_escritura(area=area, origen_tabla=origen_tabla, vista=vista)
        cursor = None
        try:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()

            cursor = self.conexion_db.cursor()
            cursor.execute(
                f"""
                DELETE FROM {tabla} 
                WHERE id = %s
                """,
                (int(id_registro),)
            )
            self.conexion_db.commit()
            return True
        except Exception as e:
            print(f"Error al eliminar registro en {tabla} (Supabase): {e}")
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            return False
        finally:
            if cursor:
                cursor.close()

    def obtener_por_id(self, id_registro, area=None, origen_tabla=None, vista=None):
        """Obtiene un registro específico por ID desde la tabla correspondiente al área del usuario."""
        tabla = self._resolver_tabla_escritura(area=area, origen_tabla=origen_tabla, vista=vista)
        cursor = None
        try:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()

            cursor = self.conexion_db.cursor()
            if tabla == "modymoi":
                cursor.execute(
                    """
                    SELECT id, calificacion_mano_obra, operario, "Horario", "Sector", "Planta", semana 
                    FROM modymoi 
                    WHERE id = %s
                    """,
                    (int(id_registro),)
                )
            else:
                cursor.execute(
                    f"""
                    SELECT id, 'MOI' AS calificacion_mano_obra, operario, horario, sector, planta, semana 
                    FROM {tabla} 
                    WHERE id = %s
                    """,
                    (int(id_registro),)
                )
            row = cursor.fetchone()
            if not row:
                return None

            if isinstance(row, dict):
                row["origen_tabla"] = tabla
                return row

            return {
                "id": row[0],
                "calificacion_mano_obra": row[1],
                "operario": row[2],
                "horario": row[3],
                "sector": row[4],
                "planta": row[5],
                "semana": row[6],
                "origen_tabla": tabla
            }
        except Exception as e:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            print(f"Error al obtener registro por ID en {tabla} (Supabase): {e}")
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