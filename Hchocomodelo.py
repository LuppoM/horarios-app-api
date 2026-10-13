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
        self.operarios_dict = {
            (row["id"] if isinstance(row, dict) else row[0]): (row["operario"] if isinstance(row, dict) else row[1])
            for row in rows if (row["operario"] if isinstance(row, dict) else row[1])
        }

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
                ORDER BY id ASC
                """
            )
            rows = cursor.fetchall() or []
            sectores_list = []

            for row in rows:
                nom_sector = row[0] if not isinstance(row, dict) else row["nombre_sector"]
                tipo_horario = row[1] if not isinstance(row, dict) else row["tipo_horario"]
                req_dotacion = row[2] if not isinstance(row, dict) else row["requiere_dotacion"]

                turnos = self.obtener_turnos_por_tipo(tipo_horario)

                sectores_list.append({
                    "sector": nom_sector,
                    "tipo_horario": tipo_horario,
                    "requiere_dotacion": req_dotacion,
                    "turnos": turnos
                })

            return sectores_list
        except Exception as e:
            print(f"Error al obtener sectores: {e}")
            return []

    def obtener_turnos_por_tipo(self, tipo_horario):
        cursor = self.conexion_db.cursor()
        try:
            cursor.execute(
                "SELECT horarios_definidos FROM tipohorario WHERE UPPER(TRIM(tipo)) = %s",
                (str(tipo_horario).upper().strip(),),
            )
            row = cursor.fetchone()
            if row:
                val = row[0] if not isinstance(row, dict) else row["horarios_definidos"]
                if val:
                    return [t.strip() for t in val.split(",")]
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
                WHERE semana_inicio = %s AND LOWER(TRIM(planta)) IN ('chocolate', 'chocolates')
                """,
                (str(semana),),
            )
            resultados = {}
            rows = cursor.fetchall() or []
            
            for row in rows:
                if isinstance(row, dict):
                    sector = row["sector"]
                    rango = row["rango_horario"]
                    cantidad = row["cantidad_operarios"]
                else:
                    # Desempaquetado seguro sin importar la cantidad de columnas devueltas
                    if len(row) == 4:
                        _, sector, rango, cantidad = row
                    else:
                        sector, rango, cantidad = row[0], row[1], row[2]

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
        rows = cursor.fetchall() or []
        return [
            (
                row[0] if not isinstance(row, dict) else row["id"],
                row[1] if not isinstance(row, dict) else row["operario"]
            )
            for row in rows
            if (row[0] if not isinstance(row, dict) else row["id"]) not in excluidos
        ]

    def obtener_datos_semana(self, semana):
        cursor = self.conexion_db.cursor()
        cursor.execute(
            """
            SELECT id, operario, "Horario", "Sector"
            FROM modymoi
            WHERE semana = %s AND LOWER(TRIM("Planta")) IN ('chocolates', 'chocolate')
            AND "Sector" IS NOT NULL AND TRIM("Sector") != ''
            """,
            (str(semana),),
        )
        rows = cursor.fetchall() or []
        
        # Formateamos estrictamente a 4 valores por fila: (id, operario, horario, sector)
        datos = []
        for r in rows:
            if isinstance(r, dict):
                datos.append((r["id"], r["operario"], r["Horario"], r["Sector"]))
            else:
                datos.append((r[0], r[1], r[2], r[3]))
        return datos

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
        rows_previos = cursor.fetchall() or []
        ids_previos_en_bd = set(
            row[0] if not isinstance(row, dict) else row["id"] for row in rows_previos
        )
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
