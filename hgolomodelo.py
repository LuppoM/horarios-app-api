# hgolomodelo.py
from datetime import date
from principalmodelo import modeloprincipal


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


class ModeloHGolo(modeloprincipal):

    def __init__(self, conexion=None):
        super().__init__()
        if conexion:
            self.conexion_db = conexion
        self.conexion = self.conexion_db
        self.operarios_dict = {}  # {id: nombre}
        self.operarios_asignados = {}  # {semana: set(IDs operarios)}

        self.cargar_operarios()

    def cargar_operarios(self):
        """Carga todos los operarios desde la base de datos"""
        cursor = self.conexion_db.cursor()
        cursor.execute("SELECT id, operario FROM modymoi ORDER BY operario ASC")
        rows = _filas(cursor)
        self.operarios_dict = {row[0]: row[1] for row in rows if row[1]}

    def obtener_operarios(self):
        """Devuelve todos los operarios cargados"""
        return self.operarios_dict

    def obtener_sectores_golosinas(self):
        """Obtiene los sectores, su tipo de horario y si requieren dotación de Golosinas desde la base de datos"""
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
        """Busca en la base de datos los turnos asociados al tipo de horario usando la tabla tipohorario"""
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
            print(f"Error al obtener turnos por tipo: {e}")
        return []

    def obtener_dotacion_teorica(self, semana):
        """Obtiene la dotación teórica por sector y horario para Golosinas"""
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
            print(f"Error al obtener dotación teórica: {e}")
            return {}

    def obtener_operarios_asignados_en_otro_sector(self, semana):
        """Devuelve IDs de operarios que ya tienen sector asignado en una semana"""
        if semana in self.operarios_asignados:
            return self.operarios_asignados[semana]

        cursor = self.conexion_db.cursor()
        cursor.execute(
            """
            SELECT id
            FROM modymoi
            WHERE semana = %s AND operario != '' AND "Sector" != ''
            """,
            (str(semana),),
        )
        asignados = set(row[0] for row in _filas(cursor))
        self.operarios_asignados[semana] = asignados
        return asignados

    def obtener_operarios_disponibles(self, semana=None):
        """Ejecuta la limpieza remota de semanas anteriores y devuelve los operarios 
        cuyo Horario, Sector y Planta están libres.
        """
        if semana:
            # Invoca a la limpieza heredada de modeloprincipal
            self.eliminar_datos_semanas_anteriores(semana_actual=semana)

        cursor = self.conexion_db.cursor()
        cursor.execute(
            """
            SELECT id, operario
            FROM modymoi
            WHERE ("Sector" IS NULL OR TRIM("Sector") = '')
              AND ("Horario" IS NULL OR TRIM("Horario") = '')
              AND operario IS NOT NULL AND TRIM(operario) != ''
            ORDER BY operario ASC
            """
        )
        return _filas(cursor)

    def obtener_datos_semana(self, semana):
        """Ejecuta la limpieza previa y devuelve los operarios asignados a Golosinas"""
        if semana:
            self.eliminar_datos_semanas_anteriores(semana_actual=semana)

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

    def guardar_operario(self, id_val, operario, horario, sector, semana):
        """Realiza el UPDATE directo a las columnas "Horario", "Sector", "Planta" y semana"""
        cursor = self.conexion_db.cursor()
        cursor.execute(
            """
            UPDATE modymoi
            SET operario = %s, "Horario" = %s, "Sector" = %s, "Planta" = 'Golosinas', semana = %s
            WHERE id = %s
            """,
            (operario, horario, sector, str(semana), id_val),
        )
        self.conexion_db.commit()

        self.operarios_dict[id_val] = operario
        if semana in self.operarios_asignados:
            self.operarios_asignados[semana].add(id_val)

    def limpiar_operario(self, id_val):
        """Elimina la asignación de un operario blanqueando Horario, Sector y Planta"""
        cursor = self.conexion_db.cursor()
        cursor.execute(
            """
            UPDATE modymoi
            SET "Horario" = '', "Sector" = '', "Planta" = ''
            WHERE id = %s
            """,
            (id_val,),
        )
        self.conexion_db.commit()

        for semana, asignados in self.operarios_asignados.items():
            asignados.discard(id_val)

    def guardar_datos_semana(self, semana, registros_pantalla):
        """Guarda la grilla semanal reutilizando limpiar_operario y guardar_operario."""
        cursor = self.conexion_db.cursor()
        sem_val = str(semana).strip()

        # 1. Obtenemos los IDs de los operarios que estaban en Golosinas para esta semana en la BD
        cursor.execute(
            """
            SELECT id 
            FROM modymoi 
            WHERE semana = %s AND LOWER(TRIM("Planta")) IN ('golosinas', 'golosina')
            """,
            (sem_val,),
        )
        ids_previos_en_bd = set(row[0] for row in _filas(cursor))

        # 2. Obtenemos los IDs presentes actualmente en la pantalla
        ids_actuales_en_pantalla = set(r[0] for r in registros_pantalla)

        # 3. Calculamos quiénes fueron reemplazados o quitados
        ids_a_limpiar = ids_previos_en_bd - ids_actuales_en_pantalla

        # 4. Reutilizamos limpiar_operario para los que ya no están
        for id_old in ids_a_limpiar:
            self.limpiar_operario(id_old)

        # 5. Reutilizamos guardar_operario para asignar los seleccionados
        for id_op, operario_nombre, turno, sector in registros_pantalla:
            self.guardar_operario(id_op, operario_nombre, turno, sector, sem_val)


# Alias por retrocompatibilidad con importaciones previas en la API
ModeloHGoloWeb = ModeloHGolo
