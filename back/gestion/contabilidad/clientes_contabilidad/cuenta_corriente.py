# gestion/contabilidad/clientes_contabilidad/cuentas_corrientes.py
from config import SHEET_NAME_MOVIMIENTOS_CC_CLIENTE, SHEET_NAME_CLIENTES # Re-importar SHEET_NAME_CLIENTES

def generar_id_movimiento_cc(g_handler):
    # ... Lógica para generar ID único para movimientos CC ...
    return f"MCC{int(datetime.now().timestamp() * 1000)}"

def registrar_movimiento_cc_cliente(id_cliente: str, tipo_comprobante: str, id_comprobante_origen: str,
                                   descripcion: str, debe: float = 0.0, haber: float = 0.0, usuario: str = "sistema"):
    try:
        g_handler = GoogleSheetsHandler()
        cliente = obtener_cliente_por_id(id_cliente) # Usa la función de gestion_clientes
        if not cliente:
            return {"status": "error", "message": f"Cliente {id_cliente} no encontrado para CC."}

        # Calcular nuevo saldo para el movimiento y para el cliente
        saldo_anterior_cliente = float(str(cliente.get('SaldoCuentaCorriente', '0')).replace(',', '.'))
        saldo_parcial_movimiento = saldo_anterior_cliente + debe - haber
        
        id_mov_cc = generar_id_movimiento_cc(g_handler)
        fecha_mov = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        data_row_mov = [
            id_mov_cc, id_cliente, fecha_mov, tipo_comprobante, id_comprobante_origen,
            descripcion, debe, haber, saldo_parcial_movimiento, usuario
        ]
        # Columnas: ID_MovimientoCC, ID_Cliente, Fecha, TipoComprobanteOrigen, ID_ComprobanteOrigen,
        #           Descripcion, Debe, Haber, SaldoParcial, Usuario

        if not g_handler.append_row(SHEET_NAME_MOVIMIENTOS_CC_CLIENTE, data_row_mov):
            return {"status": "error", "message": "Error al guardar movimiento en CC."}

        # Actualizar SaldoCuentaCorriente en la hoja Clientes
        ws_clientes = g_handler.get_worksheet(SHEET_NAME_CLIENTES)
        if ws_clientes:
            try:
                # Asumiendo ID_Cliente es col 1 y SaldoCuentaCorriente es col 11 (K)
                cell_cliente = ws_clientes.find(id_cliente, in_column=1)
                if cell_cliente:
                    ws_clientes.update_cell(cell_cliente.row, 11, saldo_parcial_movimiento) # Col K
                else:
                    print(f"Advertencia: Cliente {id_cliente} no encontrado en hoja Clientes para actualizar saldo.")
            except gspread.exceptions.CellNotFound:
                 print(f"Advertencia: Cliente {id_cliente} no encontrado en hoja Clientes para actualizar saldo.")
            except Exception as e_upd_saldo:
                print(f"Error actualizando saldo de cliente {id_cliente}: {e_upd_saldo}")
        
        return {"status": "success", "id_movimiento_cc": id_mov_cc, "message": "Movimiento en CC registrado."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def obtener_saldo_cc_cliente(id_cliente: str):
    cliente = obtener_cliente_por_id(id_cliente)
    if cliente:
        return float(str(cliente.get('SaldoCuentaCorriente', '0')).replace(',', '.'))
    return 0.0 # O None si se prefiere error