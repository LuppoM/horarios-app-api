from datetime import date, timedelta
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

        def inicio_semana_1(anio):
            primer_dia = date(anio, 1, 1)
            return primer_dia + timedelta(days=(7 - primer_dia.weekday()) % 7)

        inicio = inicio_semana_1(fecha.year)
        if fecha < inicio:
            inicio = inicio_semana_1(fecha.year - 1)

        return ((fecha - inicio).days // 7) + 1

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
                        # Usamos la sintaxis de PostgreSQL (ON CONFLICT) para reemplazar el registro si ya existe
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
