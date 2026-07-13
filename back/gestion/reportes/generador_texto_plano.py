# back/gestion/reportes/generador_texto_plano.py

from datetime import datetime, timedelta
from typing import Any, Optional

from back.gestion.reportes.qr_generator import construir_url_qr_afip, qr_url_a_lineas_ascii
from back.schemas.comprobante_schemas import GenerarComprobanteRequest
from back.gestion.reportes.generador_comprobantes import (
    TIPOS_TICKET_TERMICO,
    _afip_build_or_enrich,
    _enrich_transaccion,
    _estilos_impresora_termica,
    _get_attr_or_key,
    _resolver_ancho_impresora,
    _ticket_line,
    _wrap_ticket_text,
    format_datetime,
)

FORMATOS_TEXTO_PLANO = frozenset({"texto", "texto_plano", "txt", "plain", "text"})

_MAP_COD_AFIP = {1: "001", 6: "006"}


def es_formato_texto_plano(formato: Optional[str]) -> bool:
    if not formato:
        return False
    return formato.strip().lower() in FORMATOS_TEXTO_PLANO


class TicketTextoBuilder:
    """Arma tickets en texto plano con ancho fijo (estilo comandera)."""

    def __init__(self, ancho: int) -> None:
        self.ancho = ancho
        self._lineas: list[str] = []

    def separador(self, caracter: str = "-") -> "TicketTextoBuilder":
        self._lineas.append(caracter * self.ancho)
        return self

    def vacio(self) -> "TicketTextoBuilder":
        self._lineas.append("")
        return self

    def centrado(self, texto: str) -> "TicketTextoBuilder":
        for linea in _wrap_ticket_text(texto, self.ancho):
            self._lineas.append(linea.center(self.ancho))
        return self

    def linea(self, texto: str) -> "TicketTextoBuilder":
        for linea in _wrap_ticket_text(texto, self.ancho):
            self._lineas.append(linea)
        return self

    def par(self, izquierda: str, derecha: str) -> "TicketTextoBuilder":
        self._lineas.append(_ticket_line(izquierda, derecha, self.ancho))
        return self

    def qr_ascii(self, url_qr: Optional[str]) -> "TicketTextoBuilder":
        if not url_qr:
            return self
        self._lineas.extend(qr_url_a_lineas_ascii(url_qr, self.ancho))
        return self

    def build(self) -> str:
        return "\n".join(self._lineas).rstrip() + "\n"


def _codigo_afip(afip: Any) -> str:
    tipo_afip = _get_attr_or_key(afip, "tipo_afip") or _get_attr_or_key(afip, "tipo_comprobante_afip")
    if isinstance(tipo_afip, int):
        return _MAP_COD_AFIP.get(tipo_afip, "083")
    return "083"


def _vencimiento_cae(afip: Any) -> str:
    return (
        _get_attr_or_key(afip, "vencimiento_cae")
        or _get_attr_or_key(afip, "fecha_vencimiento_cae")
        or "S/D"
    )


def generar_recibo_texto_plano(
    emisor: Any,
    receptor: Any,
    transaccion: Any,
    fecha_emision: datetime,
    afip: Any,
    ancho: int,
) -> str:
    ticket = TicketTextoBuilder(ancho)

    ticket.centrado(_get_attr_or_key(emisor, "razon_social") or "")
    ticket.centrado(f"CUIT: {_get_attr_or_key(emisor, 'cuit') or ''}")
    domicilio = _get_attr_or_key(emisor, "domicilio")
    if domicilio:
        ticket.centrado(str(domicilio))

    ticket.separador()
    ticket.centrado("RECIBO DE PAGO")
    if (
        afip
        and str(_get_attr_or_key(afip, "tipo_comprobante_nombre") or "").upper() == "ANULACION"
    ):
        ticket.centrado("*** ANULADO ***")
    ticket.separador()

    ticket.linea(f"Fecha: {format_datetime(fecha_emision)}")
    ticket.linea(f"Cliente: {_get_attr_or_key(receptor, 'nombre_razon_social') or 'Consumidor Final'}")
    ticket.linea(f"CUIT/DNI: {_get_attr_or_key(receptor, 'cuit_o_dni') or 'S/D'}")
    ticket.separador()

    items = _get_attr_or_key(transaccion, "items") or []
    for item in items:
        cantidad = _get_attr_or_key(item, "cantidad") or 0
        precio = _get_attr_or_key(item, "precio_unitario") or 0
        subtotal = cantidad * precio
        ticket.par(str(_get_attr_or_key(item, "descripcion") or ""), f"${subtotal:.2f}")
        ticket.linea(f"  {cantidad} x ${precio:.2f}")

        desc = _get_attr_or_key(item, "descuento_especifico") or 0
        desc_por = _get_attr_or_key(item, "descuento_especifico_por") or 0
        if desc > 0:
            etiqueta = "Desc."
            if desc_por > 0:
                etiqueta += f" ({desc_por:.0f}%)"
            ticket.par(etiqueta, f"-${desc:.2f}")

    ticket.separador()
    desc_general = _get_attr_or_key(transaccion, "descuento_general") or 0
    total = _get_attr_or_key(transaccion, "total") or 0
    ticket.par("SUBTOTAL:", f"${total + desc_general:.2f}")

    desc_gral_por = _get_attr_or_key(transaccion, "descuento_general_por") or 0
    if desc_general > 0:
        etiqueta = "DESC. GRAL."
        if desc_gral_por > 0:
            etiqueta += f" ({desc_gral_por:.0f}%)"
        ticket.par(etiqueta, f"-${desc_general:.2f}")

    ticket.par("TOTAL:", f"${total:.2f}")

    observaciones = _get_attr_or_key(transaccion, "observaciones")
    if observaciones:
        ticket.separador()
        ticket.linea("Observaciones:")
        ticket.linea(str(observaciones))

    ticket.separador()
    ticket.centrado("COMPROBANTE NO VALIDO")
    ticket.centrado("COMO FACTURA")
    ticket.separador()
    ticket.centrado("Firma y Aclaracion")

    return ticket.build()


def generar_factura_texto_plano(
    emisor: Any,
    receptor: Any,
    transaccion: Any,
    fecha_emision: datetime,
    afip: Any,
    ancho: int,
    qr_url: Optional[str] = None,
) -> str:
    ticket = TicketTextoBuilder(ancho)

    ticket.centrado(_get_attr_or_key(emisor, "razon_social") or "")
    domicilio = _get_attr_or_key(emisor, "domicilio")
    if domicilio:
        ticket.centrado(str(domicilio))
    ticket.centrado(f"CUIT: {_get_attr_or_key(emisor, 'cuit') or ''}")

    iibb = _get_attr_or_key(emisor, "ingresos_brutos")
    if iibb:
        ticket.centrado(f"IIBB: {iibb}")
    inicio = _get_attr_or_key(emisor, "inicio_actividades")
    if inicio:
        ticket.centrado(f"Inicio Act.: {inicio}")
    cond_iva = _get_attr_or_key(emisor, "condicion_iva")
    if cond_iva:
        ticket.centrado(f"IVA: {cond_iva}")

    ticket.separador()
    if (
        afip
        and str(_get_attr_or_key(afip, "tipo_comprobante_nombre") or "").upper() == "ANULACION"
    ):
        ticket.centrado("*** ANULADO ***")

    tipo_nombre = _get_attr_or_key(afip, "tipo_comprobante_nombre") or "FACTURA"
    tipo_letra = _get_attr_or_key(afip, "tipo_comprobante_letra") or "B"
    numero = _get_attr_or_key(afip, "numero_comprobante") or 0
    punto_venta = _get_attr_or_key(emisor, "punto_venta") or 0

    ticket.par(str(tipo_nombre), str(tipo_letra))
    ticket.centrado(f"Cod. {_codigo_afip(afip)}")
    ticket.centrado(f"P.Venta: {punto_venta:05d} - N: {numero:08d}")
    ticket.centrado(f"Fecha: {format_datetime(fecha_emision)}")
    ticket.separador()

    ticket.linea(f"Cliente: {_get_attr_or_key(receptor, 'nombre_razon_social') or 'Consumidor Final'}")
    ticket.linea(f"CUIT/DNI: {_get_attr_or_key(receptor, 'cuit_o_dni') or 'S/D'}")
    ticket.linea(f"IVA: {_get_attr_or_key(receptor, 'condicion_iva') or 'Consumidor Final'}")
    domicilio_receptor = _get_attr_or_key(receptor, "domicilio")
    if domicilio_receptor:
        ticket.linea(f"Domicilio: {domicilio_receptor}")
    ticket.separador()

    items = _get_attr_or_key(transaccion, "items") or []
    for item in items:
        cantidad = _get_attr_or_key(item, "cantidad") or 0
        precio = _get_attr_or_key(item, "precio_unitario") or 0
        subtotal = cantidad * precio
        descripcion = _get_attr_or_key(item, "descripcion") or ""
        ticket.par(f"{cantidad}x {descripcion}", f"${subtotal:.2f}")
        ticket.linea(f"  P/U: ${precio:.2f}")

        desc = _get_attr_or_key(item, "descuento_especifico") or 0
        desc_por = _get_attr_or_key(item, "descuento_especifico_por") or 0
        if desc > 0:
            etiqueta = "Desc."
            if desc_por > 0:
                etiqueta += f" ({desc_por:.0f}%)"
            ticket.par(etiqueta, f"-${desc:.2f}")

    ticket.separador()
    desc_general = _get_attr_or_key(transaccion, "descuento_general") or 0
    subtotal_tx = _get_attr_or_key(transaccion, "subtotal")
    total = _get_attr_or_key(transaccion, "total") or 0
    if subtotal_tx is None:
        subtotal_tx = total + desc_general
    ticket.par("Subtotal", f"${subtotal_tx:.2f}")

    desc_gral_por = _get_attr_or_key(transaccion, "descuento_general_por") or 0
    if desc_general > 0:
        etiqueta = "Desc. Gral."
        if desc_gral_por > 0:
            etiqueta += f" ({desc_gral_por:.0f}%)"
        ticket.par(etiqueta, f"-${desc_general:.2f}")

    neto = _get_attr_or_key(afip, "neto") if afip else None
    iva = _get_attr_or_key(afip, "iva") if afip else None
    if neto is not None and iva is not None:
        ticket.par("Neto Gravado", f"${neto:.2f}")
        ticket.par("IVA (21%)", f"${iva:.2f}")

    ticket.par("TOTAL", f"${total:.2f}")

    pagos = _get_attr_or_key(transaccion, "pagos") or []
    if pagos:
        ticket.separador()
        ticket.linea("Forma de Pago:")
        for pago in pagos:
            forma = _get_attr_or_key(pago, "forma_pago") or "Pago"
            monto = _get_attr_or_key(pago, "monto") or 0
            ticket.par(str(forma), f"${monto:.2f}")

    observaciones = _get_attr_or_key(transaccion, "observaciones")
    if observaciones and "---" in str(observaciones):
        membrete, notas = str(observaciones).split("---", 1)
        ticket.separador()
        ticket.centrado(membrete.strip())
        if notas.strip():
            ticket.linea(notas.strip())
    elif observaciones:
        ticket.separador()
        ticket.linea(str(observaciones))

    ticket.separador()
    cae = _get_attr_or_key(afip, "cae") if afip else None
    if cae:
        ticket.centrado(f"CAE N: {cae}")
        ticket.centrado(f"Vto. CAE: {_vencimiento_cae(afip)}")
        ticket.qr_ascii(qr_url)
        ticket.centrado("Comprobante Autorizado")
    else:
        ticket.centrado("Documento no valido como factura")

    ticket.centrado("Defensa del Consumidor")
    ticket.centrado("0800-333-6634")
    ticket.centrado("Regimen de Transparencia Fiscal")
    ticket.centrado("Ley 27.743")

    return ticket.build()


def _generar_ticket_cambio_texto_plano(
    emisor: Any,
    receptor: Any,
    transaccion: Any,
    fecha_emision: datetime,
    numero: str,
    fecha_limite: str,
    ancho: int,
) -> str:
    ticket = TicketTextoBuilder(ancho)
    ticket.separador()
    ticket.centrado(_get_attr_or_key(emisor, "razon_social") or "")
    ticket.centrado("TICKET DE CAMBIO")
    ticket.centrado(f"Fecha: {format_datetime(fecha_emision, '%d/%m/%Y %H:%M')}")
    if numero:
        ticket.centrado(f"Ref: {numero}")
    ticket.separador()

    nombre_cliente = _get_attr_or_key(receptor, "nombre_razon_social")
    if nombre_cliente:
        ticket.linea(f"Cliente: {nombre_cliente}")

    items = _get_attr_or_key(transaccion, "items") or []
    for item in items:
        cantidad = _get_attr_or_key(item, "cantidad") or 0
        descripcion = _get_attr_or_key(item, "descripcion") or ""
        ticket.par(f"{cantidad}x", descripcion)

    ticket.separador()
    ticket.centrado("CAMBIO VALIDO HASTA:")
    ticket.centrado(str(fecha_limite))
    ticket.separador()
    ticket.centrado("Presentar este ticket y el producto")
    ticket.centrado("en perfectas condiciones.")
    return ticket.build()


def generar_comprobante_texto_plano(data: GenerarComprobanteRequest) -> bytes:
    """Genera recibo/factura/comprobante como texto plano UTF-8 para impresoras RAW."""
    from back.gestion.reportes.qr_generator import generar_qr_para_comprobante

    aclaraciones = data.emisor.aclaraciones_legales or {}
    ancho = int(_estilos_impresora_termica(_resolver_ancho_impresora(aclaraciones))["chars_per_line"])

    qr_base64 = generar_qr_para_comprobante(data)
    qr_url = construir_url_qr_afip(data)

    observaciones_usuario = data.transaccion.observaciones or ""
    texto_legal = aclaraciones.get(data.tipo)
    observaciones_finales = observaciones_usuario
    if texto_legal:
        observaciones_finales = (
            f"{observaciones_usuario}\n\n---\n\n{texto_legal}"
            if observaciones_usuario
            else texto_legal
        )

    transaccion = data.transaccion.model_copy(deep=True)
    transaccion.observaciones = observaciones_finales
    transaccion = _enrich_transaccion(transaccion)
    afip = _afip_build_or_enrich(transaccion, qr_base64)
    fecha_emision = datetime.now()

    tipo = data.tipo.lower()
    if tipo == "recibo":
        contenido = generar_recibo_texto_plano(
            data.emisor, data.receptor, transaccion, fecha_emision, afip, ancho
        )
    elif tipo in {"factura", "comprobante"}:
        contenido = generar_factura_texto_plano(
            data.emisor, data.receptor, transaccion, fecha_emision, afip, ancho, qr_url
        )
    else:
        raise ValueError(
            f"Texto plano no soportado para tipo '{data.tipo}'. "
            f"Use: {', '.join(sorted(TIPOS_TICKET_TERMICO))}."
        )

    if data.incluir_ticket_cambio:
        fecha_limite = str(data.plazo_cambio or "30 dias")
        try:
            dias_str = "".join(filter(str.isdigit, fecha_limite))
            if dias_str:
                fecha_limite = (datetime.now() + timedelta(days=int(dias_str))).strftime("%d/%m/%Y")
        except Exception:
            pass
        numero = getattr(data, "numero_comprobante", "") or ""
        contenido += "\n" + _generar_ticket_cambio_texto_plano(
            data.emisor,
            data.receptor,
            transaccion,
            fecha_emision,
            str(numero),
            fecha_limite,
            ancho,
        )

    return contenido.encode("utf-8")
