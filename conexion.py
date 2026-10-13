import os
import sys
import psycopg2
import psycopg2.extras

def obtener_conexion():
    # Conexión remota a PostgreSQL en Supabase sin corchetes en la contraseña
    DATABASE_URL = "postgresql://postgres.uczrwceswzarysptefra:palmesano2024@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
    
    conexion = psycopg2.connect(
        DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor # Mantiene los resultados como diccionarios igual que antes
    )
    return conexion

def obtener_ruta_icono(nombre_icono="icono.ico"):
    if getattr(sys, "frozen", False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, nombre_icono)
