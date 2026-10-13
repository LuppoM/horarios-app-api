# hgolomodelo.py
import conexion


def _a_tupla(row):
    """Convierte una fila a tupla, venga como tupla, dict o sqlite3.Row."""
    if row is None:
        return None
    if isinstance(row, dict):
        return tuple(row.values())
    return tuple(row)


def _filas(cursor):
    """fetchall() siempre como lista de tuplas."""
    return [_a_tupla(r) for r in cursor.fetchall()]


class ModeloHGoloWeb:

    def __init__(self):
        self.conexion_db = conexion.obtener_conexion()
        self.operarios_dict = {}
        self.cargar_operarios()

    def cargar_operarios(self):
        cursor = self.conexion_db.cursor()
        cursor.execute("SELECT id, operario FROM modymoi ORDER BY operario ASC")
        rows = _filas(cursor)
        self.operarios_dict = {row[0]: row[1] for row in rows if row[1]}

    def obtener_operarios(self):
        return self.operarios_dict

    def obtener_sectores_golosinas(self):
        cursor = self.conexion_db.cursor()
        try:
            cursor.execute(
                """
                SELECT nombre_sector, tipo_horario, requiere_dotacion 
                FROM sectores 
                WHERE LOWER(TRIM(planta)) IN ('golosinas', 'golosina')
                ORDER BY id ASC
                """
            )
            return _filas(cursor) or []
        except Exception as e:
            print(f"Error al obtener sectores de golosinas: {e}")
            return []

    def obtener_turnos_por_tipo(self, tipo_horario):
        cursor = self.conexion_db.cursor()
        try:
            cursor.execute(
                "SELECT horarios_definidos FROM tipohorario WHERE UPPER(TRIM(tipo)) = %s",
                (str(tipo_horario).upper().strip(),),
            )
            row = _a_tupla(cursor.fetchone())
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
                WHERE semana_inicio = %s AND LOWER(TRIM(planta)) IN ('golosinas', 'golosina')
                """,
                (str(semana),),
            )
            resultados = {}
            for row in _filas(cursor):
                if len(row) == 4:
                    _, sector, rango, cantidad = row
                else:
                    sector, rango, cantidad = row[0], row[1], row[2]

                if sector not in resultados:
                    resultados[sector] = {}
                resultados[sector][rango] = cantidad
            return resultados
        except Exception as e:
            print(f"Error dotación teórica golosinas: {e}")
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
            for id_op, nombre in _filas(cursor)
            if id_op not in excluidos
        ]

    def obtener_datos_semana(self, semana):
        cursor = self.conexion_db.cursor()
        cursor.execute(
            """
            SELECT id, operario, "Horario", "Sector"
            FROM modymoi
            WHERE semana = %s AND LOWER(TRIM("Planta")) IN ('golosinas', 'golosina')
              AND "Sector" IS NOT NULL AND TRIM("Sector") != ''
            """,
            (str(semana),),
        )
        return _filas(cursor)

    def guardar_datos_semana(self, semana, registros_pantalla):
        cursor = self.conexion_db.cursor()
        sem_val = str(semana).strip()

        cursor.execute(
            """
            SELECT id
            FROM modymoi
            WHERE semana = %s AND LOWER(TRIM("Planta")) IN ('golosinas', 'golosina')
            """,
            (sem_val,),
        )
        ids_previos_en_bd = set(row[0] for row in _filas(cursor))
        ids_actuales_en_pantalla = set(r[0] for r in registros_pantalla)

        # 1. Blanquear los operarios removidos de la pantalla
        ids_a_limpiar = ids_previos_en_bd - ids_actuales_en_pantalla
        for id_old in ids_a_limpiar:
            cursor.execute(
                'UPDATE modymoi SET "Horario" = \'\', "Sector" = \'\', "Planta" = \'\' WHERE id = %s',
                (id_old,),
            )

        # 2. Guardar asignaciones actuales
        for id_op, operario_nombre, turno, sector in registros_pantalla:
            cursor.execute(
                """
                UPDATE modymoi
                SET operario = %s, "Horario" = %s, "Sector" = %s,
                    "Planta" = 'Golosinas', semana = %s
                WHERE id = %s
                """,
                (operario_nombre, turno, sector, sem_val, id_op),
            )

        self.conexion_db.commit()

    def cerrar_conexion(self):
        if self.conexion_db:
            self.conexion_db.close()
