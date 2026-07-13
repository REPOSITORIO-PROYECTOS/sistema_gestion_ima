# back/gestion/reportes/qr_generator.py

import base64
import json
from io import BytesIO
from typing import Optional

import qrcode

from back.schemas.comprobante_schemas import GenerarComprobanteRequest


def _construir_json_qr_afip(req: GenerarComprobanteRequest) -> Optional[dict]:
    """Arma el payload JSON de AFIP para el QR fiscal."""
    es_fiscal = req.tipo.lower() in {"factura", "comprobante"}
    datos_afip = req.transaccion.afip
    if not (es_fiscal and datos_afip is not None):
        return None

    try:
        fecha_raw = datos_afip.fecha_emision
        fecha = fecha_raw.split("T")[0] if isinstance(fecha_raw, str) else str(fecha_raw)
        return {
            "ver": 1,
            "fecha": fecha,
            "cuit": req.emisor.cuit,
            "pto_vta": req.emisor.punto_venta,
            "tipo_cbte": datos_afip.tipo_comprobante_afip,
            "nro_cbte": datos_afip.numero_comprobante,
            "importe": req.transaccion.total,
            "moneda": "PES",
            "cotiz": 1,
            "tipo_doc_rec": datos_afip.codigo_tipo_doc_receptor,
            "nro_doc_rec": int(req.receptor.cuit_o_dni or 0),
            "tipo_cod_aut": "E",
            "cod_aut": int(datos_afip.cae),
        }
    except (AttributeError, TypeError, ValueError):
        return None


def construir_url_qr_afip(req: GenerarComprobanteRequest) -> Optional[str]:
    """Devuelve la URL oficial de AFIP embebida en el QR."""
    json_data = _construir_json_qr_afip(req)
    if not json_data:
        return None
    json_string = json.dumps(json_data)
    base64_string = base64.b64encode(json_string.encode("utf-8")).decode("utf-8")
    return f"https://www.afip.gob.ar/fe/qr/?p={base64_string}"


def qr_url_a_lineas_ascii(url: str, ancho: int) -> list[str]:
    """
    Renderiza el QR como arte ASCII centrado para tickets en texto plano.
    Ajusta la densidad según el ancho disponible (58mm/80mm).
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=1,
        border=1,
    )
    qr.add_data(url)
    qr.make(fit=True)
    matrix = qr.get_matrix()

    celda, vacio = "██", "  "
    lineas_crudas = ["".join((celda if celda_on else vacio) for celda_on in fila) for fila in matrix]
    ancho_qr = len(lineas_crudas[0]) if lineas_crudas else 0

    if ancho_qr > ancho:
        celda, vacio = "█", " "
        lineas_crudas = ["".join((celda if celda_on else vacio) for celda_on in fila) for fila in matrix]
        ancho_qr = len(lineas_crudas[0]) if lineas_crudas else 0

    resultado = ["[ QR AFIP ]".center(ancho)]
    if ancho_qr <= ancho:
        resultado.extend(linea.center(ancho) for linea in lineas_crudas)
        return resultado

    # Si no entra el gráfico, dejamos la URL verificable en varias líneas.
    resultado.append("URL AFIP:".center(ancho))
    resultado.extend(_partir_url_qr(url, ancho))
    return resultado


def _partir_url_qr(url: str, ancho: int) -> list[str]:
    return [url[i : i + ancho] for i in range(0, len(url), ancho)]


def generar_qr_para_comprobante(req: GenerarComprobanteRequest) -> str | None:
    """
    Función centralizada que genera el QR en Base64 para un comprobante.
    """
    print("\n--- [DEBUG QR: Iniciando generación de QR] ---")

    url_qr = construir_url_qr_afip(req)
    if not url_qr:
        print("-> [DEBUG QR] SALIDA ANTICIPADA: No se genera QR.")
        return None

    print("-> [DEBUG QR] URL generada correctamente.")

    try:
        print("-> [DEBUG QR] Generando imagen PNG del QR...")
        qr_img = qrcode.make(url_qr, border=1)
        buffered = BytesIO()
        qr_img.save(buffered, format="PNG")
        resultado_final = base64.b64encode(buffered.getvalue()).decode("utf-8")
        print("-> [DEBUG QR] ÉXITO: Imagen QR generada y codificada en Base64.")
        print("--- [DEBUG QR: Finalizado con éxito] ---\n")
        return resultado_final
    except Exception as e:
        print(f"-> [DEBUG QR] FALLO: Error al crear la imagen PNG del QR: {e}")
        return None