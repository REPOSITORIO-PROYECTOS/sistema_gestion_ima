# C:\Users\ticia\SISTEMAS\sistema_gestion_ima\back\utils\setup_sheets.py

import gspread
from google.oauth2.service_account import Credentials
import time
import os
import sys
import traceback # Para imprimir tracebacks más detallados en caso de error

try:
    # Importar las NUEVAS constantes de config.py
    from back.config import (
        GOOGLE_SHEET_ID as CONFIG_GOOGLE_SHEET_ID,
        GOOGLE_SERVICE_ACCOUNT_FILE as CONFIG_SERVICE_ACCOUNT_FILE,

        SHEET_NAME_TERCEROS,
        SHEET_NAME_DOC_VENTA_CABECERA, SHEET_NAME_DOC_VENTA_DETALLE, SHEET_NAME_DOC_VENTA_PAGOS,
        SHEET_NAME_DOC_COMPRA_DETALLE, SHEET_NAME_DOC_COMPRA_DETALLE,
        SHEET_NAME_ARTICULOS, SHEET_NAME_STOCK_CONFIG_LISTAS,
        SHEET_NAME_CAJA_SESIONES, SHEET_NAME_CAJA_MOVIMIENTOS, SHEET_NAME_STOCK_MOVIMIENTOS,
        SHEET_NAME_CONTABILIDAD_PLAN_CONFIG, SHEET_NAME_CONTABILIDAD_ASIENTOS,
        SHEET_NAME_ADMIN_TOKEN, SHEET_NAME_USUARIOS, SHEET_NAME_CONFIG_HORARIOS_CAJA
    )
    from utils.sheets_google_handler import GoogleSheetsHandler
    print("Módulos 'config' y 'utils.sheets_google_handler' importados con nuevas constantes de hoja.")

except ImportError as e:
    print(f"Error crítico importando módulos: {e}")
    traceback.print_exc()
    print("\nVerifica:")
    print("1. Que 'config.py' esté en la carpeta 'back/' y defina TODAS las constantes de hoja listadas arriba.")
    print("2. Que 'sheets_google_handler.py' esté en 'back/utils/'.")
    print("3. Que hayas creado 'back/__init__.py' y 'back/utils/__init__.py'.")
    print("4. Que estés ejecutando desde 'C:\\Users\\ticia\\SISTEMAS\\sistema_gestion_ima\\back>' con: python -m utils.setup_sheets")
    sys.exit(1)

# Lista de las NUEVAS constantes de nombres de hojas que quieres configurar
# (Esta lista ahora contiene los VALORES string de los nombres de hoja,
# ya que las variables se evalúan a sus strings cuando se añaden a la lista)
SHEET_NAME_CONSTANTS_TO_SETUP = [
    SHEET_NAME_TERCEROS,
    SHEET_NAME_DOC_VENTA_CABECERA, SHEET_NAME_DOC_VENTA_DETALLE, SHEET_NAME_DOC_VENTA_PAGOS,
    SHEET_NAME_DOC_COMPRA_DETALLE, SHEET_NAME_DOC_COMPRA_DETALLE,
    SHEET_NAME_ARTICULOS, SHEET_NAME_STOCK_CONFIG_LISTAS,
    SHEET_NAME_CAJA_SESIONES, SHEET_NAME_CAJA_MOVIMIENTOS, SHEET_NAME_STOCK_MOVIMIENTOS,
    SHEET_NAME_CONTABILIDAD_PLAN_CONFIG, SHEET_NAME_CONTABILIDAD_ASIENTOS,
    SHEET_NAME_ADMIN_TOKEN, SHEET_NAME_USUARIOS, SHEET_NAME_CONFIG_HORARIOS_CAJA
]

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file']

def _create_or_update_sheet(spreadsheet_obj, g_handler_instance, sheet_name_actual_string):
    headers = g_handler_instance.get_default_headers(sheet_name_actual_string)
    if not headers:
        print(f"  ADVERTENCIA: No se encontraron cabeceras para '{sheet_name_actual_string}'. Saltando.")
        return False
    
    worksheet = None
    try:
        worksheet = spreadsheet_obj.worksheet(sheet_name_actual_string)
        print(f"  Hoja '{sheet_name_actual_string}' existe. Limpiando...")
        worksheet.clear()
        
        if worksheet.row_count < 2:
             worksheet.resize(rows=2) # Redimensiona a 2 filas si tiene menos.
        # Si clear() eliminó todas las columnas, también podríamos necesitar reajustarlas:
        if worksheet.col_count < len(headers):
            worksheet.resize(cols=len(headers) + 2) # +2 por si acaso

    except gspread.exceptions.WorksheetNotFound:
        print(f"  Creando hoja '{sheet_name_actual_string}'...")
        # Al crear, asegurar que tenga al menos 2 filas y suficientes columnas.
        worksheet = spreadsheet_obj.add_worksheet(title=sheet_name_actual_string, rows="2", cols=len(headers) + 2) # +2 columnas por si acaso
    
    if not worksheet: # Si por alguna razón worksheet sigue siendo None
        print(f"  ERROR: No se pudo obtener o crear la referencia a la hoja '{sheet_name_actual_string}'.")
        return False

    try:
        # Usar argumentos nombrados para worksheet.update para evitar DeprecationWarning
        worksheet.update(values=[headers], range_name='A1', value_input_option='USER_ENTERED')
        
        
        # Una verificación final antes de congelar:
        if worksheet.row_count < 2:
            print(f"  Añadiendo fila explícitamente antes de congelar para '{sheet_name_actual_string}' (filas: {worksheet.row_count}).")
            worksheet.add_rows(1)

        worksheet.freeze(rows=1)
        print(f"  Cabeceras establecidas y fila congelada para '{sheet_name_actual_string}'.")
        return True
    except Exception as e:
        print(f"  ERROR estableciendo cabeceras o congelando para '{sheet_name_actual_string}': {e}")
        traceback.print_exc()
        return False

def main():
    print("--- Iniciando Configuración de Estructura de Google Sheets (AGLOMERADA) ---")
    target_google_sheet_id = CONFIG_GOOGLE_SHEET_ID
    target_service_account_file = CONFIG_SERVICE_ACCOUNT_FILE

    if not target_google_sheet_id:
        print("Error Crítico: GOOGLE_SHEET_ID no está definido en config.py.")
        sys.exit(1)
    if not target_service_account_file:
        print("Error Crítico: GOOGLE_SERVICE_ACCOUNT_FILE no está definido en config.py.")
        sys.exit(1)
    if not os.path.exists(target_service_account_file):
        print(f"Error Crítico: El archivo de credenciales '{target_service_account_file}' no se encontró.")
        sys.exit(1)

    print(f"Usando Spreadsheet ID: {target_google_sheet_id}")
    print(f"Usando credenciales: {target_service_account_file}")

    if not SHEET_NAME_CONSTANTS_TO_SETUP:
        print("Advertencia: No hay hojas definidas en 'SHEET_NAME_CONSTANTS_TO_SETUP' para procesar. Saliendo.")
        sys.exit(0)
    
    print(f"\nSe intentarán crear/actualizar las siguientes hojas (nombres según config.py):")
    for sheet_name_value in SHEET_NAME_CONSTANTS_TO_SETUP:
        print(f" - Nombre de hoja: \"{sheet_name_value}\"")

    confirm = input("\nPresiona Enter para continuar, o 'n' para cancelar: ")
    if confirm.lower() == 'n':
        print("Operación cancelada por el usuario."); sys.exit(0)

    try:
        creds = Credentials.from_service_account_file(target_service_account_file, scopes=SCOPES)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(target_google_sheet_id) # Usar open_by_key
        print(f"\nConectado a Spreadsheet: '{spreadsheet.title}'")
    except Exception as e:
        print(f"\nError fatal conectando a Google Sheets: {e}")
        traceback.print_exc()
        sys.exit(1)

    g_handler = GoogleSheetsHandler(sheet_id=target_google_sheet_id)
    print("\nProcesando hojas:")
    processed_count, failed_count = 0, 0

    for sheet_name_value in SHEET_NAME_CONSTANTS_TO_SETUP:
        if not sheet_name_value: # Debería ser un string no vacío
            print(f"  ERROR: Valor de hoja inválido (vacío o None). Saltando.");
            failed_count +=1;
            continue
        
        print(f"Procesando hoja: '{sheet_name_value}'...")
        if _create_or_update_sheet(spreadsheet, g_handler, sheet_name_value):
            processed_count += 1
        else:
            failed_count +=1
        time.sleep(1.5) # Pausa para no saturar la API

    print("\n--- Proceso de creación/actualización de hojas completado. ---")
    print(f"Hojas procesadas exitosamente: {processed_count}")
    print(f"Hojas con fallos o advertencias: {failed_count}")
    print("Por favor, revisa tu Google Spreadsheet y los mensajes de consola.")

if __name__ == '__main__':
    main()