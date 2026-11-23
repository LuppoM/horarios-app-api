import json
import psycopg2.extras
from conexion import obtener_conexion


def _parsear_permisos(valor_permisos):
    """Convierte el campo permisos de BD (JSON text o lista) a una lista limpia de strings."""
    if isinstance(valor_permisos, list):
        return [str(p).strip().upper() for p in valor_permisos if str(p).strip()]
    if not valor_permisos:
        return ["HORARIOS", "CONSOLIDADO"]
    try:
        parsed = json.loads(valor_permisos)
        if isinstance(parsed, list):
            return [str(p).strip().upper() for p in parsed if str(p).strip()]
    except Exception:
        pass
    return [p.strip().upper() for p in str(valor_permisos).split(",") if p.strip()]


def listar_usuarios_login():
    """
    Devuelve la lista de usuarios disponibles para poblar el combobox del login
    junto con su área y si requieren contraseña (sin exponer claves).
    """
    sql = """
        SELECT usuario, area, requiere_contrasena
        FROM usuarios
        ORDER BY usuario ASC
    """
    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            filas = cur.fetchall()

    return [
        {
            "usuario": f["usuario"],
            "area": f["area"],
            "requiere_contrasena": bool(f["requiere_contrasena"]),
        }
        for f in filas
    ]


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
        SELECT id, usuario, area, requiere_contrasena, contrasena, permisos
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
        "permisos": _parsear_permisos(fila.get("permisos")),
    }