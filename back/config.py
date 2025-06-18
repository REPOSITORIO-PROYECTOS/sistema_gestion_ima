# C:\Users\ticia\SISTEMAS\sistema_gestion_ima\back\config.py

import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    load_dotenv()

# --- CONFIGURACIÓN DE GOOGLE SHEETS ---
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'credentials.json')

# --- NOMBRES DE HOJAS DE CÁLCULO (ESTRUCTURA AGLOMERADA) ---

# 1. TERCEROS (Clientes y Proveedores)
SHEET_NAME_TERCEROS = os.getenv('SHEET_NAME_TERCEROS', "Terceros")

# 2. DOCUMENTOS DE VENTA
SHEET_NAME_DOC_VENTA_CABECERA = os.getenv('SHEET_NAME_DOC_VENTA_CABECERA', "Documentos_Venta_Cabecera")
SHEET_NAME_DOC_VENTA_DETALLE = os.getenv('SHEET_NAME_DOC_VENTA_DETALLE', "Documentos_Venta_Detalle")
SHEET_NAME_DOC_VENTA_PAGOS = os.getenv('SHEET_NAME_DOC_VENTA_PAGOS', "Documentos_Venta_Pagos")

# 3. DOCUMENTOS DE COMPRA
SHEET_NAME_DOC_COMPRA_DETALLE = os.getenv('SHEET_NAME_DOC_COMPRA_DETALLE', "Documentos_Compra_Cabecera")
SHEET_NAME_DOC_COMPRA_DETALLE = os.getenv('SHEET_NAME_DOC_COMPRA_DETALLE', "Documentos_Compra_Detalle")

# 4. ARTÍCULOS Y CONFIGURACIÓN DE STOCK
SHEET_NAME_ARTICULOS = os.getenv('SHEET_NAME_ARTICULOS', "Articulos")
SHEET_NAME_STOCK_CONFIG_LISTAS = os.getenv('SHEET_NAME_STOCK_CONFIG_LISTAS', "Stock_Config_Listas") # Para Categorías, Marcas, etc.

# 5. CAJA Y MOVIMIENTOS DE STOCK (Se mantienen similares)
SHEET_NAME_CAJA_SESIONES = os.getenv('SHEET_NAME_CAJA_SESIONES', "Sesiones_Caja") # Antes SHEET_NAME_CAJA_SESIONES 
SHEET_NAME_CAJA_MOVIMIENTOS = os.getenv('SHEET_NAME_CAJA_MOVIMIENTOS', "Movimientos_Caja") # Antes SHEET_NAME_CAJA_MOVIMIENTOS
SHEET_NAME_STOCK_MOVIMIENTOS = os.getenv('SHEET_NAME_STOCK_MOVIMIENTOS', "Movimientos_Stock")

# 6. CONTABILIDAD (Simplificada)
SHEET_NAME_CONTABILIDAD_PLAN_CONFIG = os.getenv('SHEET_NAME_CONTABILIDAD_PLAN_CONFIG', "Contabilidad_PlanCuentas_Y_Config")
SHEET_NAME_CONTABILIDAD_ASIENTOS = os.getenv('SHEET_NAME_CONTABILIDAD_ASIENTOS', "Contabilidad_Asientos_Resumidos")

# 7. CONFIGURACIÓN Y USUARIOS (Se mantienen)
SHEET_NAME_ADMIN_TOKEN = os.getenv('SHEET_NAME_ADMIN_TOKEN', 'AdminToken')
SHEET_NAME_USUARIOS = os.getenv('SHEET_NAME_USUARIOS', 'Usuarios')
SHEET_NAME_CONFIG_HORARIOS_CAJA = os.getenv('SHEET_NAME_CONFIG_HORARIOS_CAJA', 'ConfigHorariosCaja')

# --- VALIDACIÓN DE CONFIGURACIONES ESENCIALES ---
if not GOOGLE_SHEET_ID:
    raise ValueError("GOOGLE_SHEET_ID no está configurado.")
if not GOOGLE_SERVICE_ACCOUNT_FILE:
    raise ValueError("GOOGLE_SERVICE_ACCOUNT_FILE no está configurado.")
elif not os.path.isabs(GOOGLE_SERVICE_ACCOUNT_FILE):
    possible_path = os.path.join(os.path.dirname(__file__), GOOGLE_SERVICE_ACCOUNT_FILE)
    if os.path.exists(possible_path):
        GOOGLE_SERVICE_ACCOUNT_FILE = possible_path
if not os.path.exists(GOOGLE_SERVICE_ACCOUNT_FILE):
    raise FileNotFoundError(f"Archivo de credenciales '{GOOGLE_SERVICE_ACCOUNT_FILE}' no encontrado.")

print(f"Config (config.py): Spreadsheet ID: {GOOGLE_SHEET_ID}")
print(f"Config (config.py): Credentials File: {GOOGLE_SERVICE_ACCOUNT_FILE}")

# --- OTRAS CONFIGURACIONES ---
ADMIN_TOKEN_DURATION_SECONDS = int(os.getenv('ADMIN_TOKEN_DURATION_SECONDS', 8 * 60 * 60))

# Variables que tu test_general_flujos.py podría estar usando y que ahora tienen nuevos nombres:
# Mapeo para compatibilidad con los tests originales, si es necesario ajustarlos luego.
# O mejor, ajustar los tests para usar las nuevas constantes.
# Por ahora, el setup_sheets.py usará las nuevas constantes directamente.
# SHEET_NAME_CAJA_SESIONES  = SHEET_NAME_CAJA_SESIONES
# SHEET_NAME_CAJA_MOVIMIENTOS = SHEET_NAME_CAJA_MOVIMIENTOS
# SHEET_NAME_TERCEROS -> ahora parte de SHEET_NAME_TERCEROS
# SHEET_NAME_DOC_COMPRA_DETALLE -> ahora parte de SHEET_NAME_DOC_COMPRA_DETALLE
# SHEET_NAME_DOC_COMPRA_DETALLE -> ahora parte de SHEET_NAME_DOC_COMPRA_DETALLE
# SHEET_NAME_ARTICULOS -> se mantiene SHEET_NAME_ARTICULOS