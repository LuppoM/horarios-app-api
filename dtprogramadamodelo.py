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
        if fecha is None:
            fecha = date.today()
        elif isinstance(fecha, datetime):
            fecha = fecha.date()

        if fecha.weekday() == 6:
            fecha_ajustada = fecha + timedelta(days=1)
        else:
            fecha_ajustada = fecha

        return fecha_ajustada.isocalendar()[1]

    def obtener_sectores_rotativos_por_planta(self, planta):
        cursor = None
        try:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()

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
        finally:
            if cursor:
                cursor.close()

    def obtener_turnos_por_tipo(self, tipo="ROTATIVO"):
        horarios_predeterminados = ["06:00 a 14:00", "14:00 a 22:00", "22:00 a 06:00"]
        cursor = None
        try:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()

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
        finally:
            if cursor:
                cursor.close()

    def obtener_dotaciones_semana(self, semana):
        resultado = {"Chocolate": {}, "Golosinas": {}}
        cursor = None
        try:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()

            cursor = self.conexion_db.cursor()
            cursor.execute("""
                SELECT planta, sector, rango_horario, cantidad_operarios 
                FROM dotacion_teorica_horarios 
                WHERE semana_inicio::text = %s
            """, (str(semana).strip(),))
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
        finally:
            if cursor:
                cursor.close()

    def guardar_dotaciones(self, semana, datos_completos):
        cursor = None
        try:
            # 1. Limpieza de transacciones previas
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()

            cursor = self.conexion_db.cursor()
            val_semana = str(semana).strip()

            # 2. Desduplicación en memoria de la matriz ingresada
            registros_unicos = {}

            for planta, sectores in datos_completos.items():
                if not isinstance(sectores, dict):
                    continue
                for sector, horarios in sectores.items():
                    if not isinstance(horarios, dict):
                        continue
                    for rango_horario, cantidad in horarios.items():
                        # Excluimos columnas acumulativas de días
                        if str(rango_horario).upper() in ["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES"]:
                            continue

                        planta_clean = str(planta).strip()
                        sector_clean = str(sector).strip()
                        rango_clean = str(rango_horario).strip()
                        cant_val = int(cantidad or 0)

                        clave = (val_semana, planta_clean, sector_clean, rango_clean)
                        registros_unicos[clave] = cant_val

            # 3. Limpieza de la dotación existente para esa semana en particular
            cursor.execute("DELETE FROM dotacion_teorica_horarios WHERE semana_inicio::text = %s;", (val_semana,))

            # 4. Inserción masiva en lote
            query_insert = """
                INSERT INTO dotacion_teorica_horarios 
                    (semana_inicio, planta, sector, rango_horario, cantidad_operarios)
                VALUES (%s, %s, %s, %s, %s);
            """

            lista_valores = [
                (semana_k, planta_k, sector_k, rango_k, cant_k)
                for (semana_k, planta_k, sector_k, rango_k), cant_k in registros_unicos.items()
            ]

            if lista_valores:
                cursor.executemany(query_insert, lista_valores)

            self.conexion_db.commit()
            return True, "Guardado exitoso"

        except Exception as e:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            print(f"Error detallado en guardar_dotaciones: {e}")
            return False, str(e)

        finally:
            if cursor:
                cursor.close()
                
    def actualizar_estado_programacion(self, semana: str, estado: str = "FINALIZADO", usuario: str = "Programacion") -> bool:
        cursor = None
        try:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()

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
            cursor.execute(query, (str(semana).strip(), estado, usuario))
            self.conexion_db.commit()
            return True
        except Exception as e:
            if hasattr(self.conexion_db, 'rollback'):
                self.conexion_db.rollback()
            print(f"Error al actualizar estado_programacion: {e}")
            return False
        finally:
            if cursor:
                cursor.close()

    def cerrar_conexion(self):
        if hasattr(self, 'conexion_db') and self.conexion_db:
            try:
                self.conexion_db.close()
            except Exception:
                pass
