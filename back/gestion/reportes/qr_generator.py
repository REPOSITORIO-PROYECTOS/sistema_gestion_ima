# back/gestion/reportes/qr_generator.py

import base64
import html
import json
from io import BytesIO
from typing import Optional

import qrcode

from back.schemas.comprobante_schemas import GenerarComprobanteRequest


def _solo_digitos(valor: object) -> str:
    return "".join(ch for ch in str(valor or "") if ch.isdigit())


def _cuit_a_int(cuit: object) -> int:
    digitos = _solo_digitos(cuit)
    return int(digitos) if digitos else 0


def _construir_json_qr_afip(req: GenerarComprobanteRequest) -> Optional[dict]:
    """Arma el payload JSON de AFIP para el QR fiscal (RG 4892)."""
    es_fiscal = req.tipo.lower() in {"factura", "comprobante"}
    datos_afip = req.transaccion.afip
    if not (es_fiscal and datos_afip is not None):
        return None

    try:
        fecha_raw = datos_afip.fecha_emision
        fecha = fecha_raw.split("T")[0] if isinstance(fecha_raw, str) else str(fecha_raw)
        cae_digitos = _solo_digitos(datos_afip.cae)
        if not cae_digitos:
            return None
        return {
            "ver": 1,
            "fecha": fecha,
            "cuit": _cuit_a_int(req.emisor.cuit),
            "pto_vta": int(req.emisor.punto_venta),
            "tipo_cbte": int(datos_afip.tipo_comprobante_afip),
            "nro_cbte": int(datos_afip.numero_comprobante),
            "importe": float(req.transaccion.total),
            "moneda": "PES",
            "cotiz": 1,
            "tipo_doc_rec": int(datos_afip.codigo_tipo_doc_receptor),
            "nro_doc_rec": int(_solo_digitos(req.receptor.cuit_o_dni) or 0),
            "tipo_cod_aut": "E",
            "cod_aut": int(cae_digitos),
        }
    except (AttributeError, TypeError, ValueError):
        return None


def construir_url_qr_afip(req: GenerarComprobanteRequest) -> Optional[str]:
    """Devuelve la URL oficial de AFIP embebida en el QR."""
    json_data = _construir_json_qr_afip(req)
    if not json_data:
        return None
    # separators: AFIP acepta JSON compacto; evita espacios que agrandan el QR.
    json_string = json.dumps(json_data, separators=(",", ":"))
    base64_string = base64.b64encode(json_string.encode("utf-8")).decode("utf-8")
    return f"https://www.afip.gob.ar/fe/qr/?p={base64_string}"


def qr_url_a_lineas_ascii(url: str, ancho: int) -> list[str]:
    """
    Intenta arte ASCII del QR. El payload AFIP (~350+ chars) suele dar matrices
    de 60+ módulos: no entra en 32/42/48 columnas de ticket térmico.
    En ese caso deja marcador + URL (el escaneo real va por PNG/ESC-POS).
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

    resultado.append("(QR imagen / impresora)".center(ancho))
    return resultado


def envolver_ticket_texto_html(texto: str, qr_base64: Optional[str] = None) -> str:
    """
    Ticket monospace + QR PNG embebido.
    Pensado para formato Texto: el driver gráfico imprime el QR escaneable;
    el cuerpo sigue siendo texto de ancho fijo (comandera).
    """
    seguro = html.escape(texto)
    bloque_qr = ""
    if qr_base64:
        bloque_qr = (
            '<div class="qr-wrap">'
            f'<img src="data:image/png;base64,{qr_base64}" alt="QR AFIP" class="qr-afip" />'
            "</div>"
        )

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Comprobante</title>
  <style>
    @page {{ margin: 0; }}
    body {{ margin: 0; padding: 2mm; background: #fff; }}
    pre {{
      font-family: 'Courier New', Courier, monospace;
      font-size: 12px;
      line-height: 1.2;
      white-space: pre-wrap;
      word-break: break-word;
      margin: 0;
    }}
    .qr-wrap {{ text-align: center; margin: 4px 0; }}
    .qr-afip {{ width: 32mm; height: 32mm; image-rendering: pixelated; }}
  </style>
</head>
<body onload="window.print()">
  <pre>{seguro}</pre>
  {bloque_qr}
</body>
</html>
"""


def generar_comandos_escpos_qr(url: str, modulo_size: int = 4) -> bytes:
    """
    Secuencia ESC/POS (Epson GS ( k) para que la impresora térmica dibuje el QR.
    Útil si se imprime RAW (Generic/Text Only + puerto RAW), no vía navegador.
    """
    data = url.encode("utf-8")
    size = max(1, min(16, modulo_size))
    # Model 2
    model = b"\x1d\x28\x6b\x04\x00\x31\x41\x32\x00"
    # Module size
    module = bytes([0x1D, 0x28, 0x6B, 0x03, 0x00, 0x31, 0x43, size])
    # Error correction L
    ec = b"\x1d\x28\x6b\x03\x00\x31\x45\x30"
    store_len = len(data) + 3
    p_l = store_len & 0xFF
    p_h = (store_len >> 8) & 0xFF
    store = bytes([0x1D, 0x28, 0x6B, p_l, p_h, 0x31, 0x50, 0x30]) + data
    print_qr = b"\x1d\x28\x6b\x03\x00\x31\x51\x30"
    return model + module + ec + store + print_qr


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