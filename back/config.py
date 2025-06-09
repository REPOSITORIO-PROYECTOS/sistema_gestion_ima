# config.py
import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'credentials.json')

# Nombres de hojas de cálculo
SHEET_NAME_CAJA_APERTURAS = os.getenv('SHEET_NAME_CAJA_APERTURAS', 'CajaAperturasCierres')
SHEET_NAME_CAJA_REGISTROS = os.getenv('SHEET_NAME_CAJA_REGISTROS', 'CajaRegistros')
SHEET_NAME_USUARIOS = os.getenv('SHEET_NAME_USUARIOS', 'Usuarios') # Para registrar usuarios
SHEET_NAME_CONFIG_HORARIOS = os.getenv('SHEET_NAME_CONFIG_HORARIOS', 'ConfigHorariosCaja') # Para horarios
SHEET_NAME_ADMIN_TOKEN = os.getenv('SHEET_NAME_ADMIN_TOKEN', 'AdminToken') # Para el token de admin

# Hojas para el módulo de Compras
SHEET_NAME_PROVEEDORES = os.getenv('SHEET_NAME_PROVEEDORES', 'Proveedores')
SHEET_NAME_ORDENES_COMPRA = os.getenv('SHEET_NAME_ORDENES_COMPRA', 'OrdenesDeCompra')
SHEET_NAME_ITEMS_OC = os.getenv('SHEET_NAME_ITEMS_OC', 'ItemsOrdenDeCompra')

# Hoja para Artículos (del módulo Stock, pero necesaria aquí)
SHEET_NAME_ARTICULOS = os.getenv('SHEET_NAME_ARTICULOS', 'ArticulosStock')

# Archivos locales (opcional, podríamos usar Sheets para todo)
CURRENT_USER_FILE = "current_user_session.json" # Para guardar el usuario activo en la PC
ADMIN_TOKEN_LOCAL_FILE = "admin_token_data.json" # Para guardar el token admin localmente

# Palabras clave para el token de administrador
ADMIN_TOKEN_KEYWORDS = ["SOLAR", "LUNAR", "FUEGO", "AGUA", "VIENTO", "TIERRA", "RAYO"]

# Duración del token de administrador en segundos (8 horas)
ADMIN_TOKEN_DURATION_SECONDS = 8 * 60 * 60
# ADMIN_TOKEN_DURATION_SECONDS = 60 # Para pruebas rápidas (1 minuto)


if not GOOGLE_SHEET_ID:
    raise ValueError("La variable de entorno GOOGLE_SHEET_ID no está configurada en .env")
if not GOOGLE_SERVICE_ACCOUNT_FILE or not os.path.exists(GOOGLE_SERVICE_ACCOUNT_FILE):
    raise FileNotFoundError(
        f"El archivo de credenciales '{GOOGLE_SERVICE_ACCOUNT_FILE}' no se encontró. "
        f"Verifica la variable GOOGLE_SERVICE_ACCOUNT_FILE en .env y la existencia del archivo."
    )