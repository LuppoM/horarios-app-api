import conexion


class ModeloHChocoWeb:

    def __init__(self):
        self.conexion_db = conexion.obtener_conexion()
        self.operarios_dict = {}
        self.cargar_operarios()

    def cargar_operarios(self):
        cursor = self.conexion_db.cursor()
        cursor.execute("SELECT id, operario FROM modymoi ORDER BY operario ASC")
        rows = cursor.fetchall()
        self.operarios_dict = {row["id"]: row["operario"] for row in rows if row["operario"]}

    def obtener_operarios(self):
        return self.operarios_dict

    def obtener_sectores_chocolates(self):
        cursor = self.conexion_db.cursor()
        try:
            cursor.execute(
                """
                SELECT nombre_sector, tipo_horario, requiere_dotacion 
                FROM sectores 
                WHERE LOWER(TRIM(planta)) IN ('chocolate', 'chocolates')
                """
            )
            return cursor.fetchall() or []
        except Exception as e:
            print(f"Error al obtener sectores: {e}")
            return []

    def obtener_turnos_por_tipo(self, tipo_horario):
        cursor = self.conexion_db.cursor()
        try:
            cursor.execute(
                "SELECT horarios_definidos FROM tipohorario WHERE UPPER(TRIM(tipo)) = %s",
                (tipo_horario.upper(),),
            )
            row = cursor.fetchone()
            if row and row[0]:
                return [t.strip() for t in row[0].split(",")]
        except Exception as e:
            print(f"Error al obtener turnos: {e}")
        return []

    def obtener_dotacion_teorica(self, semana):
        cursor = self.conexion_db.cursor()
        try:
            cursor.execute(
                """
                SELECT sector, rango_horario, cantidad_operarios
                FROM dotacion_teorica_horarios
                WHERE semana_inicio = %s AND planta = 'Chocolate'
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
            print(f"Error dotación teórica: {e}")
            return {}

    def obtener_operarios_disponibles(self, semana=None, excluir_ids=None):
        cursor = self.conexion_db.cursor()
        cursor.execute(
            """
            SELECT id, operario
            FROM modymoi
            WHERE COALESCE(TRIM("Horario"), '') = ''
              AND COALESCE(TRIM("Sector"), '') = ''
              AND COALESCE(TRIM("Planta"), '') = ''
              AND operario IS NOT NULL AND TRIM(operario) != ''
            ORDER BY operario ASC
            """
        )
        excluidos = {int(i) for i in (excluir_ids or [])}
        return [
            (id_op, nombre)
            for id_op, nombre in cursor.fetchall()
            if id_op not in excluidos
        ]

    def obtener_datos_semana(self, semana):
        cursor = self.conexion_db.cursor()
        cursor.execute(
            """
            SELECT id, operario, "Horario", "Sector"
            FROM modymoi
            WHERE semana = %s AND ("Planta" = 'Chocolates' OR "Planta" = 'Chocolate')
            AND "Sector" IS NOT NULL AND TRIM("Sector") != ''
            """,
            (str(semana),),
        )
        return cursor.fetchall()

    def guardar_datos_semana(self, semana, registros_pantalla):
        cursor = self.conexion_db.cursor()
        sem_val = str(semana).strip()

        cursor.execute(
            """
            SELECT id
            FROM modymoi
            WHERE semana = %s AND LOWER(TRIM("Planta")) IN ('chocolates', 'chocolate')
            """,
            (sem_val,),
        )
        ids_previos_en_bd = set(row[0] for row in cursor.fetchall())
        ids_actuales_en_pantalla = set(r[0] for r in registros_pantalla)

        ids_a_limpiar = ids_previos_en_bd - ids_actuales_en_pantalla
        for id_old in ids_a_limpiar:
            cursor.execute(
                'UPDATE modymoi SET "Horario" = \'\', "Sector" = \'\', "Planta" = \'\' WHERE id = %s',
                (id_old,),
            )

        for id_op, operario_nombre, turno, sector in registros_pantalla:
            cursor.execute(
                """
                UPDATE modymoi
                SET operario = %s, "Horario" = %s, "Sector" = %s,
                    "Planta" = 'Chocolates', semana = %s
                WHERE id = %s
                """,
                (operario_nombre, turno, sector, sem_val, id_op),
            )

        self.conexion_db.commit()

    def cerrar_conexion(self):
        if self.conexion_db:
            self.conexion_db.close()
