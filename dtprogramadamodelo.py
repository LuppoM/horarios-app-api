import os
import sqlite3
import sys
import json
from datetime import datetime, date, timedelta

def _obtener_conexion_local():
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_path, "HORARIOS.db")
    return sqlite3.connect(db_path, check_same_thread=False)

class ModeloDTProgramadaWeb:
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
        conn = _obtener_conexion_local()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT nombre_sector 
                FROM sectores 
                WHERE LOWER(planta) = LOWER(?) 
                  AND LOWER(tipo_horario) = 'rotativo'
                  AND requiere_dotacion = 1
                ORDER BY id ASC
            """, (planta,))
            filas = cursor.fetchall()
            conn.close()
            return [f[0] for f in filas]
        except Exception as e:
            conn.close()
            print(f"Error al obtener sectores para {planta}: {e}")
            return []

    def obtener_turnos_por_tipo(self, tipo="ROTATIVO"):
        conn = _obtener_conexion_local()
        cursor = conn.cursor()
        horarios_predeterminados = ["06:00 a 14:00", "14:00 a 22:00", "22:00 a 06:00"]
        try:
            cursor.execute("""
                SELECT horarios_definidos 
                FROM tipohorario 
                WHERE LOWER(tipo) = LOWER(?)
            """, (tipo,))
            fila = cursor.fetchone()
            conn.close()
            if fila and fila[0]:
                cadena_horarios = fila[0]
                if cadena_horarios.strip().startswith("["):
                    return json.loads(cadena_horarios)
                return [h.strip() for h in cadena_horarios.split(",") if h.strip()]
            return horarios_predeterminados
        except Exception as e:
            conn.close()
            print(f"Error al obtener turnos: {e}")
            return horarios_predeterminados

    def obtener_dotaciones_semana(self, semana):
        conn = _obtener_conexion_local()
        cursor = conn.cursor()
        resultado = {"Chocolate": {}, "Golosinas": {}}
        try:
            cursor.execute("""
                SELECT planta, sector, rango_horario, cantidad_operarios 
                FROM dotacion_teorica_horarios 
                WHERE semana_inicio = ?
            """, (str(semana),))
            filas = cursor.fetchall()
            conn.close()
            for planta, sector, rango, cantidad in filas:
                if planta not in resultado:
                    resultado[planta] = {}
                if sector not in resultado[planta]:
                    resultado[planta][sector] = {}
                resultado[planta][sector][rango] = cantidad
            return resultado
        except Exception as e:
            conn.close()
            print(f"Error al obtener dotaciones semana {semana}: {e}")
            return resultado

    def guardar_dotaciones(self, semana, datos_completos):
        conn = _obtener_conexion_local()
        cursor = conn.cursor()
        try:
            for planta, sectores in datos_completos.items():
                for sector, horarios in sectores.items():
                    for rango_horario, cantidad in horarios.items():
                        cursor.execute("""
                            INSERT OR REPLACE INTO dotacion_teorica_horarios 
                                (semana_inicio, planta, sector, rango_horario, cantidad_operarios)
                            VALUES (?, ?, ?, ?, ?)
                        """, (str(semana), planta, sector, rango_horario, cantidad))
            conn.commit()
            conn.close()
            return True, "Guardado exitoso"
        except Exception as e:
            conn.rollback()
            conn.close()
            return False, str(e)
