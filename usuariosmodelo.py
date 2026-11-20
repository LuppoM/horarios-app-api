import psycopg2.extras
from conexion import obtener_conexion


def verificar_requiere_clave(usuario: str):
    """
    Devuelve si el usuario existe y si requiere contraseña.
    """
    usuario_limpio = (usuario or "").strip().lower()
    if not usuario_limpio:
        return None

    sql = """
        SELECT usuario, area, requiere_contrasena
        FROM usuarios
        WHERE LOWER(TRIM(usuario)) = %s
        LIMIT 1
    """

    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (usuario_limpio,))
            fila = cur.fetchone()

    if not fila:
        return None

    return {
        "usuario": fila["usuario"],
        "area": fila["area"],
        "requiere_contrasena": bool(fila["requiere_contrasena"]),
    }


def validar_usuario(usuario: str, clave: str = ""):
    """
    Busca el usuario en la tabla usuarios.
    Si requiere_contrasena es False, entra directo sin validar clave.
    Si requiere_contrasena es True, valida contra la columna contrasena.
    """
    usuario_limpio = (usuario or "").strip().lower()
    clave_limpia = (clave or "").strip()

    if not usuario_limpio:
        return None

    sql = """
        SELECT id, usuario, area, requiere_contrasena, contrasena
        FROM usuarios
        WHERE LOWER(TRIM(usuario)) = %s
        LIMIT 1
    """

    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (usuario_limpio,))
            fila = cur.fetchone()

    if not fila:
        return None

    requiere = bool(fila.get("requiere_contrasena", False))

    if requiere:
        clave_bd = (fila.get("contrasena") or "").strip()
        if not clave_limpia or clave_bd != clave_limpia:
            return None

    return {
        "id": fila["id"],
        "usuario": fila["usuario"],
        "area": fila["area"],
        "requiere_contrasena": requiere,
    }