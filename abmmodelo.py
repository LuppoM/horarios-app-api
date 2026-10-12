import os
import sqlite3
import sys
import traceback
from typing import Any, Dict


def _obtener_conexion_local():
  if getattr(sys, "frozen", False):
    base_path = os.path.dirname(sys.executable)
  else:
    base_path = os.path.dirname(os.path.abspath(__file__))

  db_path = os.path.join(base_path, "HORARIOS.db")
  return sqlite3.connect(db_path, check_same_thread=False)


class abmmodmoimodelo:

  def __init__(self, conexion=None):
    pass

  def obtener_por_id(self, id_registro: int) -> Dict[str, Any]:
    try:
      conn = _obtener_conexion_local()
      cursor = conn.cursor()
      cursor.execute(
          """
                SELECT id, calificacion_mano_obra, operario, horario, semana, sector, planta 
                FROM modymoi WHERE id = ?
            """,
          (id_registro,),
      )
      row = cursor.fetchone()
      if not row:
        return None
      cols = [column[0] for column in cursor.description]
      return dict(zip(cols, row))
    finally:
      conn.close()

  def insertar(self, datos: Dict[str, Any]) -> None:
    try:
      if not datos:
        raise ValueError("No se proporcionaron datos para insertar.")

      campos = ", ".join(f"[{k}]" for k in datos.keys())
      placeholders = ", ".join(["?"] * len(datos))
      valores = list(datos.values())

      query = f"INSERT INTO modymoi ({campos}) VALUES ({placeholders})"
      conn = _obtener_conexion_local()
      cursor = conn.cursor()
      cursor.execute(query, valores)
      conn.commit()
      cursor.close()
      conn.close()
    except Exception as e:
      raise Exception(f"Error al insertar: {e}\n{traceback.format_exc()}")

  def modificar(self, id: int, datos: Dict[str, Any]) -> None:
    try:
      if not datos:
        raise ValueError("No se proporcionaron datos para modificar.")

      set_clause = ", ".join(f"[{k}] = ?" for k in datos.keys())
      valores = list(datos.values())
      valores.append(id)

      query = f"UPDATE modymoi SET {set_clause} WHERE id = ?"
      conn = _obtener_conexion_local()
      cursor = conn.cursor()
      cursor.execute(query, valores)
      conn.commit()
      cursor.close()
      conn.close()
    except Exception as e:
      raise Exception(f"Error al modificar: {e}\n{traceback.format_exc()}")

  def eliminar(self, id: int) -> None:
    try:
      conn = _obtener_conexion_local()
      cursor = conn.cursor()
      cursor.execute("DELETE FROM modymoi WHERE id = ?", (id,))
      conn.commit()
      cursor.close()
      conn.close()
    except Exception as e:
      raise Exception(f"Error al eliminar: {e}\n{traceback.format_exc()}")