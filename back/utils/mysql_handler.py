import mysql.connector
from mysql.connector import Error

# ¡Importamos nuestra configuración centralizada!
from back.config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME

def get_db_connection():
    """Crea y devuelve una conexión a la base de datos usando la configuración central."""
    try:
        # Ahora los datos de conexión se leen desde config.py
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"Error CRÍTICO al conectar a MySQL: {e}")
        # En una aplicación real, aquí podrías registrar el error en un log.
        return None