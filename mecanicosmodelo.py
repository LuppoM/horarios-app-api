import conexion


class ModeloMecanicosWeb:

    def __init__(self):
        self.conexion_db = conexion.obtener_conexion()
        self._cache_turnos = None

    def _filas(self, cursor):
        filas = cursor.fetchall()
        if not filas:
            return []
        if isinstance(filas[0], dict):
            return [tuple(f.values()) for f in filas]
        return filas

    def obtener_sectores_mantenimiento(self):
        """Obtiene sectores de mantenimiento/mecánicos con su planta y tipo_horario."""
        cursor = self.conexion_db.cursor()
        try:
            cursor.execute("""
                SELECT nombre_sector, tipo_horario, requiere_dotacion, COALESCE(planta, '')
                FROM sectores
                WHERE UPPER(TRIM(COALESCE(area, ''))) IN ('MANTENIMIENTO', 'MECANICOS', 'MECÁNICOS')
                ORDER BY id ASC
            """)
            return self._filas(cursor)
        except Exception as e:
            print(f"Error al obtener sectores de mantenimiento: {e}")
            return []

    def obtener_turnos_por_tipo(self, tipo_horario):
        """Busca los turnos asociados al tipo_horario (con caché)."""
        if self._cache_turnos is None:
            self._cache_turnos = {}
            cursor = self.conexion_db.cursor()
            for tabla in ("tipos_horario", "tipohorario"):
                try:
                    cursor.execute(f"SELECT tipo, horarios_definidos FROM {tabla}")
                    filas = cursor.fetchall()
                    for row in filas:
                        t = row["tipo"] if isinstance(row, dict) else row[0]
                        h = row["horarios_definidos"] if isinstance(row, dict) else row[1]
                        if t and h:
                            clave = str(t).upper().strip()
                            if isinstance(h, list):
                                lista = [str(x).strip() for x in h if str(x).strip()]
                            else:
                                texto = str(h).strip()
                                for sep in ("\n", ";", ","):
                                    if sep in texto:
                                        lista = [p.strip() for p in texto.split(sep) if p.strip()]
                                        break
                                else:
                                    lista = [texto] if texto else []
                            self._cache_turnos[clave] = lista
                    break
                except Exception:
                    self.conexion_db.rollback()
                    continue

        return self._cache_turnos.get(str(tipo_horario or "").upper().strip(), [])

    def obtener_mecanicos_disponibles(self):
        cursor = self.conexion_db.cursor()
        cursor.execute("SELECT id, operario FROM mecanicos ORDER BY operario ASC;")
        filas = cursor.fetchall()
        return [[f[0], f[1]] if not isinstance(f, dict) else [f["id"], f["operario"]] for f in filas]

    def obtener_asignaciones_semana(self, semana):
        cursor = self.conexion_db.cursor()
        sem_val = int(semana) if str(semana).isdigit() else semana
        cursor.execute("""
            SELECT id, operario, horario, planta
            FROM mecanicos
            WHERE semana = %s AND horario IS NOT NULL AND TRIM(horario) != ''
            ORDER BY horario ASC, operario ASC;
        """, (sem_val,))
        filas = cursor.fetchall()
        return [[f[0], f[1], f[2], f[3]] if not isinstance(f, dict) else [f["id"], f["operario"], f["horario"], f["planta"]] for f in filas]

    def guardar_asignaciones_mecanicos(self, semana, registros):
        cursor = self.conexion_db.cursor()
        sem_val = int(semana) if str(semana).isdigit() else semana
        cursor.execute("UPDATE mecanicos SET horario = NULL WHERE semana = %s;", (sem_val,))
        for id_op, horario, planta in registros:
            cursor.execute("""
                UPDATE mecanicos
                SET horario = %s, planta = %s, semana = %s
                WHERE id = %s;
            """, (horario, planta, sem_val, id_op))
        self.conexion_db.commit()

    def cerrar_conexion(self):
        if hasattr(self, 'conexion_db') and self.conexion_db:
            try:
                self.conexion_db.close()
            except Exception:
                pass