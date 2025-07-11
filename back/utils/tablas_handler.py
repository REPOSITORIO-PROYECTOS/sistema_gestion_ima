import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Any, Optional, Tuple

# Importar las VARIABLES PYTHON definidas en config.py
from back.config import (
    GOOGLE_SHEET_ID, GOOGLE_SERVICE_ACCOUNT_FILE,
    CONFIGURACION_GLOBAL_SHEET, USUARIOS_SHEET, TERCEROS_SHEET, ARTICULOS_SHEET,
    CAJA_SESIONES_SHEET, CAJA_MOVIMIENTOS_SHEET, STOCK_MOVIMIENTOS_SHEET,
    COMPRAS_CABECERA_SHEET, COMPRAS_DETALLE_SHEET,
    # Descomenta estas si las defines en config.py y .env para hojas de venta separadas
    # VENTAS_CABECERA_SHEET, VENTAS_DETALLE_SHEET, VENTAS_PAGOS_SHEET,
    # Descomenta estas si las defines y usas:
    # ADMIN_TOKEN_SHEET, # Aunque ahora podría ir en CONFIGURACION_GLOBAL_SHEET
    # STOCK_LISTAS_CONFIG_SHEET,
    # CONTABILIDAD_PLAN_SHEET, CONTABILIDAD_ASIENTOS_SHEET,
)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file']


datos_clientes: List[Dict] = []

class TablasHandler:
    def __init__(self):
        self.client = self._init_client()

    def _init_client(self) -> Optional[gspread.Client]:
        global gspread_client
        if gspread_client is None:
            print("Inicializando cliente gspread...")
            try:
                gspread_client = gspread.service_account(filename=GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES)
                print("Cliente gspread inicializado.")
            except FileNotFoundError:
                print(f"ERROR FATAL: Archivo de credenciales no encontrado en '{GOOGLE_SERVICE_ACCOUNT_FILE}'")
                gspread_client = None
            except Exception as e:
                print(f"ERROR FATAL: No se pudo inicializar el cliente gspread: {e}")
                gspread_client = None
        return gspread_client
    

    def cargar_clientes(self):
        print("Intentando cargar/recargar datos de Clientes...")
        if self.client:
            try:
                sheet = self.client.open_by_key(GOOGLE_SHEET_ID)
                worksheet = sheet.worksheet("clientes")
                datos_clientes = worksheet.get_all_records()
                return datos_clientes
            except gspread.exceptions.WorksheetNotFound:
                print("ERROR: Hoja 'clientes' no encontrada.")
            except Exception as e:
                print(f"Error al cargar datos de Clientes: {e}")
        else:
            print("Cliente no disponible.")
        return []
