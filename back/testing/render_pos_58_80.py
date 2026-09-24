"""Genera PDFs de muestra POS 58mm y 80mm en Downloads."""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader
from pypdf import PdfReader
from weasyprint import CSS, HTML

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from back.gestion.reportes.generador_comprobantes import (  # noqa: E402
    _css_comprobante_termico,
    _estilos_impresora_termica,
    _ticket_line,
    _wrap_ticket_text,
    format_datetime,
)

TEMPLATE_DIR = ROOT / "back" / "gestion" / "reportes" / "plantillas"
OUT_DIR = Path.home() / "Downloads"


def _ctx() -> dict:
    emisor = SimpleNamespace(
        razon_social="KIOSCO RIVADAVIA",
        domicilio="Gral. Paz 2149 Este",
        condicion_iva="MONOTRIBUTO",
        cuit="20434852529",
        ingresos_brutos="20434852529",
        inicio_actividades="01/07/2026",
        punto_venta=2,
        logo_url=None,
    )
    receptor = SimpleNamespace(
        nombre_razon_social="Consumidor Final",
        cuit_o_dni="0",
        condicion_iva="Consumidor Final",
        domicilio="Sin especificar",
    )
    items = [
        SimpleNamespace(
            cantidad=1.0,
            descripcion="PANIFICACION",
            precio_unitario=12000.00,
            descuento_especifico=0.0,
            descuento_especifico_por=0.0,
        )
    ]
    transaccion = SimpleNamespace(
        items=items,
        subtotal=12000.0,
        descuento_general=0.0,
        descuento_general_por=0.0,
        total=12000.0,
        observaciones=None,
        pagos=[{"forma_pago": "Débito", "monto": 12000.0}],
    )
    afip = SimpleNamespace(
        tipo_comprobante_letra="B",
        tipo_comprobante_nombre="FACTURA",
        tipo_afip=83,
        numero_comprobante=39,
        cae="76123456789012",
        vencimiento_cae="03/10/2026",
        fecha_vencimiento_cae="03/10/2026",
        neto=9917.36,
        iva=2082.64,
        qr_base64=None,
    )
    return {
        "emisor": emisor,
        "receptor": receptor,
        "transaccion": transaccion,
        "afip": afip,
        "fecha_emision": datetime(
            2026, 7, 30, 16, 30, tzinfo=ZoneInfo("America/Argentina/Buenos_Aires")
        ),
    }


def main() -> None:
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    env.filters["date"] = format_datetime
    env.filters["wrap_ticket"] = _wrap_ticket_text
    env.filters["ticket_line"] = _ticket_line
    base = _ctx()

    for ancho in ("80mm", "58mm"):
        estilos = _estilos_impresora_termica(ancho)
        html = env.get_template("ticket/factura.html").render(**base, estilos=estilos)
        out = OUT_DIR / f"comprobante_pos_{ancho}.pdf"
        out.write_bytes(
            HTML(string=html).write_pdf(
                stylesheets=[CSS(string=_css_comprobante_termico(estilos))]
            )
        )
        page = PdfReader(str(out)).pages[0]
        w = float(page.mediabox.width) * 25.4 / 72
        h = float(page.mediabox.height) * 25.4 / 72
        print(
            f"{ancho}: {w:.2f}x{h:.2f} mm | "
            f"@page {estilos['page_size']} margin {estilos['page_margin']} "
            f"font {estilos['font_size']} -> {out}"
        )


if __name__ == "__main__":
    main()
