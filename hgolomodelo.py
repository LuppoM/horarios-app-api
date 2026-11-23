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
        self._cache_modymoi = None
        self._cache_turnos = None

    def _leer_modymoi_completo(self):
        """Lee la tabla modymoi UNA sola vez por instancia para alimentar todos los métodos."""
        if self._cache_modymoi is not None:
            return self._cache_modymoi

        cursor = self.conexion_db.cursor()
        cursor.execute(
            """
            SELECT id, operario, "Horario", "Sector", "Planta", semana
            FROM modymoi
            ORDER BY operario ASC
            """
        )
        filas = _filas(cursor)
        self._cache_modymoi = filas
        self.operarios_dict = {r[0]: r[1] for r in filas if r[1]}
        return filas

    def cargar_operarios(self):
        """Carga todos los operarios desde la base de datos"""
        self._leer_modymoi_completo()

    def obtener_operarios(self):
        """Devuelve todos los operarios cargados"""
        self._leer_modymoi_completo()
        return self.operarios_dict

    def obtener_sectores_golosinas(self):
        """Obtiene los sectores de producción, su tipo de horario y si requieren dotación de Golosinas desde la base de datos"""
        cursor = self.conexion_db.cursor()
        try:
            cursor.execute(
                """
                SELECT nombre_sector, tipo_horario, requiere_dotacion
                FROM sectores
                WHERE LOWER(TRIM(planta)) IN ('golosinas', 'golosina')
                  AND LOWER(TRIM(COALESCE(area, ''))) IN ('produccion', 'producción')
                ORDER BY id ASC
                """
            )
            return _filas(cursor) or []
        except Exception as e:
            print(f"Error al obtener sectores de golosinas: {e}")
            return []

    def obtener_turnos_por_tipo(self, tipo_horario):
        """Busca en la base de datos los turnos asociados al tipo de horario (con caché en memoria)"""
        if self._cache_turnos is None:
            self._cache_turnos = {}
            cursor = self.conexion_db.cursor()
            try:
                cursor.execute("SELECT tipo, horarios_definidos FROM tipohorario")
                for row in _filas(cursor):
                    if row[0] and row[1]:
                        clave = str(row[0]).upper().strip()
                        self._cache_turnos[clave] = [t.strip() for t in row[1].split(",")]
            except Exception as e:
                print(f"Error al obtener turnos por tipo: {e}")

        return self._cache_turnos.get(str(tipo_horario).upper().strip(), [])

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
        sem_str = str(semana).strip()
        if sem_str in self.operarios_asignados:
            return self.operarios_asignados[sem_str]

        filas = self._leer_modymoi_completo()
        asignados = set(
            r[0]
            for r in filas
            if str(r[5] or "").strip() == sem_str
            and (r[1] or "").strip() != ""
            and (r[3] or "").strip() != ""
        )
        self.operarios_asignados[sem_str] = asignados
        return asignados

    def obtener_operarios_disponibles(self, semana=None):
        """Devuelve todos los operarios que no están asignados ni a un Sector ni a una Planta (sin re-consultar BD)."""
        try:
            filas = self._leer_modymoi_completo()
            resultado = []
            for id_op, operario, _, sector, planta, _ in filas:
                op_str = (operario or "").strip()
                if not op_str:
                    continue
                sec_str = (sector or "").strip().lower()
                pla_str = (planta or "").strip().lower()
                if sec_str in ("", "null") and pla_str in ("", "null"):
                    resultado.append((id_op, operario))
            return resultado
        except Exception as e:
            print(f"Error al obtener operarios disponibles: {e}")
            return []

    def obtener_datos_semana(self, semana):
        """Devuelve los operarios asignados a Golosinas para la semana dada (sin re-consultar BD)."""
        sem_str = str(semana).strip()
        filas = self._leer_modymoi_completo()
        resultado = []
        for id_op, operario, horario, sector, planta, sem_row in filas:
            if (
                str(sem_row or "").strip() == sem_str
                and (planta or "").strip().lower() in ("golosinas", "golosina")
                and (sector or "").strip() != ""
            ):
                resultado.append((id_op, operario, horario, sector))
        return resultado

    def guardar_operario(self, id_val, operario, horario, sector, semana, hacer_commit=True):
        """Realiza el UPDATE directo a las columnas Horario, Sector, Planta y semana"""
        cursor = self.conexion_db.cursor()
        cursor.execute(
            """
            UPDATE modymoi
            SET operario = %s, "Horario" = %s, "Sector" = %s, "Planta" = 'Golosinas', semana = %s
            WHERE id = %s
            """,
            (operario, horario, sector, str(semana), id_val),
        )
        if hacer_commit:
            self.conexion_db.commit()

        self.operarios_dict[id_val] = operario
        self._cache_modymoi = None
        if semana in self.operarios_asignados:
            self.operarios_asignados[semana].add(id_val)

    def limpiar_operario(self, id_val, hacer_commit=True):
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
        if hacer_commit:
            self.conexion_db.commit()

        self._cache_modymoi = None
        for semana, asignados in self.operarios_asignados.items():
            asignados.discard(id_val)

    def guardar_datos_semana(self, semana, registros_pantalla):
        """Guarda toda la grilla semanal en una única transacción (1 solo commit)."""
        cursor = self.conexion_db.cursor()
        sem_val = str(semana).strip()

        # Limpieza de semanas anteriores solo al guardar
        self.eliminar_datos_semanas_anteriores(semana_actual=sem_val)

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
        ids_a_limpiar = ids_previos_en_bd - ids_actuales_en_pantalla

        for id_old in ids_a_limpiar:
            self.limpiar_operario(id_old, hacer_commit=False)

        for id_op, operario_nombre, turno, sector in registros_pantalla:
            self.guardar_operario(id_op, operario_nombre, turno, sector, sem_val, hacer_commit=False)

        self.conexion_db.commit()


# Alias por retrocompatibilidad con importaciones previas en la API
ModeloHGoloWeb = ModeloHGolo