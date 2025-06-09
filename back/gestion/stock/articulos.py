# gestion/stock/__init__.py
# (Archivo vacío)

# gestion/stock/articulos.py
from utils.sheets_google_handler import GoogleSheetsHandler
from config import SHEET_NAME_ARTICULOS # Necesitarás definir esta hoja y su estructura

# g_handler = GoogleSheetsHandler() # Podría instanciarse aquí

# ---- SIMULACIÓN INICIAL ----
ARTICULOS_SIMULADOS_DB = {
    "PROD001": {"ID_Articulo": "PROD001", "Descripcion": "Coca Cola 600ml", "StockActual": 50, "CostoUltimo": 0.80, "PrecioVenta": 1.50},
    "PROD002": {"ID_Articulo": "PROD002", "Descripcion": "Galletas Oreo", "StockActual": 100, "CostoUltimo": 0.40, "PrecioVenta": 0.80},
    "MATPRIMA01": {"ID_Articulo": "MATPRIMA01", "Descripcion": "Harina 000 1kg", "StockActual": 20, "CostoUltimo": 0.50, "PrecioVenta": None}, # Materia prima
}

def obtener_articulo_por_id_simulado(id_articulo: str):
    """Función simulada para obtener datos de un artículo."""
    print(f"[STOCK_ARTICULOS_SIMULADO] Buscando artículo: {id_articulo}")
    return ARTICULOS_SIMULADOS_DB.get(id_articulo)

# --- FIN SIMULACIÓN ---


def obtener_articulo_por_id(id_articulo: str):
    """
    Obtiene un artículo específico por su ID desde Google Sheets.
    (Implementación real cuando desarrollemos este módulo)
    """
    # try:
    #     g_handler = GoogleSheetsHandler()
    #     ws = g_handler.get_worksheet(SHEET_NAME_ARTICULOS)
    #     if ws:
    #         # Asumiendo que ID_Articulo es la primera columna y la hoja tiene encabezados
    #         # Esto es ineficiente para búsquedas frecuentes. Considerar cargar todo en memoria o mejor indexación.
    #         records = ws.get_all_records()
    #         for record in records:
    #             if record.get('ID_Articulo') == id_articulo:
    #                 return record # Devuelve el diccionario del artículo
    #         return None # No encontrado
    # except Exception as e:
    #     print(f"Error obteniendo artículo {id_articulo}: {e}")
    #     return None
    print(f"ADVERTENCIA: Usando obtener_articulo_por_id_simulado para {id_articulo}")
    return obtener_articulo_por_id_simulado(id_articulo) # Temporalmente usar la simulación

