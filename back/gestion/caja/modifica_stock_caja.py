# gestion/caja/modifica_stock_caja.py
# Este módulo interactuará con el módulo de STOCK más adelante.
# Por ahora, solo simulará la acción o registrará la intención.

from utils.sheets_google_handler import GoogleSheetsHandler
# from config import SHEET_NAME_STOCK_MOVIMIENTOS # Suponiendo una hoja para esto
from datetime import datetime

# g_handler = GoogleSheetsHandler()

def actualizar_stock_por_venta(id_sesion_caja: int, items_vendidos: list, usuario: str):
    """
    Esta función será llamada después de una venta para disminuir el stock.
    items_vendidos: lista de dicts [{'id_articulo': X, 'cantidad_vendida': Y}, ...]

    Por ahora, esta función es un placeholder. Eventualmente, interactuará
    con el módulo de Stock para actualizar las cantidades reales.
    Podría registrar el movimiento de stock en una hoja separada "MovimientosStock".
    """
    print(f"[MODIFICA_STOCK_CAJA] Solicitud para actualizar stock por venta (Sesión: {id_sesion_caja}, Usuario: {usuario}):")
    if not items_vendidos:
        return {"status": "warning", "message": "No hay items para actualizar en stock."}
    # try:
    #     g_handler = GoogleSheetsHandler() # Asegurar conexión
    #     if not g_handler.client:
    #         return {"status": "error", "message": "No se pudo conectar a Google Sheets para modificar stock."}

    #     now = datetime.now()
    #     fecha = now.strftime("%Y-%m-%d")
    #     hora = now.strftime("%H:%M:%S")

    #     for item in items_vendidos:
    #         id_articulo = item.get('id_articulo')
    #         cantidad = item.get('cantidad_vendida')
    #         if id_articulo is None or cantidad is None:
    #             print(f"  - Item inválido, saltando: {item}")
    #             continue

    #         print(f"  - Artículo ID: {id_articulo}, Cantidad a disminuir: {cantidad}")
            # Aquí iría la lógica para:
            # 1. Encontrar el artículo en la hoja de Stock.
            # 2. Leer su stock actual.
            # 3. Restar la cantidad vendida.
            # 4. Actualizar la celda del stock del artículo.
            # 5. (Opcional pero recomendado) Registrar este movimiento en una hoja "MovimientosStock"
            #    Columnas: ID_Mov, Fecha, Hora, Tipo (VENTA), ID_Articulo, Cantidad_Modificada (-X), Stock_Resultante, ID_Transaccion_Origen (ej. id_sesion_caja o id_venta), Usuario

            # Ejemplo de registro en "MovimientosStock" (requiere SHEET_NAME_STOCK_MOVIMIENTOS en config)
            # movimiento_data = [
            #     int(now.timestamp() * 1000 + int(id_articulo)), # ID Movimiento único
            #     fecha, hora, "SALIDA_POR_VENTA", id_articulo, -cantidad,
            #     f"Sesión {id_sesion_caja}", usuario
            # ]
            # g_handler.append_row(SHEET_NAME_STOCK_MOVIMIENTOS, movimiento_data)

        # Por ahora, solo mensaje de éxito simulado
        # return {"status": "success", "message": "Intento de modificación de stock registrado (simulado)."}
    # except Exception as e:
    #     print(f"Error en actualizar_stock_por_venta (simulado): {e}")
    #     return {"status": "error", "message": f"Error simulando actualización de stock: {str(e)}"}
    