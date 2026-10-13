import conexion


def _obtener_conexion():
    return conexion.obtener_conexion()


def obtener_tipos_horarios():
    conn = _obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, tipo, horarios_definidos
            FROM tipohorario
            ORDER BY id ASC
        """)
        filas = cursor.fetchall()

        # Convertimos RealDictCursor a lista de listas para la tabla web
        datos = []
        for f in filas:
            if isinstance(f, dict):
                datos.append([
                    f.get("id"),
                    f.get("tipo"),
                    f.get("horarios_definidos")
                ])
            else:
                datos.append(list(f))
        return datos
    except Exception as e:
        if hasattr(conn, 'rollback'):
            conn.rollback()
        print(f"Error al obtener tipos de horarios: {e}")
        return []
    finally:
        conn.close()


def obtener_tipo_horario_por_id(tipo_id):
    conn = _obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, tipo, horarios_definidos
            FROM tipohorario
            WHERE id = %s
        """, (tipo_id,))
        fila = cursor.fetchone()
        if not fila:
            return None

        if isinstance(fila, dict):
            return {
                "id": fila.get("id"),
                "tipo": fila.get("tipo"),
                "horarios_definidos": fila.get("horarios_definidos")
            }

        return {
            "id": fila[0],
            "tipo": fila[1],
            "horarios_definidos": fila[2]
        }
    except Exception as e:
        if hasattr(conn, 'rollback'):
            conn.rollback()
        print(f"Error al obtener tipo de horario {tipo_id}: {e}")
        return None
    finally:
        conn.close()


def insertar_tipo_horario(datos):
    conn = _obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO tipohorario (tipo, horarios_definidos)
            VALUES (%s, %s)
        """, (datos.get("tipo"), datos.get("horarios_definidos")))
        conn.commit()
    except Exception as e:
        if hasattr(conn, 'rollback'):
            conn.rollback()
        print(f"Error al insertar tipo de horario: {e}")
        raise e
    finally:
        conn.close()


def modificar_tipo_horario(tipo_id, datos):
    conn = _obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE tipohorario
            SET tipo = %s, horarios_definidos = %s
            WHERE id = %s
        """, (datos.get("tipo"), datos.get("horarios_definidos"), tipo_id))
        conn.commit()
    except Exception as e:
        if hasattr(conn, 'rollback'):
            conn.rollback()
        print(f"Error al modificar tipo de horario {tipo_id}: {e}")
        raise e
    finally:
        conn.close()


def eliminar_tipo_horario(tipo_id):
    conn = _obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM tipohorario WHERE id = %s", (tipo_id,))
        conn.commit()
    except Exception as e:
        if hasattr(conn, 'rollback'):
            conn.rollback()
        print(f"Error al eliminar tipo de horario {tipo_id}: {e}")
        raise e
    finally:
        conn.close()
