import os
import sys
import pymysql
import pymysql.cursors

def obtener_conexion():
    # Conexión local a XAMPP (MySQL)
    # Por defecto XAMPP usa usuario 'root' sin contraseña y la base de datos la llamaremos 'horarios_db'
    return pymysql.connect(
        host='localhost',
        user='root',
        password='',
        database='horarios_db',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor # Para mantener diccionarios igual que antes
    )

def obtener_ruta_icono(nombre_icono="icono.ico"):
    if getattr(sys, "frozen", False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, nombre_icono)