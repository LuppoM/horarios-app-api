import json
import psycopg2.extras
from conexion import obtener_conexion

PERMISOS_POR_DEFECTO = ["HORARIOS", "CONSOLIDADO"]


def _extraer_id(fila):
    """Extrae el ID sin importar si el cursor devuelve dict (RealDictCursor) o tuple."""
    if fila is None:
        return None
    if isinstance(fila, dict):
        return fila.get("id")
    return fila[0]


def _parsear_permisos(valor_permisos):
    """Convierte el campo permisos de BD (JSON text o lista) a una lista limpia de strings."""
    if isinstance(valor_permisos, list):
        return [str(p).strip().upper() for p in valor_permisos if str(p).strip()]
    if not valor_permisos:
        return list(PERMISOS_POR_DEFECTO)
    try:
        parsed = json.loads(valor_permisos)
        if isinstance(parsed, list):
            return [str(p).strip().upper() for p in parsed if str(p).strip()]
    except Exception:
        pass
    return [p.strip().upper() for p in str(valor_permisos).split(",") if p.strip()]


def listar_usuarios():
    sql = """
        SELECT id, usuario, area, requiere_contrasena, contrasena, permisos
        FROM usuarios
        ORDER BY id ASC
    """
    with obtener_conexion() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            filas = cur.fetchall()

    resultado = []
    for fila in filas:
        item = dict(fila)
        item["permisos"] = _parsear_permisos(item.get("permisos"))
        resultado.append(item)
    return resultado


def existe_usuario(usuario: str, excluir_id: int = None) -> bool:
    usuario_limpio = (usuario or "").strip().lower()
    if excluir_id is not None:
        sql = "SELECT 1 AS existe FROM usuarios WHERE LOWER(TRIM(usuario)) = %s AND id <> %s LIMIT 1"
        params = (usuario_limpio, excluir_id)
    else:
        sql = "SELECT 1 AS existe FROM usuarios WHERE LOWER(TRIM(usuario)) = %s LIMIT 1"
        params = (usuario_limpio,)

    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone() is not None


def crear_usuario(
    usuario: str,
    area: str,
    requiere_contrasena: bool,
    contrasena: str = None,
    permisos: list = None,
) -> int:
    user_limpio = (usuario or "").strip()
    area_limpia = (area or "").strip().upper()
    clave_final = (contrasena or "").strip() if requiere_contrasena else None
    permisos_json = json.dumps(_parsear_permisos(permisos))

    if not user_limpio or not area_limpia:
        raise ValueError("El usuario y el área son obligatorios.")
    if requiere_contrasena and not clave_final:
        raise ValueError("Debés ingresar una contraseña si está marcada como obligatoria.")
    if existe_usuario(user_limpio):
        raise ValueError(f"El usuario '{user_limpio}' ya existe.")

    sql = """
        INSERT INTO usuarios (usuario, area, requiere_contrasena, contrasena, permisos)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """
    with obtener_conexion() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (user_limpio, area_limpia, requiere_contrasena, clave_final, permisos_json))
                nuevo_id = _extraer_id(cur.fetchone())
            conn.commit()
            return nuevo_id
        except Exception:
            conn.rollback()
            raise


def editar_usuario(
    user_id: int,
    usuario: str,
    area: str,
    requiere_contrasena: bool,
    contrasena: str = None,
    permisos: list = None,
) -> bool:
    user_limpio = (usuario or "").strip()
    area_limpia = (area or "").strip().upper()
    clave_limpia = (contrasena or "").strip()
    permisos_json = json.dumps(_parsear_permisos(permisos))

    if not user_limpio or not area_limpia:
        raise ValueError("El usuario y el área son obligatorios.")
    if existe_usuario(user_limpio, excluir_id=user_id):
        raise ValueError(f"El usuario '{user_limpio}' ya está en uso.")

    with obtener_conexion() as conn:
        try:
            with conn.cursor() as cur:
                if not requiere_contrasena:
                    sql = """
                        UPDATE usuarios
                        SET usuario = %s, area = %s, requiere_contrasena = FALSE, contrasena = NULL, permisos = %s
                        WHERE id = %s
                    """
                    cur.execute(sql, (user_limpio, area_limpia, permisos_json, user_id))
                elif clave_limpia:
                    sql = """
                        UPDATE usuarios
                        SET usuario = %s, area = %s, requiere_contrasena = TRUE, contrasena = %s, permisos = %s
                        WHERE id = %s
                    """
                    cur.execute(sql, (user_limpio, area_limpia, clave_limpia, permisos_json, user_id))
                else:
                    sql = """
                        UPDATE usuarios
                        SET usuario = %s, area = %s, requiere_contrasena = TRUE, permisos = %s
                        WHERE id = %s
                    """
                    cur.execute(sql, (user_limpio, area_limpia, permisos_json, user_id))

                filas = cur.rowcount
            conn.commit()
            return filas > 0
        except Exception:
            conn.rollback()
            raise


def eliminar_usuario(user_id: int) -> bool:
    sql = "DELETE FROM usuarios WHERE id = %s"
    with obtener_conexion() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id,))
                filas = cur.rowcount
            conn.commit()
            return filas > 0
        except Exception:
            conn.rollback()
            raise