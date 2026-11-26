import conexion


class ModeloDepositoMPWeb:

    def __init__(self):
        self.conexion_db = conexion.obtener_conexion()
        self._cache_turnos = None

    @staticmethod
    def _resolver_planta_finde(sector):
        sec_upper = str(sector or "").upper()
        if "CHOCOLATES" in sec_upper:
            return "Chocolate"
        if "GOLOSINAS" in sec_upper:
            return "Golosinas"
        return ""

    def obtener_sectores_area(self):
        """Obtiene los sectores de DEPOSITOMP desde la tabla sectores."""
        cursor = self.conexion_db.cursor()
        try:
            cursor.execute("""
                SELECT nombre_sector, tipo_horario, requiere_dotacion
                FROM sectores
                WHERE UPPER(TRIM(area)) = 'DEPOSITOMP'
                ORDER BY id ASC
            """)
            filas = cursor.fetchall()
            return [
                (f["nombre_sector"], f["tipo_horario"], f["requiere_dotacion"])
                if isinstance(f, dict) else (f[0], f[1], f[2])
                for f in filas
            ]
        except Exception as e:
            print(f"Error al obtener sectores de DEPOSITOMP: {e}")
            return []
        finally:
            try:
                cursor.close()
            except Exception:
                pass

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
            finally:
                try:
                    cursor.close()
                except Exception:
                    pass

        return self._cache_turnos.get(str(tipo_horario).upper().strip(), [])

    def obtener_operarios_disponibles(self, semana):
        cursor = self.conexion_db.cursor()
        try:
            sem_val = int(semana) if str(semana).isdigit() else semana
            cursor.execute("""
                SELECT id, operario
                FROM depositomp
                WHERE semana = %s AND operario IS NOT NULL AND TRIM(operario) != ''
                ORDER BY operario ASC;
            """, (sem_val,))
            filas = cursor.fetchall()
            return [
                [f[0], f[1]] if not isinstance(f, dict) else [f["id"], f["operario"]]
                for f in filas
            ]
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    def obtener_asignaciones_semana(self, semana):
        cursor = self.conexion_db.cursor()
        try:
            sem_val = int(semana) if str(semana).isdigit() else semana

            # 1. Traer semana desde depositomp
            cursor.execute("""
                SELECT id, operario, horario, COALESCE(NULLIF(TRIM(sector), ''), planta) AS sector_asig
                FROM depositomp
                WHERE semana = %s AND horario IS NOT NULL AND TRIM(horario) != ''
            """, (sem_val,))
            filas_semana = cursor.fetchall()

            resultado = [
                [f["id"], f["operario"], f["horario"], f["sector_asig"]]
                if isinstance(f, dict) else [f[0], f[1], f[2], f[3]]
                for f in filas_semana
            ]

            # 2. Traer finde desde depositomp_finde (incluyendo planta)
            cursor.execute("""
                SELECT operario_id, operario, turno, sector, COALESCE(planta, '') AS planta
                FROM depositomp_finde
                WHERE semana = %s
            """, (sem_val,))
            filas_finde = cursor.fetchall()

            for f in filas_finde:
                if isinstance(f, dict):
                    planta_val = f.get("planta") or self._resolver_planta_finde(f.get("sector"))
                    resultado.append([f["operario_id"], f["operario"], f["turno"], f["sector"], planta_val])
                else:
                    planta_val = f[4] if len(f) > 4 and f[4] else self._resolver_planta_finde(f[3])
                    resultado.append([f[0], f[1], f[2], f[3], planta_val])

            return resultado
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    def guardar_asignaciones_depositomp(self, semana, registros):
        """registros: [[id_operario, operario, turno, sector], ...]"""
        cursor = self.conexion_db.cursor()
        sem_val = int(semana) if str(semana).isdigit() else semana

        try:
            if hasattr(self.conexion_db, "rollback"):
                self.conexion_db.rollback()

            cursor.execute("UPDATE depositomp SET horario = NULL, sector = NULL WHERE semana = %s;", (sem_val,))
            cursor.execute("DELETE FROM depositomp_finde WHERE semana = %s;", (sem_val,))

            for item in (registros or []):
                if not item or len(item) < 4:
                    continue
                id_op, operario, turno, sector = item[0], item[1], item[2], item[3]
                if not id_op or not str(operario or "").strip():
                    continue

                id_op_val = int(id_op) if str(id_op).strip().isdigit() else id_op
                sector_limpio = str(sector).strip()
                turno_limpio = str(turno).strip()
                operario_limpio = str(operario).strip()

                if "FIN DE SEMANA" in sector_limpio.upper():
                    planta_finde = self._resolver_planta_finde(sector_limpio)
                    cursor.execute("""
                        INSERT INTO depositomp_finde (semana, sector, turno, operario_id, operario, planta)
                        VALUES (%s, %s, %s, %s, %s, %s);
                    """, (sem_val, sector_limpio, turno_limpio, id_op_val, operario_limpio, planta_finde))
                else:
                    cursor.execute("""
                        UPDATE depositomp
                        SET horario = %s, sector = %s, planta = %s, semana = %s
                        WHERE id = %s;
                    """, (turno_limpio, sector_limpio, sector_limpio, sem_val, id_op_val))

            self.conexion_db.commit()
        except Exception as e:
            if hasattr(self.conexion_db, "rollback"):
                try:
                    self.conexion_db.rollback()
                except Exception:
                    pass
            detalle = str(e).strip() or repr(e)
            print(f"Error en guardar_asignaciones_depositomp: {detalle}")
            raise RuntimeError(detalle) from e
        finally:
            try:
                cursor.close()
            except Exception:
                pass