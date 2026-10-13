import conexion


class ModeloHChocoWeb:

    def __init__(self):
        # Misma conexión que usa principalmodelo, para ver la misma tabla
        # modymoi (y por lo tanto la misma limpieza semanal).
        self.conexion_db = conexion.obtener_conexion()
        self.operarios_dict = {}
        self.cargar_operarios()

    def cargar_operarios(self):
        cursor = self.conexion_db.cursor()
        cursor.execute("SELECT id, operario FROM modymoi ORDER BY operario ASC")
        rows = cursor.fetchall()
        self.operarios_dict = {row[0]: row[1] for row in rows if row[1]}

    def obtener_operarios(self):
        return self.operarios_dict

    def obtener_sectores_chocolates(self):
        cursor = self.conexion_db.cursor()
        try:
            cursor.execute(
                "SELECT nombre_sector, tipo_horario, requiere_dotacion FROM sectores WHERE planta='Chocolate'"
            )
            return cursor.fetchall() or []
        except Exception as e:
            print(f"Error al obtener sectores: {e}")
            return []

    def obtener_turnos_por_tipo(self, tipo_horario):
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
            print(f"Error al obtener turnos: {e}")
        return []

    def obtener_dotacion_teorica(self, semana):
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
            print(f"Error dotación teórica: {e}")
            return {}

    def obtener_operarios_disponibles(self, semana=None, excluir_ids=None):
        """Operarios libres para las listas desplegables: los que NO tienen
        horario, sector ni planta cargados en modymoi (ni en esta planta ni en
        Golosinas).

        excluir_ids: ids que ya fueron puestos en la grilla de la pantalla pero
        todavía no se guardaron. Se sacan de la lista a medida que se cargan.

        'semana' no filtra: un operario libre es el que no tiene asignación, y
        al guardar se le asigna la semana (guardar_datos_semana). Se mantiene
        el parámetro por compatibilidad con quien ya llama al método.
        """
        cursor = self.conexion_db.cursor()
        cursor.execute(
            """
            SELECT id, operario
            FROM modymoi
            WHERE COALESCE(TRIM(horario_semana), '') = ''
              AND COALESCE(TRIM(sector_semana), '') = ''
              AND COALESCE(TRIM(planta_semana), '') = ''
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
            SELECT id, operario, horario_semana, sector_semana
            FROM modymoi
            WHERE semana=? AND (planta_semana='Chocolates' OR planta_semana='Chocolate')
            AND sector_semana IS NOT NULL AND TRIM(sector_semana) != ''
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
            WHERE semana = ? AND LOWER(TRIM(planta_semana)) IN ('chocolates', 'chocolate')
            """,
            (sem_val,),
        )
        ids_previos_en_bd = set(row[0] for row in cursor.fetchall())
        ids_actuales_en_pantalla = set(r[0] for r in registros_pantalla)

        # Los que estaban cargados y ya no están en pantalla quedan libres
        ids_a_limpiar = ids_previos_en_bd - ids_actuales_en_pantalla
        for id_old in ids_a_limpiar:
            cursor.execute(
                "UPDATE modymoi SET horario_semana='', sector_semana='', planta_semana='' WHERE id=?",
                (id_old,),
            )

        # Los que están en pantalla quedan asignados (y dejan de ser disponibles)
        for id_op, operario_nombre, turno, sector in registros_pantalla:
            cursor.execute(
                """
                UPDATE modymoi
                SET operario=?, horario_semana=?, sector_semana=?,
                    planta_semana='Chocolates', semana=?
                WHERE id=?
                """,
                (operario_nombre, turno, sector, sem_val, id_op),
            )

        self.conexion_db.commit()

    def cerrar_conexion(self):
        if self.conexion_db:
            self.conexion_db.close()
