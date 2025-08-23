# back/gestion/reportes/qr_generator.py

import qrcode
import base64
import json
from io import BytesIO
from back.schemas.comprobante_schemas import GenerarComprobanteRequest # Importamos el schema

def generar_qr_para_comprobante(req: GenerarComprobanteRequest) -> str | None:
    """
    Función centralizada que genera el QR en Base64 para un comprobante.
    Devuelve el string Base64 si es una factura con datos AFIP, o None en caso contrario.
    """
    # 1. Verificamos si es necesario generar un QR
    if not (req.tipo.lower() == "factura" and hasattr(req.transaccion, 'afip') and req.transaccion.afip):
        return None # No es una factura o no tiene datos de AFIP

    # 2. Construimos el diccionario de datos para el QR
    try:
        json_data = {
            "ver": 1,
            "fecha": req.transaccion.afip.fecha_emision,
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
    except (AttributeError, TypeError) as e:
        print(f"[ADVERTENCIA] Faltan datos para generar el QR: {e}")
        return None # Si falta algún dato de AFIP, no generamos el QR

    # 3. Construimos la URL completa de AFIP
    json_string = json.dumps(json_data)
    base64_string = base64.b64encode(json_string.encode('utf-8')).decode('utf-8')
    url_qr = f"https://www.afip.gob.ar/fe/qr/?p={base64_string}"

    # 4. Generamos la imagen del QR y la devolvemos como string Base64
    qr_img = qrcode.make(url_qr, border=1)
    buffered = BytesIO()
    qr_img.save(buffered, format="PNG")
    img_bytes = buffered.getvalue()
    
    return base64.b64encode(img_bytes).decode('utf-8')