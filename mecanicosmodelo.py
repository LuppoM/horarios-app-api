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
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    def _resolver_sector_mecanicos(self, planta, sector_enviado=None):
        if sector_enviado and str(sector_enviado).strip():
            return str(sector_enviado).strip()

        pla_up = str(planta or "").strip().upper()
        sectores = self.obtener_sectores_mantenimiento()

        for row in sectores:
            nombre_sec = str(row[0] or "").strip()
            planta_sec = str(row[3] or "").strip().upper()
            if pla_up and (pla_up in nombre_sec.upper() or pla_up == planta_sec):
                return nombre_sec

        if "CHOCO" in pla_up:
            return "PLANTA CHOCOLATES"
        if "GOLOS" in pla_up:
            return "PLANTA GOLOSINAS"
        if "VACAC" in pla_up:
            return "PERSONAL DE VACACIONES"
        return str(planta or "").strip()

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
            try:
                cursor.close()
            except Exception:
                pass

        return self._cache_turnos.get(str(tipo_horario or "").upper().strip(), [])

    def obtener_mecanicos_disponibles(self):
        cursor = self.conexion_db.cursor()
        try:
            cursor.execute("SELECT id, operario FROM mecanicos ORDER BY operario ASC;")
            filas = cursor.fetchall()
            return [[f[0], f[1]] if not isinstance(f, dict) else [f["id"], f["operario"]] for f in filas]
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    def obtener_asignaciones_semana(self, semana):
        cursor = self.conexion_db.cursor()
        try:
            if hasattr(self.conexion_db, "rollback"):
                self.conexion_db.rollback()

            sem_val = int(semana) if str(semana).isdigit() else semana
            cursor.execute("""
                SELECT id, operario, horario,
                       COALESCE(planta, '') AS planta,
                       COALESCE(sector, '') AS sector
                FROM mecanicos
                WHERE semana = %s
                  AND horario IS NOT NULL
                  AND TRIM(horario) != ''
                ORDER BY id ASC, operario ASC;
            """, (sem_val,))
            filas = cursor.fetchall()
            salida = []
            for f in filas:
                if isinstance(f, dict):
                    id_op = f["id"]
                    op = f["operario"]
                    hor = f["horario"]
                    pla = f.get("planta") or ""
                    sec = self._resolver_sector_mecanicos(pla, f.get("sector"))
                else:
                    id_op, op, hor = f[0], f[1], f[2]
                    pla = f[3] if len(f) > 3 else ""
                    sec_raw = f[4] if len(f) > 4 else ""
                    sec = self._resolver_sector_mecanicos(pla, sec_raw)
                salida.append([id_op, op, hor, pla, sec])
            return salida
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    def guardar_asignaciones_mecanicos(self, semana, registros):
        cursor = self.conexion_db.cursor()
        sem_val = int(semana) if str(semana).isdigit() else semana
        try:
            if hasattr(self.conexion_db, "rollback"):
                self.conexion_db.rollback()

            cursor.execute("UPDATE mecanicos SET horario = NULL, sector = NULL WHERE semana = %s;", (sem_val,))

            for item in (registros or []):
                if not item or len(item) < 3:
                    continue

                if len(item) >= 4:
                    id_op, horario, planta, sector_item = item[0], item[1], item[2], item[3]
                else:
                    id_op, horario, planta = item[0], item[1], item[2]
                    sector_item = None

                if not id_op:
                    continue

                id_op_val = int(id_op) if str(id_op).strip().isdigit() else id_op
                sector_resuelto = self._resolver_sector_mecanicos(planta, sector_item)

                cursor.execute("""
                    UPDATE mecanicos
                    SET horario = %s, planta = %s, sector = %s, semana = %s
                    WHERE id = %s;
                """, (horario, planta, sector_resuelto, sem_val, id_op_val))

            self.conexion_db.commit()
        except Exception:
            if hasattr(self.conexion_db, "rollback"):
                try:
                    self.conexion_db.rollback()
                except Exception:
                    pass
            raise
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    def cerrar_conexion(self):
        if hasattr(self, 'conexion_db') and self.conexion_db:
            try:
                self.conexion_db.close()
            except Exception:
                pass