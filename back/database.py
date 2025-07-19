# database.py
import os
from sqlmodel import create_engine, Session
from dotenv import load_dotenv  # <--- 1. Importa la función

# --- 0. CARGAR LAS VARIABLES DE ENTORNO DESDE EL ARCHIVO .env ---
# Esta línea busca un archivo .env en el directorio actual o en directorios superiores
# y carga las variables que contiene para que os.getenv() pueda encontrarlas.
load_dotenv() # <--- 2. Llama a la función

# --- 1. CONFIGURACIÓN DE LA BASE DE DATOS ---
# Ahora os.getenv() leerá las variables de tu archivo .env
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "3306") # '3306' es un valor por defecto si no lo defines en .env
DB_NAME = os.getenv("DB_NAME")

# Añadimos una comprobación para asegurarnos de que las variables se cargaron
if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_NAME]):
    raise ValueError("Faltan variables de entorno para la base de datos. Asegúrate de que el archivo .env esté configurado correctamente.")

# --- 2. CREACIÓN DE LA CADENA DE CONEXIÓN (DATABASE_URL) ---
DATABASE_URL = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# --- 3. CREACIÓN DEL ENGINE ---
engine = create_engine(DATABASE_URL, echo=True)

# --- 4. FUNCIÓN GENERADORA DE SESIONES (get_db) ---
def obtener_sesion():
    with Session(engine) as session:
        try:
            yield session
        finally:
            session.close()

# --- 5. FUNCIÓN PARA CREAR LAS TABLAS ---
def create_db_and_tables():
    from sqlmodel import SQLModel
    
    # Importa tus modelos aquí para que SQLModel los conozca
    # from . import models 

    print("Creando tablas en la base de datos...")
    SQLModel.metadata.create_all(engine)
    print("Tablas creadas exitosamente.")