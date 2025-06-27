# back/config.py
import os
from dotenv import load_dotenv, find_dotenv

# --- Carga de .env ---
print("--- Cargando config.py (Versión Estructura Base Estable) ---")
dotenv_path = find_dotenv(usecwd=True, raise_error_if_not_found=False)
if dotenv_path and os.path.exists(dotenv_path):
    print(f"DEBUG_CFG: Cargando .env desde: '{dotenv_path}'")
    load_dotenv(dotenv_path=dotenv_path, override=True)
else:
    print("DEBUG_CFG: No se encontró .env o la ruta no existe, usando defaults o variables de sistema.")
    load_dotenv(override=True) # Intentar cargar de todas formas
# --- Fin Carga .env ---

# --- SEGURIDAD-----
SECRET_KEY_SEC= os.getenv('SECRET_KEY_SEGURIDAD')

# --- Variables de Conexión ---
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', "credencial_IA.json") # Default simple

# --- Nombres de Variables Python para las Hojas ---
# Leemos de .env usando las claves (SHEET_NAME_ENV_...)
# Si la clave no está en .env, se usa el valor string default que es el nombre deseado de la hoja.

# Configuración y Administración
CONFIGURACION_GLOBAL_SHEET = os.getenv('SHEET_NAME_CONFIGURACION_GLOBAL', 'ConfiguracionGlobal')
USUARIOS_SHEET = os.getenv('SHEET_NAME_USUARIOS', 'Usuarios')
# ADMIN_TOKEN_SHEET ahora se manejaría dentro de CONFIGURACION_GLOBAL_SHEET o USUARIOS_SHEET
# Si aún quieres una hoja separada para tokens (no recomendado con ConfiguracionGlobal),
# deberías añadir SHEET_NAME_ENV_ADMIN_TOKEN a tu .env y luego:
# ADMIN_TOKEN_SHEET = os.getenv('SHEET_NAME_ENV_ADMIN_TOKEN', 'AdminTokens_Default')

# Terceros (Clientes y Proveedores)
TERCEROS_SHEET = os.getenv('SHEET_NAME_TERCEROS', 'Terceros')

# Artículos y Stock
ARTICULOS_SHEET = os.getenv('SHEET_NAME_ARTICULOS', 'Articulos')
STOCK_MOVIMIENTOS_SHEET = os.getenv('SHEET_NAME_STOCK_MOVIMIENTOS', 'StockMovimientos')
# Si necesitas listas de configuración de stock (categorías, marcas, etc.)
# STOCK_LISTAS_CONFIG_SHEET = os.getenv('SHEET_NAME_ENV_STOCK_LISTAS_CONFIG', 'StockConfigListas')

# Caja
CAJA_SESIONES_SHEET = os.getenv('SHEET_NAME_CAJA_SESIONES', 'CajaSesiones')
CAJA_MOVIMIENTOS_SHEET = os.getenv('SHEET_NAME_CAJA_MOVIMIENTOS', 'CajaMovimientos')

# Compras
COMPRAS_CABECERA_SHEET = os.getenv('SHEET_NAME_COMPRAS_CABECERA', 'Compras')
COMPRAS_DETALLE_SHEET = os.getenv('SHEET_NAME_COMPRAS_DETALLE', 'ComprasDetalle')

# Ventas (si decides tener hojas separadas y no integrar en CajaMovimientos)
# VENTAS_CABECERA_SHEET = os.getenv('SHEET_NAME_VENTAS_CABECERA', 'Ventas')
# VENTAS_DETALLE_SHEET = os.getenv('SHEET_NAME_VENTAS_DETALLE', 'VentasDetalle')
# VENTAS_PAGOS_SHEET = os.getenv('SHEET_NAME_VENTAS_PAGOS', 'VentasPagos')

# Contabilidad (si la implementas)
# CONTABILIDAD_PLAN_SHEET = os.getenv('SHEET_NAME_CONTABILIDAD_PLAN', 'ContabilidadPlanCuentas')
# CONTABILIDAD_ASIENTOS_SHEET = os.getenv('SHEET_NAME_CONTABILIDAD_ASIENTOS', 'ContabilidadAsientos')


# Otras configuraciones
ADMIN_TOKEN_DURATION_SECONDS = int(os.getenv('ADMIN_TOKEN_DURATION_SECONDS', 8 * 60 * 60))

# --- Verificaciones Críticas ---
if not GOOGLE_SHEET_ID:
    raise ValueError("CRÍTICO: GOOGLE_SHEET_ID no está configurado en .env.")
if not GOOGLE_SERVICE_ACCOUNT_FILE:
     raise ValueError("CRÍTICO: GOOGLE_SERVICE_ACCOUNT_FILE no está configurado en .env.")
if not os.path.exists(GOOGLE_SERVICE_ACCOUNT_FILE):
    raise FileNotFoundError(
        f"CRÍTICO: Archivo de credenciales '{GOOGLE_SERVICE_ACCOUNT_FILE}' (definido por GOOGLE_SERVICE_ACCOUNT_FILE) no encontrado. "
        f"Verifica el valor en tu .env y la existencia del archivo en el servidor."
    )
print(f"DEBUG_CFG: Configuración cargada. Usando GOOGLE_SERVICE_ACCOUNT_FILE='{GOOGLE_SERVICE_ACCOUNT_FILE}'")
print(f"DEBUG_CFG: Hoja de Sesiones de Caja se llamará: '{CAJA_SESIONES_SHEET}'") # Ejemplo de verificación