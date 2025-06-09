# utils/sheets_google_handler.py

import gspread
from google.oauth2.service_account import Credentials
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Alcances necesarios para las APIs de Google Sheets y Drive
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

# Nombre del archivo JSON de credenciales (espera que esté en la raíz del proyecto o define la ruta)
# Lo leeremos desde una variable de entorno
SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'credentials.json')

# ID de tu Google Spreadsheet (se obtiene de la URL del sheet)
# Ejemplo: https://docs.google.com/spreadsheets/d/ESTE_ES_EL_ID/edit
# Lo leeremos desde una variable de entorno
SPREADSHEET_ID = os.getenv('GOOGLE_SHEET_ID')

class GoogleSheetsHandler:
    def __init__(self, spreadsheet_id=None, creds_file=None):
        self.spreadsheet_id = spreadsheet_id or SPREADSHEET_ID
        self.creds_file = creds_file or SERVICE_ACCOUNT_FILE
        self.creds = None
        self.client = None
        self.sheet = None

        if not self.spreadsheet_id:
            raise ValueError("Spreadsheet ID not provided or found in .env (GOOGLE_SHEET_ID)")
        if not os.path.exists(self.creds_file):
            raise FileNotFoundError(
                f"Credentials file '{self.creds_file}' not found. "
                "Ensure it's in the correct path or GOOGLE_SERVICE_ACCOUNT_FILE is set in .env"
            )

        self._connect()

    def _connect(self):
        """Establece la conexión con Google Sheets."""
        try:
            self.creds = Credentials.from_service_account_file(
                self.creds_file, scopes=SCOPES
            )
            self.client = gspread.authorize(self.creds)
            self.sheet = self.client.open_by_key(self.spreadsheet_id)
            print(f"Conectado exitosamente a la hoja de cálculo: {self.sheet.title}")
        except Exception as e:
            print(f"Error al conectar con Google Sheets: {e}")
            # Podrías querer relanzar la excepción o manejarla de forma más específica
            raise

    def get_worksheet(self, worksheet_name):
        """Obtiene una hoja de trabajo específica por su nombre."""
        try:
            return self.sheet.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            print(f"Hoja de trabajo '{worksheet_name}' no encontrada.")
            return None
        except Exception as e:
            print(f"Error al obtener la hoja de trabajo '{worksheet_name}': {e}")
            return None

    def get_all_records(self, worksheet_name):
        """Obtiene todos los registros de una hoja de trabajo como una lista de diccionarios."""
        ws = self.get_worksheet(worksheet_name)
        if ws:
            return ws.get_all_records() # Asume que la primera fila son encabezados
        return []

    def append_row(self, worksheet_name, data_row):
        """Añade una fila de datos a una hoja de trabajo."""
        ws = self.get_worksheet(worksheet_name)
        if ws:
            try:
                ws.append_row(data_row)
                print(f"Fila añadida a '{worksheet_name}': {data_row}")
                return True
            except Exception as e:
                print(f"Error al añadir fila a '{worksheet_name}': {e}")
                return False
        return False

    def find_row(self, worksheet_name, column_index, value_to_find):
        """Encuentra la primera fila que contiene un valor específico en una columna dada."""
        ws = self.get_worksheet(worksheet_name)
        if ws:
            try:
                cell = ws.find(value_to_find, in_column=column_index)
                if cell:
                    return ws.row_values(cell.row)
            except gspread.exceptions.CellNotFound:
                print(f"Valor '{value_to_find}' no encontrado en la columna {column_index} de '{worksheet_name}'.")
            except Exception as e:
                print(f"Error al buscar en '{worksheet_name}': {e}")
        return None

    def update_cell(self, worksheet_name, row, col, value):
        """Actualiza el valor de una celda específica."""
        ws = self.get_worksheet(worksheet_name)
        if ws:
            try:
                ws.update_cell(row, col, value)
                print(f"Celda ({row}, {col}) en '{worksheet_name}' actualizada a '{value}'.")
                return True
            except Exception as e:
                print(f"Error al actualizar celda en '{worksheet_name}': {e}")
                return False
        return False