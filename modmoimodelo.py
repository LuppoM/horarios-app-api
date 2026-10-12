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
    # Ignoramos o mantenemos el argumento opcional para no romper llamadas legacy
    self._modelo_principal = modeloprincipal()

  def obtener_numero_semana_personalizado(self, fecha=None):
    return self._modelo_principal.obtener_numero_semana_personalizado(fecha)

  def obtener_datos(self, filtro_columna=None, filtro_valor=None):
    """Obtiene únicamente las columnas y filas correspondientes a la Semana."""
    try:
      conn = _obtener_conexion_local()
      cursor = conn.cursor()
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
            """
      if filtro_columna and filtro_valor:
        consulta = (
            f"{query_base} WHERE [{filtro_columna}] LIKE ? ORDER BY operario"
            " ASC"
        )
        cursor.execute(consulta, ("%" + filtro_valor + "%",))
      else:
        consulta = f"{query_base} ORDER BY operario ASC"
        cursor.execute(consulta)

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

  def obtener_datos_finde(self, filtro_columna=None, filtro_valor=None):
    """Obtiene únicamente las columnas y filas correspondientes al Fin de Semana."""
    try:
      conn = _obtener_conexion_local()
      cursor = conn.cursor()
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
            """
      if filtro_columna and filtro_valor:
        col_prefix = (
            f"f.[{filtro_columna}]"
            if filtro_columna
            in ["semana", "dia", "horario", "sector", "planta"]
            else f"m.[{filtro_columna}]"
        )
        consulta = (
            f"{query_base} WHERE {col_prefix} LIKE ? ORDER BY m.operario ASC,"
            " f.dia ASC"
        )
        cursor.execute(consulta, ("%" + filtro_valor + "%",))
      else:
        consulta = f"{query_base} ORDER BY m.operario ASC, f.dia ASC"
        cursor.execute(consulta)

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

  def contar_mano_de_obra(self, es_finde=False):
    """Cuenta únicamente los registros MOD y MOI de la tabla activa."""
    try:
      conn = _obtener_conexion_local()
      cursor = conn.cursor()

      if es_finde:
        query = """
                    SELECT m.calificacion_mano_obra 
                    FROM modymoi_finde f
                    INNER JOIN modymoi m ON f.id_operario = m.id
                """
      else:
        query = "SELECT calificacion_mano_obra FROM modymoi"

      cursor.execute(query)
      valores = cursor.fetchall()

      mod_count = sum(
          1 for v in valores if v[0] and v[0].strip().upper() == "MOD"
      )
      moi_count = sum(
          1 for v in valores if v[0] and v[0].strip().upper() == "MOI"
      )

      return mod_count, moi_count
    except Exception as e:
      raise Exception(f"No se pudo contar la mano de obra: {e}")
    finally:
      try:
        cursor.close()
        conn.close()
      except Exception:
        pass