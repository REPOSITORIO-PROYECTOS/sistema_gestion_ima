# /home/sgi_user/proyectos/sistema_gestion_ima/back/utils/tablas_handler.py

import os
import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Optional

from back.config import GOOGLE_SERVICE_ACCOUNT_FILE

# LA LÍNEA QUE CAUSABA EL ERROR HA SIDO ELIMINADA.
# AHORA EL MOTOR PUEDE ARRANCAR SIN PROBLEMAS.

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file']
gspread_client: Optional[gspread.Client] = None

class TablasHandler:
    def __init__(self):
        self.client = self._init_client()

    def _init_client(self) -> Optional[gspread.Client]:
        # Tu inicialización del cliente está perfecta, no se cambia.
        global gspread_client
        if gspread_client is None:
            print("Inicializando cliente gspread...")
            try:
                back_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                credential_path = os.path.join(back_dir, GOOGLE_SERVICE_ACCOUNT_FILE)
                gspread_client = gspread.service_account(filename=credential_path, scopes=SCOPES)
                print("Cliente gspread inicializado.")
            except Exception as e:
                print(f"ERROR FATAL: No se pudo inicializar el cliente gspread: {e}")
                gspread_client = None
        return gspread_client
    
    # MANTENEMOS TU FUNCIÓN, PERO AHORA ES MÁS SEGURA
    # PORQUE REQUIERE QUE LE DIGAN A QUÉ HOJA CONECTARSE.
    def cargar_clientes(self, google_sheet_id: str) -> List[Dict]:
        print(f"Cargando datos de Clientes desde el sheet: {google_sheet_id}")
        if not self.client: return []
        try:
            sheet = self.client.open_by_key(google_sheet_id)
            worksheet = sheet.worksheet("clientes")
            return worksheet.get_all_records()
        except Exception as e:
            print(f"❌ Error al cargar clientes de GSheet: {e}")
            return []

    # MANTENEMOS TU FUNCIÓN, PERO AHORA ES MÁS SEGURA.
    def cargar_articulos(self, google_sheet_id: str) -> List[Dict]:
        print(f"Cargando datos de Artículos desde el sheet: {google_sheet_id}")
        if not self.client: return []
        try:
            sheet = self.client.open_by_key(google_sheet_id)
            worksheet = sheet.worksheet("stock")
            return worksheet.get_all_records()
        except Exception as e:
            print(f"❌ Error al cargar artículos de GSheet: {e}")
            return []