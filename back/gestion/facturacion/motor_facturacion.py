# gestion/facturacion/motor_facturacion.py
from config import (
    EMISOR_CONDICION_IVA, EMISOR_PUNTO_VENTA_DEFAULT, SHEET_NAME_COMPROBANTES_EMITIDOS,
    EMISOR_RAZON_SOCIAL, EMISOR_CUIT
)
from utils.sheets_google_handler import GoogleSheetsHandler
from datetime import datetime

def generar_id_comprobante_emitido(g_handler):
    return f"CE{int(datetime.now().timestamp() * 1000)}"

def determinar_tipo_comprobante_afip(condicion_iva_emisor: str, condicion_iva_cliente: str):
    """Determina qué tipo de factura AFIP corresponde."""
    emisor = condicion_iva_emisor.upper()
    cliente = condicion_iva_cliente.upper()

    if emisor == "RESPONSABLE_INSCRIPTO":
        if cliente == "RESPONSABLE_INSCRIPTO": return "Factura A"
        if cliente in ["MONOTRIBUTISTA", "CONSUMIDOR_FINAL", "EXENTO"]: return "Factura B"
    elif emisor == "MONOTRIBUTISTA":
        # Monotributistas emiten Factura C a todos (o Ticket C)
        return "Factura C" # O "Ticket C" si es el comprobante por defecto
    # Añadir más lógicas si el emisor es Exento, etc.
    return "Ticket Consumidor Final" # Por defecto si no hay match claro

def simular_facturacion_online(datos_factura: dict):
    """
    Simula la llamada a una API de facturación online (ej. AFIP WSFE).
    En un sistema real, aquí iría la lógica con suds, zeep, o requests.
    """
    print(f"\n--- SIMULANDO FACTURACIÓN ONLINE PARA: {datos_factura.get('NumeroComprobanteAFIP')} ---")
    print(f"  Tipo: {datos_factura.get('TipoComprobanteAFIP')}")
    print(f"  Cliente: {datos_factura.get('NombreCliente')} ({datos_factura.get('CUIT_DNI_Cliente')})")
    print(f"  Total: {datos_factura.get('TotalComprobante')}")
    
    # Simular una respuesta exitosa de AFIP
    if "error" not in datos_factura.get("TipoComprobanteAFIP", "").lower(): # No simular error si el tipo es raro
        cae_simulado = f"CAE_SIMULADO_{int(datetime.now().timestamp())}"
        fecha_vto_cae_simulado = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
        print(f"  CAE Simulado: {cae_simulado}, Vto: {fecha_vto_cae_simulado}")
        return {
            "status_afip": "APROBADO",
            "cae": cae_simulado,
            "fecha_vto_cae": fecha_vto_cae_simulado,
            "numero_comprobante": datos_factura.get("NumeroComprobanteAFIP"), # Devolver el mismo número
            "qr_data": "URL_QR_SIMULADA_o_datos_para_generar_QR",
            "pdf_url": f"http://dominio.com/facturas/{cae_simulado}.pdf" # Simulado
        }
    else:
        print("  Simulación de error en AFIP.")
        return {
            "status_afip": "RECHAZADO",
            "errores_afip": [{"code": "001", "msg": "Error simulado de AFIP."}]
        }


def registrar_comprobante_emitido(id_operacion_origen: str, tipo_comprobante: str,
                                  datos_cliente: dict, total_comprobante: float,
                                  items_comprobante: list, # Para reconstruir la factura si es necesario
                                  facturar_online: bool = True):
    """
    Genera y registra un comprobante (fiscal o no).
    datos_cliente: {'ID_Cliente', 'NombreApellido', 'CUIT_DNI_Cliente', 'CondicionIVA'}
    """
    try:
        g_handler = GoogleSheetsHandler()
        id_comprobante_emitido = generar_id_comprobante_emitido(g_handler)
        fecha_emision = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        tipo_comprobante_final = tipo_comprobante # Ej: "Ticket No Fiscal", "PRESUPUESTO", etc.
        cae = None
        fecha_vto_cae = None
        estado_afip = "NO_APLICA" # Para comprobantes no fiscales
        url_pdf = None
        
        # Obtener último número de comprobante para el tipo y punto de venta (simulado)
        # En un sistema real, AFIP devuelve el número o lo consultas antes.
        # Aquí lo simulamos de forma simple.
        registros_comp = g_handler.get_all_records(SHEET_NAME_COMPROBANTES_EMITIDOS)
        ultimo_numero = 0
        for reg_comp in registros_comp:
            if reg_comp.get('TipoComprobanteAFIP') == tipo_comprobante and \
               reg_comp.get('PuntoVentaAFIP') == EMISOR_PUNTO_VENTA_DEFAULT and \
               str(reg_comp.get('NumeroComprobanteAFIP')).isdigit():
                ultimo_numero = max(ultimo_numero, int(reg_comp.get('NumeroComprobanteAFIP')))
        numero_comprobante_nuevo = str(ultimo_numero + 1).zfill(8)


        if facturar_online and tipo_comprobante in ["Factura A", "Factura B", "Factura C"]: # Tipos que van a AFIP
            datos_para_api = {
                "ID_ComprobanteEmitido": id_comprobante_emitido,
                "TipoComprobanteAFIP": tipo_comprobante,
                "PuntoVentaAFIP": EMISOR_PUNTO_VENTA_DEFAULT,
                "NumeroComprobanteAFIP": numero_comprobante_nuevo, # Este número podría venir de la API de AFIP
                "FechaEmision": fecha_emision.split(" ")[0], # Solo fecha YYYY-MM-DD
                "ID_Cliente": datos_cliente.get("ID_Cliente"),
                "NombreCliente": datos_cliente.get("NombreApellido"),
                "CUIT_DNI_Cliente": datos_cliente.get("NumeroDocumento"),
                "TipoDocCliente": datos_cliente.get("TipoDocumento"), # Necesario para AFIP
                "CondicionIVACliente": datos_cliente.get("CondicionIVA"),
                "TotalComprobante": total_comprobante,
                "Items": items_comprobante, # Lista de items con detalle, precio, iva, etc.
                "EmisorCUIT": EMISOR_CUIT,
                # ... más datos que pida la API de AFIP ...
            }
            respuesta_api = simular_facturacion_online(datos_para_api)
            
            estado_afip = respuesta_api.get("status_afip")
            if estado_afip == "APROBADO":
                cae = respuesta_api.get("cae")
                fecha_vto_cae = respuesta_api.get("fecha_vto_cae")
                numero_comprobante_nuevo = respuesta_api.get("numero_comprobante", numero_comprobante_nuevo) # AFIP puede dar el nro
                url_pdf = respuesta_api.get("pdf_url")
                print(f"Comprobante {tipo_comprobante} N° {EMISOR_PUNTO_VENTA_DEFAULT}-{numero_comprobante_nuevo} APROBADO. CAE: {cae}")
            else:
                print(f"Error al facturar online: {respuesta_api.get('errores_afip')}")
                # Podrías decidir no guardar este comprobante o guardarlo como RECHAZADO.
                # Por ahora, lo guardamos como RECHAZADO si la simulación falla.
                tipo_comprobante_final = f"{tipo_comprobante}_RECHAZADO_AFIP" # Para distinguirlo
        
        # Guardar en la hoja ComprobantesEmitidos
        datos_adicionales_json = {
            "items": items_comprobante,
            "emisor_cond_iva": EMISOR_CONDICION_IVA,
            "cliente_cond_iva": datos_cliente.get("CondicionIVA")
        }
        if 'respuesta_api' in locals(): # Si hubo intento de facturación online
            datos_adicionales_json['respuesta_api_simulada'] = respuesta_api

        data_row_comp = [
            id_comprobante_emitido, id_operacion_origen, fecha_emision,
            tipo_comprobante_final, EMISOR_PUNTO_VENTA_DEFAULT, numero_comprobante_nuevo,
            cae if cae else "", fecha_vto_cae if fecha_vto_cae else "",
            datos_cliente.get("ID_Cliente"), datos_cliente.get("NombreApellido"), datos_cliente.get("NumeroDocumento"),
            total_comprobante, url_pdf if url_pdf else "", estado_afip,
            json.dumps(datos_adicionales_json) # Guardar detalles como JSON
        ]
        # Columnas: ID_ComprobanteEmitido, ID_OperacionOrigen, FechaEmision, TipoComprobanteAFIP,
        #           PuntoVentaAFIP, NumeroComprobanteAFIP, CAE, FechaVtoCAE, ID_Cliente, NombreCliente,
        #           CUIT_DNI_Cliente, TotalComprobante, URL_PDF_Comprobante, EstadoAFIP, DatosAdicionalesJSON

        if g_handler.append_row(SHEET_NAME_COMPROBANTES_EMITIDOS, data_row_comp):
            return {
                "status": "success" if estado_afip in ["APROBADO", "NO_APLICA"] else "error_afip",
                "id_comprobante_emitido": id_comprobante_emitido,
                "tipo_comprobante": tipo_comprobante_final,
                "numero_comprobante": f"{EMISOR_PUNTO_VENTA_DEFAULT}-{numero_comprobante_nuevo}",
                "cae": cae,
                "message": f"Comprobante {tipo_comprobante_final} registrado."
            }
        else:
            return {"status": "error", "message": "Error al guardar comprobante emitido."}

    except Exception as e:
        return {"status": "error", "message": str(e)}