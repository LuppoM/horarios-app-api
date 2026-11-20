import psycopg2.extras
from conexion import obtener_conexion


def listar_usuarios():
    sql = """
        SELECT id, usuario, area, requiere_contrasena, contrasena
        FROM usuarios
        ORDER BY id ASC
    """
    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(fila) for fila in cur.fetchall()]


def existe_usuario(usuario: str, excluir_id: int = None) -> bool:
    usuario_limpio = (usuario or "").strip().lower()
    if excluir_id is not None:
        sql = "SELECT 1 FROM usuarios WHERE LOWER(TRIM(usuario)) = %s AND id <> %s LIMIT 1"
        params = (usuario_limpio, excluir_id)
    else:
        sql = "SELECT 1 FROM usuarios WHERE LOWER(TRIM(usuario)) = %s LIMIT 1"
        params = (usuario_limpio,)

    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone() is not None


def crear_usuario(usuario: str, area: str, requiere_contrasena: bool, contrasena: str = None) -> int:
    user_limpio = (usuario or "").strip()
    area_limpia = (area or "").strip().upper()
    clave_final = (contrasena or "").strip() if requiere_contrasena else None

    if not user_limpio or not area_limpia:
        raise ValueError("El usuario y el área son obligatorios.")
    if requiere_contrasena and not clave_final:
        raise ValueError("Debés ingresar una contraseña si está marcada como obligatoria.")
    if existe_usuario(user_limpio):
        raise ValueError(f"El usuario '{user_limpio}' ya existe.")

    sql = """
        INSERT INTO usuarios (usuario, area, requiere_contrasena, contrasena)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_limpio, area_limpia, requiere_contrasena, clave_final))
            nuevo_id = cur.fetchone()[0]
        conn.commit()
    return nuevo_id


def editar_usuario(user_id: int, usuario: str, area: str, requiere_contrasena: bool, contrasena: str = None) -> bool:
    user_limpio = (usuario or "").strip()
    area_limpia = (area or "").strip().upper()
    clave_limpia = (contrasena or "").strip()

    if not user_limpio or not area_limpia:
        raise ValueError("El usuario y el área son obligatorios.")
    if existe_usuario(user_limpio, excluir_id=user_id):
        raise ValueError(f"El usuario '{user_limpio}' ya está en uso.")

    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            if not requiere_contrasena:
                sql = """
                    UPDATE usuarios
                    SET usuario = %s, area = %s, requiere_contrasena = FALSE, contrasena = NULL
                    WHERE id = %s
                """
                cur.execute(sql, (user_limpio, area_limpia, user_id))
            elif clave_limpia:
                sql = """
                    UPDATE usuarios
                    SET usuario = %s, area = %s, requiere_contrasena = TRUE, contrasena = %s
                    WHERE id = %s
                """
                cur.execute(sql, (user_limpio, area_limpia, clave_limpia, user_id))
            else:
                sql = """
                    UPDATE usuarios
                    SET usuario = %s, area = %s, requiere_contrasena = TRUE
                    WHERE id = %s
                """
                cur.execute(sql, (user_limpio, area_limpia, user_id))

            filas = cur.rowcount
        conn.commit()
    return filas > 0


def eliminar_usuario(user_id: int) -> bool:
    sql = "DELETE FROM usuarios WHERE id = %s"
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            filas = cur.rowcount
        conn.commit()
    return filas > 0