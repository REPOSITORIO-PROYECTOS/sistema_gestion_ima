# gestion/compra/registro_compra.py
import gspread
from utils.sheets_google_handler import GoogleSheetsHandler
from config import SHEET_NAME_ORDENES_COMPRA, SHEET_NAME_ITEMS_OC, SHEET_NAME_PROVEEDORES, SHEET_NAME_ARTICULOS
from datetime import datetime
from . import proveedores_compra # Para obtener datos del proveedor
from gestion.stock import articulos as stock_articulos # Para obtener datos del artículo (necesitaremos crear este módulo)
from . import modifica_stock_compra # Para llamar al ingreso de stock


def generar_id_orden_compra(g_handler):
    """Genera un ID de Orden de Compra (ej. OC2023-001)."""
    registros = g_handler.get_all_records(SHEET_NAME_ORDENES_COMPRA)
    year_prefix = f"OC{datetime.now().year}-"
    
    max_num = 0
    if registros:
        for reg in registros:
            id_oc = reg.get("ID_OrdenCompra", "")
            if id_oc.startswith(year_prefix):
                try:
                    num = int(id_oc[len(year_prefix):])
                    if num > max_num:
                        max_num = num
                except ValueError:
                    continue
    return f"{year_prefix}{(max_num + 1):03d}"


def crear_orden_de_compra(id_proveedor: str, usuario_creador: str, items_oc: list, 
                          fecha_entrega_estimada: str = None, observaciones: str = ""):
    """
    Crea una nueva Orden de Compra.
    items_oc: lista de dicts [{'id_articulo': X, 'cantidad_pedida': Y, 'costo_estimado': Z}, ...]
    """
    try:
        g_handler = GoogleSheetsHandler()
        if not g_handler.client:
            return {"status": "error", "message": "No se pudo conectar a Google Sheets."}

        proveedor = proveedores_compra.obtener_proveedor_por_id(id_proveedor)
        if not proveedor:
            return {"status": "error", "message": f"Proveedor con ID {id_proveedor} no encontrado o inactivo."}
        if not items_oc:
            return {"status": "error", "message": "La orden de compra debe tener al menos un ítem."}

        id_orden_compra = generar_id_orden_compra(g_handler)
        fecha_creacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        total_estimado_oc = 0
        items_oc_para_guardar = []

        # Validar items y calcular total
        for i, item_data in enumerate(items_oc):
            id_articulo = item_data.get('id_articulo')
            cantidad = item_data.get('cantidad_pedida')
            costo_est = item_data.get('costo_estimado', 0.0)

            if not id_articulo or not isinstance(cantidad, (int, float)) or cantidad <= 0:
                return {"status": "error", "message": f"Ítem {i+1} inválido (ID artículo o cantidad)."}
            
            # Aquí deberíamos verificar que el id_articulo existe en nuestra hoja de ArticulosStock
            # articulo_info = stock_articulos.obtener_articulo_por_id(id_articulo) # Suponiendo que existe esta función
            # if not articulo_info:
            #     return {"status": "error", "message": f"Artículo con ID {id_articulo} no encontrado."}
            # descripcion_articulo = articulo_info.get('Descripcion', 'N/A')
            # ---- SIMULACIÓN POR AHORA ----
            articulo_info = stock_articulos.obtener_articulo_por_id_simulado(id_articulo) # Usamos simulado
            if not articulo_info:
                 return {"status": "error", "message": f"Artículo con ID {id_articulo} no encontrado (simulado)."}
            descripcion_articulo = articulo_info.get('Descripcion', 'Descripción Simulada')
            # ---- FIN SIMULACIÓN ----

            subtotal_item = cantidad * costo_est
            total_estimado_oc += subtotal_item

            items_oc_para_guardar.append({
                "ID_ItemOC": f"IOC-{id_orden_compra}-{i+1}",
                "ID_OrdenCompra": id_orden_compra,
                "ID_Articulo": id_articulo,
                "DescripcionArticulo": descripcion_articulo, # Idealmente del maestro de artículos
                "CantidadPedida": cantidad,
                "CostoUnitarioEstimado": costo_est,
                "SubtotalEstimado": subtotal_item,
                "CantidadRecibida": 0, # Inicialmente 0
                "CostoUnitarioReal": 0.0, # Se actualiza al recibir
                "FechaRecepcionItem": ""
            })
        
        # Guardar la Orden de Compra principal
        orden_data = [
            id_orden_compra,
            fecha_creacion,
            id_proveedor,
            proveedor.get("RazonSocial", "N/A"),
            fecha_entrega_estimada if fecha_entrega_estimada else "",
            "PENDIENTE", # Estado inicial
            usuario_creador,
            observaciones,
            total_estimado_oc
        ]
        # Columnas: ID_OrdenCompra, FechaCreacion, ID_Proveedor, NombreProveedor, FechaEntregaEstimada,
        #           Estado, UsuarioCreador, Observaciones, TotalEstimado
        if not g_handler.append_row(SHEET_NAME_ORDENES_COMPRA, orden_data):
            return {"status": "error", "message": "Error al guardar la cabecera de la Orden de Compra."}

        # Guardar los ítems de la Orden de Compra
        # gspread permite append_rows para múltiples filas
        rows_to_append_items = []
        for item_dict in items_oc_para_guardar:
            # Asegurar el orden de las columnas para la hoja SHEET_NAME_ITEMS_OC
            # ID_ItemOC, ID_OrdenCompra, ID_Articulo, DescripcionArticulo, CantidadPedida,
            # CostoUnitarioEstimado, SubtotalEstimado, CantidadRecibida, CostoUnitarioReal, FechaRecepcionItem
            row = [
                item_dict["ID_ItemOC"], item_dict["ID_OrdenCompra"], item_dict["ID_Articulo"],
                item_dict["DescripcionArticulo"], item_dict["CantidadPedida"],
                item_dict["CostoUnitarioEstimado"], item_dict["SubtotalEstimado"],
                item_dict["CantidadRecibida"], item_dict["CostoUnitarioReal"], item_dict["FechaRecepcionItem"]
            ]
            rows_to_append_items.append(row)
        
        # Usar batch append si gspread lo soporta bien o append_rows
        ws_items = g_handler.get_worksheet(SHEET_NAME_ITEMS_OC)
        if ws_items:
            ws_items.append_rows(rows_to_append_items, value_input_option='USER_ENTERED') # USER_ENTERED para que Google interprete tipos
            print(f"Orden de Compra {id_orden_compra} creada con {len(items_oc_para_guardar)} ítems.")
            return {"status": "success", "id_orden_compra": id_orden_compra, "message": "Orden de Compra creada exitosamente."}
        else:
            # Aquí podrías querer "deshacer" la inserción de la cabecera de la OC o marcarla como errónea.
            return {"status": "error", "message": f"Hoja '{SHEET_NAME_ITEMS_OC}' no encontrada. Ítems no guardados."}

    except Exception as e:
        print(f"Error en crear_orden_de_compra: {e}")
        return {"status": "error", "message": str(e)}


def registrar_recepcion_mercaderia(id_orden_compra: str, items_recibidos: list, usuario_receptor: str, 
                                   nro_remito: str = "", nro_factura_proveedor: str = "", fecha_recepcion: str = None):
    """
    Registra la recepción de mercadería para una Orden de Compra.
    Actualiza las cantidades recibidas y costos reales en ItemsOrdenDeCompra.
    Llama a modificar_stock_compra.ingresar_stock_por_compra.
    items_recibidos: lista de dicts [{'id_item_oc': X, 'cantidad_recibida': Y, 'costo_unitario_real': Z (opcional)}, ...]
                    o [{'id_articulo': A, 'cantidad_recibida': Y, ...}] si no se conoce el ID_ItemOC
    """
    try:
        g_handler = GoogleSheetsHandler()
        if not g_handler.client: return {"status": "error", "message": "No se pudo conectar a Google Sheets."}

        fecha_recep_str = fecha_recepcion if fecha_recepcion else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Obtener la OC y sus ítems
        ws_items_oc = g_handler.get_worksheet(SHEET_NAME_ITEMS_OC)
        if not ws_items_oc: return {"status": "error", "message": f"Hoja '{SHEET_NAME_ITEMS_OC}' no encontrada."}
        
        all_items_sheet = ws_items_oc.get_all_records()
        items_de_esta_oc = [item_row for item_row in all_items_sheet if item_row.get('ID_OrdenCompra') == id_orden_compra]

        if not items_de_esta_oc:
            return {"status": "error", "message": f"No se encontraron ítems para la OC {id_orden_compra}."}

        updates_batch_items = []
        items_para_actualizar_stock = []
        
        # Mapear ID_Articulo a fila para actualización si se recibe por ID_Articulo
        map_articulo_a_fila = {str(item.get('ID_Articulo')): i + 2 for i, item in enumerate(items_de_esta_oc)} # +2 por cabecera y base 1

        for item_rec in items_recibidos:
            id_item_oc = item_rec.get('id_item_oc')
            id_articulo_recibido = item_rec.get('id_articulo') # Alternativa si no viene id_item_oc
            cantidad_rec = item_rec.get('cantidad_recibida')
            costo_real = item_rec.get('costo_unitario_real') # Puede ser None si no se conoce aún

            if not isinstance(cantidad_rec, (int, float)) or cantidad_rec < 0:
                print(f"Advertencia: Cantidad recibida inválida para {id_item_oc or id_articulo_recibido}. Saltando.")
                continue
            
            target_row_index = None
            item_oc_original = None

            if id_item_oc:
                # Encontrar la fila del ID_ItemOC específico
                try:
                    cell = ws_items_oc.find(id_item_oc, in_column=1) # Asumiendo ID_ItemOC es col 1
                    if cell: target_row_index = cell.row
                    # Encontrar el item original para obtener id_articulo y cantidad pedida
                    item_oc_original = next((i for i in items_de_esta_oc if i.get('ID_ItemOC') == id_item_oc), None)
                except gspread.exceptions.CellNotFound:
                    print(f"Advertencia: ID_ItemOC '{id_item_oc}' no encontrado en la OC. Saltando.")
                    continue
            elif id_articulo_recibido:
                # Si se provee id_articulo, buscar la primera coincidencia en la OC que no esté totalmente recibida
                # Esto es más complejo si hay múltiples líneas del mismo artículo.
                # Por simplicidad, tomamos la primera que coincida y tenga pendiente.
                for i_original, item_orig_data in enumerate(items_de_esta_oc):
                    if str(item_orig_data.get('ID_Articulo')) == str(id_articulo_recibido):
                        cant_pedida = float(item_orig_data.get('CantidadPedida', 0))
                        cant_ya_recibida = float(item_orig_data.get('CantidadRecibida', 0))
                        if cant_ya_recibida < cant_pedida : # Si hay pendiente
                            target_row_index = map_articulo_a_fila.get(str(id_articulo_recibido)) # Obtener fila del map
                            item_oc_original = item_orig_data
                            break # Tomar la primera coincidencia con pendiente
                if not target_row_index:
                    print(f"Advertencia: Artículo '{id_articulo_recibido}' no encontrado en OC con pendiente o ya completo. Saltando.")
                    continue
            else:
                print("Advertencia: Falta id_item_oc o id_articulo en los datos recibidos. Saltando.")
                continue

            if not item_oc_original: continue # No se pudo asociar

            # Actualizar campos
            # Columnas: ID_ItemOC(1), ..., CantidadRecibida(8), CostoUnitarioReal(9), FechaRecepcionItem(10)
            # Actualizar CantidadRecibida (sumar a la existente)
            nueva_cantidad_recibida = float(item_oc_original.get('CantidadRecibida', 0)) + cantidad_rec
            updates_batch_items.append({
                'range': gspread.utils.rowcol_to_a1(target_row_index, 8), # Col H para CantidadRecibida
                'values': [[nueva_cantidad_recibida]]
            })
            updates_batch_items.append({
                'range': gspread.utils.rowcol_to_a1(target_row_index, 10), # Col J para FechaRecepcionItem
                'values': [[fecha_recep_str]]
            })
            if costo_real is not None:
                updates_batch_items.append({
                    'range': gspread.utils.rowcol_to_a1(target_row_index, 9), # Col I para CostoUnitarioReal
                    'values': [[costo_real]]
                })
            
            items_para_actualizar_stock.append({
                "id_articulo": item_oc_original.get('ID_Articulo'),
                "cantidad_ingresada": cantidad_rec,
                "costo_unitario": costo_real if costo_real is not None else float(item_oc_original.get('CostoUnitarioEstimado',0)),
                "id_referencia_origen": id_orden_compra,
                "tipo_origen": "COMPRA"
            })

        if updates_batch_items:
            ws_items_oc.batch_update(updates_batch_items)
            print(f"Ítems de OC {id_orden_compra} actualizados por recepción.")
        
        # Actualizar estado general de la OC (PENDIENTE, RECIBIDA PARCIAL, RECIBIDA COMPLETA)
        # Esto requiere volver a leer los ítems actualizados.
        all_items_oc_updated = ws_items_oc.get_all_records() # O filtrar los que acabamos de actualizar
        items_de_esta_oc_updated = [item for item in all_items_oc_updated if item.get('ID_OrdenCompra') == id_orden_compra]
        
        total_pendiente = 0
        total_recibido_parcialmente = 0
        for item in items_de_esta_oc_updated:
            cant_pedida = float(item.get('CantidadPedida', 0))
            cant_recibida = float(item.get('CantidadRecibida', 0))
            if cant_recibida < cant_pedida:
                total_pendiente += 1
            if cant_recibida > 0 and cant_recibida < cant_pedida:
                total_recibido_parcialmente +=1
        
        nuevo_estado_oc = "PENDIENTE"
        if total_pendiente == 0:
            nuevo_estado_oc = "RECIBIDA COMPLETA"
        elif total_recibido_parcialmente > 0 or (len(items_de_esta_oc_updated) > 0 and total_pendiente < len(items_de_esta_oc_updated)):
            # Si algún item se recibió parcialmente, o si no todos están pendientes (alguno se recibió)
            nuevo_estado_oc = "RECIBIDA PARCIAL"
        
        # Actualizar estado en la hoja OrdenesDeCompra
        ws_oc = g_handler.get_worksheet(SHEET_NAME_ORDENES_COMPRA)
        if ws_oc:
            try:
                cell_oc_estado = ws_oc.find(id_orden_compra, in_column=1) # ID_OrdenCompra es col 1
                if cell_oc_estado:
                    # Columna de Estado es la 6 (F)
                    ws_oc.update_cell(cell_oc_estado.row, 6, nuevo_estado_oc)
                    print(f"Estado de OC {id_orden_compra} actualizado a: {nuevo_estado_oc}")
            except gspread.exceptions.CellNotFound:
                print(f"Error: No se encontró la OC {id_orden_compra} para actualizar su estado.")
            except Exception as e_oc_update:
                print(f"Error actualizando estado de OC {id_orden_compra}: {e_oc_update}")


        # Finalmente, llamar a la función para ingresar el stock
        if items_para_actualizar_stock:
            resultado_stock = modifica_stock_compra.ingresar_stock_por_compra(
                items_ingresados=items_para_actualizar_stock,
                usuario=usuario_receptor,
                referencia_documento=f"OC: {id_orden_compra}, Remito: {nro_remito}, Fact: {nro_factura_proveedor}"
            )
            if resultado_stock["status"] == "success":
                return {"status": "success", "message": f"Recepción para OC {id_orden_compra} registrada y stock actualizado."}
            else:
                return {"status": "warning", "message": f"Recepción registrada, pero error al actualizar stock: {resultado_stock['message']}"}
        
        return {"status": "success", "message": f"Recepción para OC {id_orden_compra} registrada. No hubo items para stock."}

    except Exception as e:
        print(f"Error en registrar_recepcion_mercaderia: {e}")
        return {"status": "error", "message": str(e)}