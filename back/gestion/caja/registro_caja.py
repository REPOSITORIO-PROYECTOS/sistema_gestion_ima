# gestion/caja/registro_caja.py

from datetime import datetime
from utils.sheets_google_handler import GoogleSheetsHandler
from config import SHEET_NAME_CAJA_MOVIMIENTOS
from . import modifica_stock_caja # Para llamar a la función de modificar stock
from . import apertura_cierre # Para obtener ID de sesión actual
from gestion.contabilidad.clientes_contabilidad import gestion_clientes, cuentas_corrientes
from gestion.facturacion import motor_facturacion
import json 
from config import EMISOR_CONDICION_IVA # Para determinar tipo de comprobante

# g_handler = GoogleSheetsHandler() # Podría instanciarse aquí

def registrar_movimiento(id_sesion_caja: int, tipo_movimiento: str, descripcion: str, monto: float, usuario: str, detalles_adicionales=None):
    """
    Registra un movimiento genérico de caja (ingreso, egreso, venta).
    Asume una hoja con columnas: ID_Registro, ID_SesionCaja, Fecha, Hora, Tipo, Descripcion, Ingreso, Egreso, SaldoParcial, Usuario, Detalles
    """
    try:
        g_handler = GoogleSheetsHandler()
        if not g_handler.client:
            return {"status": "error", "message": "No se pudo conectar a Google Sheets."}

        now = datetime.now()
        fecha = now.strftime("%Y-%m-%d")
        hora = now.strftime("%H:%M:%S")

        ingreso = 0.0
        egreso = 0.0

        if tipo_movimiento.upper() in ["INGRESO", "VENTA"]:
            ingreso = monto
        elif tipo_movimiento.upper() == "EGRESO":
            egreso = monto
        else:
            return {"status": "error", "message": f"Tipo de movimiento '{tipo_movimiento}' no reconocido."}

        # Generar un ID de registro (similar al de sesión o un timestamp)
        id_registro = int(now.timestamp() * 1000) # Timestamp en milisegundos para mayor unicidad

        # El cálculo de SaldoParcial es complejo si se hace directamente en Sheets
        # sin scripts. Lo dejaremos en blanco o 0 por ahora.
        # Podría requerir leer el último saldo y sumar/restar.
        saldo_parcial = 0 # Placeholder

        data_row = [
            id_registro, id_sesion_caja, fecha, hora,
            tipo_movimiento.upper(), descripcion,
            ingreso, egreso, saldo_parcial, usuario,
            str(detalles_adicionales) if detalles_adicionales else ""
        ]

        if g_handler.append_row(SHEET_NAME_CAJA_MOVIMIENTOS, data_row):
            print(f"Movimiento '{tipo_movimiento}' registrado: {descripcion}, Monto: {monto}, Usuario: {usuario}")
            return {"status": "success", "id_registro": id_registro, "message": "Movimiento registrado."}
        else:
            return {"status": "error", "message": "Error al registrar movimiento en Google Sheets."}

    except Exception as e:
        print(f"Error en registrar_movimiento: {e}")
        return {"status": "error", "message": str(e)}


def registrar_venta(id_sesion_caja: int, articulos_vendidos: list, id_cliente: str, # Cambiado de cliente_nombre a id_cliente
                    metodo_pago: str, usuario: str, total_venta: float,
                    quiere_factura: bool = True, tipo_comprobante_solicitado: str = None, # Nuevos params
                    paga_con: float = None): # Nuevo: monto con el que paga el cliente
    """
    Registra una venta. Puede o no generar factura y afectar Cta Cte.
    articulos_vendidos: lista de dicts [{'id_articulo': X, 'cantidad': Y, 'precio_unitario': Z, 'subtotal': W, 'tasa_iva': Tasa}, ...]
                        Asegúrate de que cada item tenga 'tasa_iva'.
    tipo_comprobante_solicitado: "Factura A", "Factura B", "Factura C", "Ticket Consumidor Final", "Ticket No Fiscal"
    """
    g_handler = GoogleSheetsHandler() # Asumimos configurado

    # 1. Obtener datos del cliente
    cliente_data = gestion_clientes.obtener_cliente_por_id(id_cliente)
    if not cliente_data:
        return {"status": "error", "message": f"Cliente con ID {id_cliente} no encontrado."}
    
    nombre_cliente_para_desc = cliente_data.get("NombreApellido", cliente_data.get("RazonSocial", "Desconocido"))
    descripcion_venta = f"Venta a {nombre_cliente_para_desc}. Método: {metodo_pago}. Items: {len(articulos_vendidos)}"
    detalles_venta = {
        "id_cliente": id_cliente,
        "nombre_cliente": nombre_cliente_para_desc,
        "metodo_pago": metodo_pago,
        "articulos": articulos_vendidos,
        "total": total_venta,
        "quiere_factura": quiere_factura,
        "tipo_comprobante_solicitado": tipo_comprobante_solicitado,
        "paga_con": paga_con
    }

    # 2. Registrar el movimiento de caja (como VENTA)
    #    El monto que ingresa a caja es el total_venta si es contado, o 0 si es Cta. Cte. pura.
    #    Si es Cta. Cte. parcial, el monto_caja es lo que paga en efectivo/tarjeta.
    monto_para_caja = total_venta
    afecta_cta_cte = False
    monto_a_cta_cte = 0.0

    if metodo_pago.upper() == "CUENTA_CORRIENTE":
        if cliente_data.get("PermiteCuentaCorriente", "NO").upper() != "SI":
            return {"status": "error", "message": f"El cliente {nombre_cliente_para_desc} no tiene habilitada la cuenta corriente."}
        
        saldo_actual_cc = float(str(cliente_data.get("SaldoCuentaCorriente", "0")).replace(',', '.'))
        limite_credito = float(str(cliente_data.get("LimiteCredito", "0")).replace(',', '.'))
        if limite_credito > 0 and (saldo_actual_cc + total_venta) > limite_credito:
            return {"status": "error", "message": f"La venta excede el límite de crédito del cliente. Límite: ${limite_credito:.2f}, Saldo actual+Venta: ${saldo_actual_cc + total_venta:.2f}"}

        monto_para_caja = 0 # Todo a Cta Cte
        afecta_cta_cte = True
        monto_a_cta_cte = total_venta
        descripcion_venta += " (Cta. Cte.)"
    elif metodo_pago.upper() == "MIXTO" and paga_con is not None: # Ej: parte efectivo, parte CC
        # Asumimos que 'paga_con' es lo que entra a caja
        if paga_con < 0 : return {"status": "error", "message": "El monto pagado en modo mixto no puede ser negativo."}
        if paga_con >= total_venta: # Cubrió todo o más, no va a CC
            monto_para_caja = total_venta # A caja va el total de la venta (el vuelto se calcula después)
            afecta_cta_cte = False
        else: # paga_con < total_venta, la diferencia va a CC
            if cliente_data.get("PermiteCuentaCorriente", "NO").upper() != "SI":
                return {"status": "error", "message": f"El cliente {nombre_cliente_para_desc} no tiene habilitada la cuenta corriente para el saldo pendiente."}
            
            monto_para_caja = paga_con
            monto_a_cta_cte = total_venta - paga_con
            afecta_cta_cte = True
            # ... (verificar límite de crédito para monto_a_cta_cte) ...
            saldo_actual_cc = float(str(cliente_data.get("SaldoCuentaCorriente", "0")).replace(',', '.'))
            limite_credito = float(str(cliente_data.get("LimiteCredito", "0")).replace(',', '.'))
            if limite_credito > 0 and (saldo_actual_cc + monto_a_cta_cte) > limite_credito:
                 return {"status": "error", "message": f"El saldo a Cta. Cte. excede el límite de crédito del cliente."}

            descripcion_venta += f" (Pago parcial caja: ${monto_para_caja:.2f}, Cta. Cte.: ${monto_a_cta_cte:.2f})"
    
    resultado_movimiento = registrar_movimiento( # Esta función ya la tienes
        id_sesion_caja=id_sesion_caja,
        tipo_movimiento="VENTA", # Aunque sea a CC, es una venta que puede tener un pago parcial
        descripcion=descripcion_venta,
        monto=monto_para_caja, # Solo lo que ingresa a caja
        usuario=usuario,
        detalles_adicionales=detalles_venta
    )

    if resultado_movimiento["status"] != "success":
        return resultado_movimiento # Devuelve el error del registro del movimiento

    id_registro_venta_caja = resultado_movimiento.get("id_registro")

    # 3. Afectar Cuenta Corriente si aplica
    if afecta_cta_cte and monto_a_cta_cte > 0:
        res_cc = cuentas_corrientes.registrar_movimiento_cc_cliente(
            id_cliente=id_cliente,
            tipo_comprobante="VENTA_CC",
            id_comprobante_origen=str(id_registro_venta_caja), # ID de la Venta en CajaRegistros
            descripcion=f"Saldo de venta (Reg: {id_registro_venta_caja})",
            debe=monto_a_cta_cte, # Aumenta la deuda del cliente
            usuario=usuario
        )
        if res_cc["status"] != "success":
            # Problema: la venta se registró en caja pero no en CC. Requiere manejo.
            # Podrías intentar anular el movimiento de caja o marcarlo para revisión.
            return {"status": "error", "message": f"Venta registrada en caja, pero error en Cta. Cte.: {res_cc['message']}"}

    # 4. Generar Comprobante (Factura o Ticket No Fiscal)
    id_comprobante_final_emitido = None
    numero_comprobante_final_emitido = "N/A"

    if quiere_factura:
        tipo_factura_a_emitir = ""
        if tipo_comprobante_solicitado and tipo_comprobante_solicitado != "Ticket No Fiscal":
            # Validar si el emisor puede emitir este tipo al cliente
            tipo_calculado = motor_facturacion.determinar_tipo_comprobante_afip(
                EMISOR_CONDICION_IVA,
                cliente_data.get("CondicionIVA", "CONSUMIDOR_FINAL")
            )
            # Si el solicitado es más específico (ej. Factura A) y es compatible con el calculado, se usa.
            # Si el emisor es Monotributista, solo puede C. Si es RI, puede A o B.
            if EMISOR_CONDICION_IVA == "MONOTRIBUTISTA" and tipo_comprobante_solicitado not in ["Factura C", "Ticket Consumidor Final"]:
                print(f"Advertencia: Emisor Monotributista. Se emitirá Factura C en lugar de {tipo_comprobante_solicitado}.")
                tipo_factura_a_emitir = "Factura C"
            elif EMISOR_CONDICION_IVA == "RESPONSABLE_INSCRIPTO":
                if tipo_comprobante_solicitado == "Factura A" and tipo_calculado == "Factura A":
                    tipo_factura_a_emitir = "Factura A"
                elif tipo_comprobante_solicitado == "Factura B" and tipo_calculado == "Factura B":
                    tipo_factura_a_emitir = "Factura B"
                else: # Si no coincide o es genérico como "Ticket Consumidor Final"
                    tipo_factura_a_emitir = tipo_calculado # Usar el calculado por defecto
            else: # Otros emisores (simplificado)
                 tipo_factura_a_emitir = tipo_calculado

            if not tipo_factura_a_emitir: # Si algo salió mal en la determinación
                tipo_factura_a_emitir = "Ticket Consumidor Final" # Fallback

        elif tipo_comprobante_solicitado == "Ticket No Fiscal":
            tipo_factura_a_emitir = "Ticket No Fiscal"
        else: # Determinar automáticamente si no se especificó
            tipo_factura_a_emitir = motor_facturacion.determinar_tipo_comprobante_afip(
                EMISOR_CONDICION_IVA,
                cliente_data.get("CondicionIVA", "CONSUMIDOR_FINAL")
            )
        
        # Para la facturación online, necesitamos todos los datos del cliente y los items
        items_para_factura = []
        for item_v in articulos_vendidos:
            # Asegúrate que cada 'item_v' tenga 'tasa_iva'
            # Esto debería venir desde la info del artículo en stock.
            # Si no, asigna una por defecto o busca en el maestro de artículos.
            tasa_iva_item = item_v.get('tasa_iva', 21.0) # Ejemplo, obtenerla del producto real
            items_para_factura.append({
                "codigo": item_v.get("id_articulo"),
                "descripcion": item_v.get("nombre"),
                "cantidad": item_v.get("cantidad"),
                "precio_unitario_neto": item_v.get("precio_unitario"), # Asumir que es neto, o ajustar
                "tasa_iva": tasa_iva_item, # ej. 21.00 para 21%
                "subtotal": item_v.get("subtotal")
            })

        res_factura = motor_facturacion.registrar_comprobante_emitido(
            id_operacion_origen=str(id_registro_venta_caja),
            tipo_comprobante=tipo_factura_a_emitir,
            datos_cliente={
                "ID_Cliente": id_cliente,
                "NombreApellido": nombre_cliente_para_desc,
                "NumeroDocumento": cliente_data.get("NumeroDocumento"),
                "TipoDocumento": cliente_data.get("TipoDocumento"),
                "CondicionIVA": cliente_data.get("CondicionIVA")
            },
            total_comprobante=total_venta,
            items_comprobante=items_para_factura,
            facturar_online=(tipo_factura_a_emitir not in ["Ticket No Fiscal", "PRESUPUESTO", "REMITO"]) # Solo facturas van online
        )
        if res_factura["status"] == "success" or res_factura["status"] == "error_afip": # Guardamos incluso si AFIP rechazó
            id_comprobante_final_emitido = res_factura.get("id_comprobante_emitido")
            numero_comprobante_final_emitido = res_factura.get("numero_comprobante")
            if res_factura["status"] == "error_afip":
                print(f"Advertencia: Comprobante {numero_comprobante_final_emitido} RECHAZADO por AFIP (simulado).")
        else:
            print(f"Error al generar/registrar comprobante: {res_factura['message']}")
            # Podría ser un problema grave si la venta se hizo y no se pudo facturar.

    # 5. Modificar Stock
    print("Venta registrada, procediendo a modificar stock...")
    items_para_stock = [{"id_articulo": item['id_articulo'], "cantidad_vendida": item['cantidad']} for item in articulos_vendidos]
    resultado_stock = modifica_stock_caja.actualizar_stock_por_venta(id_sesion_caja, items_para_stock, usuario) # Esta función ya la tienes (simulada)

    final_message = f"Venta registrada (ID Caja: {id_registro_venta_caja})."
    if id_comprobante_final_emitido:
        final_message += f" Comprobante: {numero_comprobante_final_emitido} (ID: {id_comprobante_final_emitido})."
    if afecta_cta_cte:
        final_message += " Afectó Cta. Cte."
    if resultado_stock["status"] != "success":
        final_message += f" Advertencia Stock: {resultado_stock['message']}"

    return {
        "status": "success",
        "id_registro_venta": id_registro_venta_caja,
        "id_comprobante_emitido": id_comprobante_final_emitido,
        "numero_comprobante": numero_comprobante_final_emitido,
        "message": final_message
    }

# Podrías añadir funciones específicas para registrar_ingreso y registrar_egreso
# que simplemente llamen a registrar_movimiento con los parámetros correctos.
def registrar_ingreso_efectivo(id_sesion_caja: int, concepto: str, monto: float, usuario: str):
    return registrar_movimiento(id_sesion_caja, "INGRESO", concepto, monto, usuario)

def registrar_egreso_efectivo(id_sesion_caja: int, concepto: str, monto: float, usuario: str):
    return registrar_movimiento(id_sesion_caja, "EGRESO", concepto, monto, usuario)

def calcular_vuelto(total_a_pagar: float, monto_recibido: float, metodo_pago: str = "EFECTIVO"):
    """
    Calcula el vuelto para una transacción.
    Por ahora, solo maneja efectivo. Podría extenderse para otros métodos.
    """
    print(f"\n--- Calculadora de Vuelto ---")
    print(f"Total a pagar: ${total_a_pagar:.2f}")
    print(f"Monto recibido ({metodo_pago}): ${monto_recibido:.2f}")

    if metodo_pago.upper() != "EFECTIVO":
        print("Cálculo de vuelto automático usualmente aplica a pagos en EFECTIVO.")
        # Podrías preguntar si igual quiere calcularlo o manejar lógicas para tarjeta + efectivo, etc.
        # return None o 0 si no hay vuelto

    if monto_recibido < total_a_pagar:
        print(f"Monto insuficiente. Faltan: ${total_a_pagar - monto_recibido:.2f}")
        return None # O levantar un error

    vuelto = monto_recibido - total_a_pagar
    print(f"Vuelto a entregar: ${vuelto:.2f}")
    return vuelto

