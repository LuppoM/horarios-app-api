import conexion


class ModeloAnalistasCalidadWeb:

    def __init__(self):
        self.conexion_db = conexion.obtener_conexion()
        self._cache_turnos = None

    def obtener_sectores_area(self):
        """Obtiene los sectores de CALIDAD desde la tabla sectores."""
        cursor = self.conexion_db.cursor()
        try:
            cursor.execute("""
                SELECT nombre_sector, tipo_horario, requiere_dotacion
                FROM sectores
                WHERE UPPER(TRIM(area)) = 'CALIDAD'
                ORDER BY id ASC
            """)
            filas = cursor.fetchall()
            return [
                (f["nombre_sector"], f["tipo_horario"], f["requiere_dotacion"])
                if isinstance(f, dict) else (f[0], f[1], f[2])
                for f in filas
            ]
        except Exception as e:
            print(f"Error al obtener sectores de CALIDAD: {e}")
            return []

    def obtener_turnos_por_tipo(self, tipo_horario):
        """Busca en tipohorario los turnos asociados al tipo de horario (con caché)."""
        if self._cache_turnos is None:
            self._cache_turnos = {}
            cursor = self.conexion_db.cursor()
            try:
                cursor.execute("SELECT tipo, horarios_definidos FROM tipohorario")
                for row in cursor.fetchall():
                    t = row["tipo"] if isinstance(row, dict) else row[0]
                    h = row["horarios_definidos"] if isinstance(row, dict) else row[1]
                    if t and h:
                        clave = str(t).upper().strip()
                        self._cache_turnos[clave] = [x.strip() for x in h.split(",") if x.strip()]
            except Exception as e:
                print(f"Error al obtener turnos por tipo: {e}")

        return self._cache_turnos.get(str(tipo_horario).upper().strip(), [])

    def obtener_analistas_disponibles(self):
        cursor = self.conexion_db.cursor()
        cursor.execute("SELECT id, operario FROM operarios ORDER BY operario ASC;")
        filas = cursor.fetchall()
        return [
            [f[0], f[1]] if not isinstance(f, dict) else [f["id"], f["operario"]]
            for f in filas
        ]

    def obtener_asignaciones_semana(self, semana):
        cursor = self.conexion_db.cursor()
        sem_val = int(semana) if str(semana).isdigit() else semana
        cursor.execute("""
            SELECT id, operario, horario, COALESCE(NULLIF(TRIM(sector), ''), planta) AS sector_asig
            FROM analistascalidad
            WHERE semana = %s AND horario IS NOT NULL AND TRIM(horario) != ''
            ORDER BY horario ASC, operario ASC;
        """, (sem_val,))
        filas = cursor.fetchall()
        return [
            [f["id"], f["operario"], f["horario"], f["sector_asig"]]
            if isinstance(f, dict) else [f[0], f[1], f[2], f[3]]
            for f in filas
        ]

    def guardar_asignaciones_analistas(self, semana, registros):
        """registros: [[id_operario, operario, turno, sector], ...]"""
        cursor = self.conexion_db.cursor()
        sem_val = int(semana) if str(semana).isdigit() else semana

        cursor.execute("UPDATE analistascalidad SET horario = NULL, sector = NULL WHERE semana = %s;", (sem_val,))

        for id_op, _, turno, sector in registros:
            cursor.execute("""
                UPDATE analistascalidad
                SET horario = %s, sector = %s, planta = %s, semana = %s
                WHERE id = %s;
            """, (turno, sector, sector, sem_val, id_op))

        self.conexion_db.commit()

    def cerrar_conexion(self):
        if hasattr(self, 'conexion_db') and self.conexion_db:
            try:
                self.conexion_db.close()
            except Exception:
                pass