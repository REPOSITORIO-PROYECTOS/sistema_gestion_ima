# back/gestion/reportes/qr_generator.py

import qrcode
import base64
import json
from io import BytesIO
from back.schemas.comprobante_schemas import GenerarComprobanteRequest # Importamos el schema

def generar_qr_para_comprobante(req: GenerarComprobanteRequest) -> str | None:
    """
    Función centralizada que genera el QR en Base64 para un comprobante.
    Incluye prints de depuración para rastrear el flujo.
    """
    print("\n--- [DEBUG QR: Iniciando generación de QR] ---")

    # 1. Verificación inicial: ¿Es una factura con datos de AFIP?
    es_factura = req.tipo.lower() == "factura"
    tiene_afip_attr = hasattr(req.transaccion, 'afip')
    datos_afip_existen = tiene_afip_attr and req.transaccion.afip is not None

    if not (es_factura and datos_afip_existen):
        print(f"-> [DEBUG QR] SALIDA ANTICIPADA: No se genera QR.")
        print(f"   - ¿Es factura?: {es_factura}")
        print(f"   - ¿Tiene datos AFIP?: {datos_afip_existen}")
        return None
    
    print("-> [DEBUG QR] PASO 1: Es una factura y tiene datos de AFIP. Procediendo...")

    # 2. Construcción del diccionario de datos para el QR
    try:
        print("-> [DEBUG QR] PASO 2: Intentando construir el diccionario de datos...")
        json_data = {
            "ver": 1,
            # Asegúrate de que el formato de fecha sea YYYY-MM-DD
            "fecha": req.transaccion.afip.fecha_emision.split('T')[0],
            "cuit": req.emisor.cuit,
            "pto_vta": req.emisor.punto_venta,
            "tipo_cbte": req.transaccion.afip.tipo_comprobante_afip,
            "nro_cbte": req.transaccion.afip.numero_comprobante,
            "importe": req.transaccion.total,
            "moneda": "PES",
            "cotiz": 1,
            "tipo_doc_rec": req.transaccion.afip.codigo_tipo_doc_receptor,
            "nro_doc_rec": int(req.receptor.cuit_o_dni),
            "tipo_cod_aut": "E",
            "cod_aut": int(req.transaccion.afip.cae)
        }
        print("-> [DEBUG QR] ÉXITO: Diccionario de datos construido:")
        print(json.dumps(json_data, indent=2))

    except (AttributeError, TypeError, ValueError) as e:
        print(f"-> [DEBUG QR] FALLO: Faltan datos o hay un error de tipo al construir el diccionario.")
        print(f"   - Error específico: {type(e).__name__}: {e}")
        print("   - Esto suele pasar si un campo (ej. 'cae') es None o no se puede convertir a entero.")
        return None

    # 3. Construcción de la URL completa de AFIP
    try:
        print("-> [DEBUG QR] PASO 3: Construyendo la URL para AFIP...")
        json_string = json.dumps(json_data)
        base64_string = base64.b64encode(json_string.encode('utf-8')).decode('utf-8')
        url_qr = f"https://www.afip.gob.ar/fe/qr/?p={base64_string}"
        print("-> [DEBUG QR] ÉXITO: URL generada.")
    except Exception as e:
        print(f"-> [DEBUG QR] FALLO: Error al codificar en Base64 la URL: {e}")
        return None


    # 4. Generación de la imagen del QR y devolución como string Base64
    try:
        print("-> [DEBUG QR] PASO 4: Generando la imagen PNG del QR...")
        qr_img = qrcode.make(url_qr, border=1)
        buffered = BytesIO()
        qr_img.save(buffered, format="PNG")
        img_bytes = buffered.getvalue()
        
        resultado_final = base64.b64encode(img_bytes).decode('utf-8')
        print("-> [DEBUG QR] ÉXITO: Imagen QR generada y codificada en Base64.")
        print("--- [DEBUG QR: Finalizado con éxito] ---\n")
        return resultado_final
    except Exception as e:
        print(f"-> [DEBUG QR] FALLO: Error al crear la imagen PNG del QR: {e}")
        return None