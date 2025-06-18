# gestion/caja/modifica_stock_caja.py

from datetime import datetime
from utils.sheets_google_handler import GoogleSheetsHandler
from config import SHEET_NAME_ARTICULOS, SHEET_NAME_STOCK_MOVIMIENTOS

def actualizar_stock_por_venta(id_sesion_caja: int, items_vendidos: list, usuario: str):
    print(f"[MODIFICA_STOCK_CAJA] Iniciando actualización de stock por venta (Sesión: {id_sesion_caja}, Usuario: {usuario})")

    if not items_vendidos:
        print("  - No hay items para actualizar en stock.")
        return {"status": "warning", "message": "No hay items para actualizar en stock."}

    try:
        g_handler = GoogleSheetsHandler()
        if not g_handler.client:
            print("  - Error: No se pudo conectar a Google Sheets para modificar stock.")
            return {"status": "error", "message": "No se pudo conectar a Google Sheets para modificar stock."}

        now = datetime.now()
        timestamp_mov = now.isoformat()
        
        items_procesados_correctamente = 0
        items_con_error = 0
        errores_detalle = []

        for item in items_vendidos:
            id_articulo = item.get('id_articulo')
            cantidad_vendida_str = item.get('cantidad') # Asumo que tu test usa 'cantidad'
            nombre_articulo = item.get('nombre', str(id_articulo))

            if id_articulo is None or cantidad_vendida_str is None:
                print(f"  - Item inválido (datos faltantes), saltando: {item}")
                errores_detalle.append(f"Item {nombre_articulo} con datos faltantes.")
                items_con_error += 1
                continue
            
            try:
                cantidad_vendida = float(cantidad_vendida_str)
                if cantidad_vendida <= 0:
                    raise ValueError("Cantidad debe ser positiva.")
            except ValueError:
                print(f"  - Cantidad vendida inválida para artículo {nombre_articulo} (ID: {id_articulo}): '{cantidad_vendida_str}'. Saltando.")
                errores_detalle.append(f"Item {nombre_articulo} con cantidad inválida '{cantidad_vendida_str}'.")
                items_con_error += 1
                continue

            print(f"  - Procesando Artículo: {nombre_articulo} (ID: {id_articulo}), Cantidad a disminuir: {cantidad_vendida}")

            # 1. Obtener artículo y stock actual de la hoja SHEET_NAME_ARTICULOS
            articulo_data, row_index_articulo = g_handler.get_row_by_id(SHEET_NAME_ARTICULOS, id_articulo, "ID_Articulo")

            if not articulo_data:
                print(f"    - ADVERTENCIA: Artículo {nombre_articulo} (ID: {id_articulo}) no encontrado en '{SHEET_NAME_ARTICULOS}'. No se actualiza stock.")
                errores_detalle.append(f"Artículo {nombre_articulo} (ID: {id_articulo}) no encontrado.")
                items_con_error += 1
                continue
            
            try:
                stock_actual = float(articulo_data.get("StockActual", "0"))
            except ValueError:
                print(f"    - ERROR: Stock actual para {nombre_articulo} (ID: {id_articulo}) no es un número válido ('{articulo_data.get('StockActual')}'). No se actualiza stock.")
                errores_detalle.append(f"Stock actual inválido para {nombre_articulo} (ID: {id_articulo}).")
                items_con_error += 1
                continue

            stock_anterior = stock_actual
            stock_nuevo = stock_anterior - cantidad_vendida
            
            # (Opcional: Validar si el stock se vuelve negativo y qué hacer en ese caso)
            if stock_nuevo < 0:
                 print(f"    - ADVERTENCIA: Stock para {nombre_articulo} (ID: {id_articulo}) quedaría negativo ({stock_nuevo}). Se registrará, pero revisar.")
                 errores_detalle.append(f"Stock negativo para {nombre_articulo} (ID: {id_articulo}).")


            # 2. Actualizar stock en la hoja SHEET_NAME_ARTICULOS
            col_index_stock_actual = g_handler._get_column_index(SHEET_NAME_ARTICULOS, "StockActual")
            if row_index_articulo != -1 and col_index_stock_actual is not None:
                if g_handler.update_cell(SHEET_NAME_ARTICULOS, row_index_articulo, col_index_stock_actual, stock_nuevo):
                    print(f"    - Stock de {nombre_articulo} (ID: {id_articulo}) actualizado en '{SHEET_NAME_ARTICULOS}' a: {stock_nuevo}")
                else:
                    print(f"    - ERROR: No se pudo actualizar el stock de {nombre_articulo} (ID: {id_articulo}) en '{SHEET_NAME_ARTICULOS}'.")
                    errores_detalle.append(f"Fallo al actualizar stock de {nombre_articulo} (ID: {id_articulo}) en hoja Articulos.")
                    items_con_error += 1
                    # Continuar para registrar el movimiento de todas formas, o decidir abortar. Por ahora, continuamos.
            else:
                print(f"    - ERROR: No se pudo encontrar la fila o columna 'StockActual' para {nombre_articulo} (ID: {id_articulo}) en '{SHEET_NAME_ARTICULOS}'.")
                errores_detalle.append(f"Fallo al ubicar celda de stock para {nombre_articulo} (ID: {id_articulo}).")
                items_con_error += 1
                continue # Si no podemos actualizar el stock, no registramos el movimiento para evitar inconsistencias graves

            # 3. Registrar movimiento en SHEET_NAME_STOCK_MOVIMIENTOS
            id_movimiento_stock = f"VTA-{id_sesion_caja}-{str(id_articulo).replace(' ', '')}-{int(now.timestamp())%10000}"
            descripcion_articulo_mov = articulo_data.get("DescripcionPrincipal", nombre_articulo) # Usar descripción de la hoja si existe

            movimiento_data = [
                id_movimiento_stock,
                timestamp_mov,
                id_articulo,
                descripcion_articulo_mov,
                "SALIDA_POR_VENTA",
                -cantidad_vendida, # Cantidad negativa para salidas
                stock_anterior,
                stock_nuevo,
                str(id_sesion_caja), # ID de referencia (puede ser ID de venta si lo tuvieras)
                usuario,
                f"Venta desde caja sesión {id_sesion_caja}" # Notas
            ]
            
            # Asegurar que las cabeceras existan en Movimientos_Stock si la hoja es nueva
            ws_mov_stock = g_handler.get_worksheet(SHEET_NAME_STOCK_MOVIMIENTOS)
            if ws_mov_stock and ws_mov_stock.row_count == 0: # Si está completamente vacía
                headers_mov_stock = g_handler.get_default_headers(SHEET_NAME_STOCK_MOVIMIENTOS)
                if headers_mov_stock:
                    ws_mov_stock.append_row(headers_mov_stock)

            if g_handler.append_row(SHEET_NAME_STOCK_MOVIMIENTOS, movimiento_data):
                print(f"    - Movimiento de stock para {nombre_articulo} (ID: {id_articulo}) registrado en '{SHEET_NAME_STOCK_MOVIMIENTOS}'.")
                items_procesados_correctamente += 1
            else:
                print(f"    - ERROR: No se pudo registrar el movimiento de stock para {nombre_articulo} (ID: {id_articulo}) en '{SHEET_NAME_STOCK_MOVIMIENTOS}'.")
                errores_detalle.append(f"Fallo al registrar movimiento para {nombre_articulo} (ID: {id_articulo}).")
                items_con_error += 1
                # Considerar revertir la actualización de stock en Articulos si esto falla (más complejo)

        if items_con_error > 0:
            return {
                "status": "partial_error",
                "message": f"Actualización de stock procesada con {items_con_error} errores de {len(items_vendidos)} items.",
                "items_ok": items_procesados_correctamente,
                "items_failed": items_con_error,
                "details": errores_detalle
            }
        
        print(f"[MODIFICA_STOCK_CAJA] Actualización de stock completada exitosamente para {items_procesados_correctamente} items.")
        return {"status": "success", "message": f"Stock actualizado para {items_procesados_correctamente} items."}

    except Exception as e:
        print(f"  - Error general crítico en actualizar_stock_por_venta: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": f"Error general procesando actualización de stock: {str(e)}"}