import os
import sqlite3
import sys
from principalmodelo import modeloprincipal


def _obtener_conexion_local():
    if getattr(sys, "frozen", False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    db_path = os.path.join(base_path, "HORARIOS.db")
    return sqlite3.connect(db_path, check_same_thread=False)


class ModMoiModel:

    def __init__(self, conexion=None):
        self._modelo_principal = modeloprincipal()

    def obtener_numero_semana_personalizado(self, fecha=None):
        return self._modelo_principal.obtener_numero_semana_personalizado(fecha)

    def obtener_datos(self, filtro_columna=None, filtro_valor=None, semana_actual=None):
        """Obtiene las columnas y filas de la semana indicada. Si no se pasa, usa la actual."""
        try:
            conn = _obtener_conexion_local()
            cursor = conn.cursor()
            
            if not semana_actual:
                semana_actual = str(self.obtener_numero_semana_personalizado())

            query_base = """
                SELECT 
                    id,
                    calificacion_mano_obra,
                    operario,
                    semana,
                    Horario AS horario_semana,
                    Sector AS sector_semana,
                    Planta AS planta_semana
                FROM modymoi
                WHERE semana = ?
            """
            
            params = [str(semana_actual)]
            
            if filtro_columna and filtro_valor:
                query_base += f" AND [{filtro_columna}] LIKE ?"
                params.append("%" + filtro_valor + "%")
                
            query_base += " ORDER BY operario ASC"
            
            cursor.execute(query_base, params)
            datos = cursor.fetchall()
            columnas = [desc[0] for desc in cursor.description]
            return columnas, datos
        except sqlite3.OperationalError as e:
            raise Exception(f"Error de SQL: {e}")
        finally:
            try:
                cursor.close()
                conn.close()
            except Exception:
                pass

    def obtener_datos_finde(self, filtro_columna=None, filtro_valor=None, semana_actual=None):
        """Obtiene las filas de fin de semana correspondientes estrictamente a la semana actual."""
        try:
            conn = _obtener_conexion_local()
            cursor = conn.cursor()
            
            if not semana_actual:
                semana_actual = str(self.obtener_numero_semana_personalizado())

            query_base = """
                SELECT 
                    m.id,
                    m.operario,
                    f.semana,
                    f.dia AS finde_dia,
                    f.horario AS finde_horario,
                    f.sector AS finde_sector,
                    f.planta AS finde_planta
                FROM modymoi_finde f
                INNER JOIN modymoi m ON f.id_operario = m.id
                WHERE f.semana = ?
            """
            params = [str(semana_actual)]

            if filtro_columna and filtro_valor:
                col_prefix = (
                    f"f.[{filtro_columna}]"
                    if filtro_columna in ["semana", "dia", "horario", "sector", "planta"]
                    else f"m.[{filtro_columna}]"
                )
                query_base += f" AND {col_prefix} LIKE ?"
                params.append("%" + filtro_valor + "%")

            query_base += " ORDER BY m.operario ASC, f.dia ASC"
            cursor.execute(query_base, params)

            datos = cursor.fetchall()
            columnas = [desc[0] for desc in cursor.description]
            return columnas, datos
        except sqlite3.OperationalError as e:
            raise Exception(f"Error al consultar fin de semana: {e}")
        finally:
            try:
                cursor.close()
                conn.close()
            except Exception:
                pass

    def limpiar_semanas_antiguas(self, semana_actual):
        """Limpia automáticamente los campos de horario, sector y planta de la semana anterior en modymoi."""
        try:
            conn = _obtener_conexion_local()
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE modymoi 
                SET Horario = '', Sector = '', Planta = '' 
                WHERE semana != ? AND semana IS NOT NULL AND semana != ''
                """,
                (str(semana_actual),)
            )
            conn.commit()
        except Exception as e:
            print(f"Error al limpiar semanas antiguas: {e}")
        finally:
            try:
                cursor.close()
                conn.close()
            except Exception:
                pass

    def eliminar_ot(self, id_ot):
        try:
            conn = _obtener_conexion_local()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM modymoi WHERE ID = ?", (id_ot,))
            conn.commit()
        except Exception as e:
            raise Exception(f"No se pudo eliminar la OT: {e}")
        finally:
            try:
                cursor.close()
                conn.close()
            except Exception:
                pass

    def contar_mano_de_obra(self, es_finde=False, semana_actual=None):
        """Cuenta únicamente los registros MOD y MOI de la semana activa."""
        try:
            conn = _obtener_conexion_local()
            cursor = conn.cursor()

            if not semana_actual:
                semana_actual = str(self.obtener_numero_semana_personalizado())

            if es_finde:
                query = """
                    SELECT m.calificacion_mano_obra 
                    FROM modymoi_finde f
                    INNER JOIN modymoi m ON f.id_operario = m.id
                    WHERE f.semana = ?
                """
                cursor.execute(query, (str(semana_actual),))
            else:
                query = "SELECT calificacion_mano_obra FROM modymoi WHERE semana = ?"
                cursor.execute(query, (str(semana_actual),))

            valores = cursor.fetchall()

            mod_count = sum(1 for v in valores if v[0] and v[0].strip().upper() == "MOD")
            moi_count = sum(1 for v in valores if v[0] and v[0].strip().upper() == "MOI")

            return mod_count, moi_count
        except Exception as e:
            raise Exception(f"No se pudo contar la mano de obra: {e}")
        finally:
            try:
                cursor.close()
                conn.close()
            except Exception:
                pass
