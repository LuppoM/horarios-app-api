from datetime import date, datetime, timedelta
import json
import conexion


class ModeloDTProgramadaWeb:

    def __init__(self, conexion_db=None):
        if conexion_db:
            self.conexion_db = conexion_db
        else:
            self.conexion_db = conexion.obtener_conexion()

    def obtener_numero_semana_personalizado(self, fecha=None):
        """Calcula el número de semana de producción personalizado.
        Idéntico a principalmodelo, HChoco y HGolo.
        """
        if fecha is None:
            fecha = date.today()
        elif isinstance(fecha, datetime):
            fecha = fecha.date()

        # Si el día es domingo, la semana operativa empieza/corresponde al lunes siguiente
        if fecha.weekday() == 6:
            fecha_ajustada = fecha + timedelta(days=1)
        else:
            fecha_ajustada = fecha

        # Obtiene el número de semana de la fecha
        return fecha_ajustada.isocalendar()[1]

    def obtener_sectores_rotativos_por_planta(self, planta):
        try:
            cursor = self.conexion_db.cursor()
            cursor.execute("""
                SELECT nombre_sector 
                FROM sectores 
                WHERE LOWER(planta) = LOWER(%s) 
                  AND LOWER(tipo_horario) = 'rotativo'
                  AND requiere_dotacion = 1
                ORDER BY id ASC
            """, (planta,))
            filas = cursor.fetchall()
            
            sectores = []
            for f in filas:
                if isinstance(f, dict):
                    sectores.append(f.get("nombre_sector"))
                else:
                    sectores.append(f[0])
            return sectores
        except Exception as e:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            print(f"Error al obtener sectores para {planta}: {e}")
            return []

    def obtener_turnos_por_tipo(self, tipo="ROTATIVO"):
        horarios_predeterminados = ["06:00 a 14:00", "14:00 a 22:00", "22:00 a 06:00"]
        try:
            cursor = self.conexion_db.cursor()
            cursor.execute("""
                SELECT horarios_definidos 
                FROM tipohorario 
                WHERE LOWER(tipo) = LOWER(%s)
            """, (tipo,))
            fila = cursor.fetchone()
            
            cadena_horarios = None
            if fila:
                cadena_horarios = fila.get("horarios_definidos") if isinstance(fila, dict) else fila[0]

            if cadena_horarios:
                if cadena_horarios.strip().startswith("["):
                    return json.loads(cadena_horarios)
                return [h.strip() for h in cadena_horarios.split(",") if h.strip()]
            return horarios_predeterminados
        except Exception as e:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            print(f"Error al obtener turnos: {e}")
            return horarios_predeterminados

    def obtener_dotaciones_semana(self, semana):
        resultado = {"Chocolate": {}, "Golosinas": {}}
        try:
            cursor = self.conexion_db.cursor()
            cursor.execute("""
                SELECT planta, sector, rango_horario, cantidad_operarios 
                FROM dotacion_teorica_horarios 
                WHERE semana_inicio::text = %s
            """, (str(semana),))
            filas = cursor.fetchall()

            for f in filas:
                if isinstance(f, dict):
                    planta = f.get("planta")
                    sector = f.get("sector")
                    rango = f.get("rango_horario")
                    cantidad = f.get("cantidad_operarios")
                else:
                    planta, sector, rango, cantidad = f[0], f[1], f[2], f[3]

                if planta not in resultado:
                    resultado[planta] = {}
                if sector not in resultado[planta]:
                    resultado[planta][sector] = {}
                resultado[planta][sector][rango] = cantidad

            return resultado
        except Exception as e:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            print(f"Error al obtener dotaciones semana {semana}: {e}")
            return resultado

    def guardar_dotaciones(self, semana, datos_completos):
        try:
            cursor = self.conexion_db.cursor()
            for planta, sectores in datos_completos.items():
                for sector, horarios in sectores.items():
                    for rango_horario, cantidad in horarios.items():
                        cursor.execute("""
                            INSERT INTO dotacion_teorica_horarios 
                                (semana_inicio, planta, sector, rango_horario, cantidad_operarios)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (semana_inicio, planta, sector, rango_horario) 
                            DO UPDATE SET cantidad_operarios = EXCLUDED.cantidad_operarios
                        """, (str(semana), planta, sector, rango_horario, cantidad))

            self.conexion_db.commit()
            return True, "Guardado exitoso"
        except Exception as e:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            print(f"Error al guardar dotaciones: {e}")
            return False, str(e)

    def cerrar_conexion(self):
        if hasattr(self, 'conexion_db') and self.conexion_db:
            try:
                self.conexion_db.close()
            except Exception:
                pass
    def obtener_estado_programacion(self, semana: str) -> dict:
        """
        Consulta el estado de la programación para una semana en la tabla estados_programacion.
        """
        try:
            cursor = self.conexion_db.cursor()
            query = """
                SELECT semana, estado, modificado_por, fecha_modificacion 
                FROM estados_programacion 
                WHERE semana = %s;
            """
            cursor.execute(query, (str(semana),))
            row = cursor.fetchone()

            if row:
                return {
                    "semana": row[0],
                    "estado": row[1], # p.ej. 'FINALIZADO' o 'PENDIENTE'
                    "modificado_por": row[2],
                    "fecha_modificacion": row[3].strftime("%Y-%m-%d %H:%M:%S") if row[3] else None
                }
            return {"semana": str(semana), "estado": "PENDIENTE", "modificado_por": "", "fecha_modificacion": None}

        except Exception as e:
            print(f"Error al obtener estado de programación para semana {semana}: {e}")
            return {"semana": str(semana), "estado": "PENDIENTE", "modificado_por": "", "fecha_modificacion": None}

    def actualizar_estado_programacion(self, semana: str, estado: str = "FINALIZADO", usuario: str = "Programacion") -> bool:
        """
        Registra o actualiza el estado de la programación en estados_programacion (UPSERT).
        """
        try:
            cursor = self.conexion_db.cursor()
            query = """
                INSERT INTO estados_programacion (semana, estado, modificado_por, fecha_modificacion)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (semana) 
                DO UPDATE SET 
                    estado = EXCLUDED.estado,
                    modificado_por = EXCLUDED.modificado_por,
                    fecha_modificacion = NOW();
            """
            cursor.execute(query, (str(semana), estado, usuario))
            self.conexion_db.commit()
            return True
        except Exception as e:
            if hasattr(self, 'conexion_db') and self.conexion_db:
                self.conexion_db.rollback()
            print(f"Error al actualizar estado_programacion: {e}")
            return False
