import conexion


def _obtener_conexion():
    return conexion.obtener_conexion()


def _normalizar_requiere_dotacion(valor, defecto=1) -> int:
    if valor is None:
        return defecto
    return 1 if str(valor).strip().lower() in ["1", "true", "si", "on"] else 0


def obtener_sectores():
    conn = _obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, nombre_sector, planta, tipo_horario, requiere_dotacion
            FROM sectores
            ORDER BY id ASC
        """)
        filas = cursor.fetchall()
        
        datos = []
        for f in filas:
            if isinstance(f, dict):
                datos.append([
                    f.get("id"),
                    f.get("nombre_sector"),
                    f.get("planta"),
                    f.get("tipo_horario"),
                    f.get("requiere_dotacion")
                ])
            else:
                datos.append(list(f))
        return datos
    except Exception as e:
        if hasattr(conn, 'rollback'):
            conn.rollback()
        print(f"Error al obtener sectores: {e}")
        return []
    finally:
        try: cursor.close()
        except Exception: pass
        conn.close()


def obtener_sector_por_id(sector_id):
    conn = _obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, nombre_sector, planta, tipo_horario, requiere_dotacion
            FROM sectores
            WHERE id = %s
        """, (sector_id,))
        fila = cursor.fetchone()
        if not fila:
            return None

        if isinstance(fila, dict):
            return {
                "id": fila.get("id"),
                "nombre_sector": fila.get("nombre_sector"),
                "planta": fila.get("planta"),
                "tipo_horario": fila.get("tipo_horario"),
                "requiere_dotacion": fila.get("requiere_dotacion")
            }
        return {
            "id": fila[0],
            "nombre_sector": fila[1],
            "planta": fila[2],
            "tipo_horario": fila[3],
            "requiere_dotacion": fila[4]
        }
    except Exception as e:
        if hasattr(conn, 'rollback'):
            conn.rollback()
        print(f"Error al obtener sector {sector_id}: {e}")
        return None
    finally:
        try: cursor.close()
        except Exception: pass
        conn.close()


def obtener_tipos_horario():
    conn = _obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT tipo FROM tipohorario ORDER BY tipo ASC")
        filas = cursor.fetchall()

        tipos = []
        for f in filas:
            if isinstance(f, dict):
                tipos.append(f.get("tipo"))
            else:
                tipos.append(f[0])
        return tipos if tipos else ["ROTATIVO", "CENTRAL"]
    except Exception as e:
        if hasattr(conn, 'rollback'):
            conn.rollback()
        print(f"Error al obtener tipos de horario: {e}")
        return ["ROTATIVO", "CENTRAL"]
    finally:
        try: cursor.close()
        except Exception: pass
        conn.close()


def insertar_sector(datos):
    conn = _obtener_conexion()
    cursor = conn.cursor()
    try:
        requiere_dotacion = _normalizar_requiere_dotacion(datos.get("requiere_dotacion"), defecto=1)

        # Previene 'duplicate key violates unique constraint sectores_pkey'
        cursor.execute("""
            SELECT setval(
                pg_get_serial_sequence('sectores', 'id'), 
                COALESCE((SELECT MAX(id) FROM sectores), 1)
            );
        """)

        cursor.execute("""
            INSERT INTO sectores (nombre_sector, planta, tipo_horario, requiere_dotacion)
            VALUES (%s, %s, %s, %s)
        """, (datos.get("nombre_sector"), datos.get("planta"), datos.get("tipo_horario"), requiere_dotacion))
        
        conn.commit()
    except Exception as e:
        if hasattr(conn, 'rollback'):
            conn.rollback()
        print(f"Error al insertar sector: {e}")
        raise e
    finally:
        try: cursor.close()
        except Exception: pass
        conn.close()


def modificar_sector(sector_id, datos):
    conn = _obtener_conexion()
    cursor = conn.cursor()
    try:
        nombre_sector = datos.get("nombre_sector") or datos.get("nombre")
        planta = datos.get("planta")
        tipo_horario = datos.get("tipo_horario")
        requiere_dotacion = _normalizar_requiere_dotacion(datos.get("requiere_dotacion"), defecto=1)

        cursor.execute("""
            UPDATE sectores
            SET nombre_sector = %s, planta = %s, tipo_horario = %s, requiere_dotacion = %s
            WHERE id = %s
        """, (nombre_sector, planta, tipo_horario, requiere_dotacion, sector_id))

        conn.commit()
        return True, "Modificación exitosa"
    except Exception as e:
        if hasattr(conn, 'rollback'):
            conn.rollback()
        print(f"Error al modificar sector {sector_id}: {e}")
        return False, str(e)
    finally:
        try: cursor.close()
        except Exception: pass
        conn.close()


def eliminar_sector(sector_id):
    conn = _obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM sectores WHERE id = %s", (sector_id,))
        conn.commit()
    except Exception as e:
        if hasattr(conn, 'rollback'):
            conn.rollback()
        print(f"Error al eliminar sector {sector_id}: {e}")
        raise e
    finally:
        try: cursor.close()
        except Exception: pass
        conn.close()
