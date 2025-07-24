# back/reportes/generador_comprobantes.py

import os
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
from typing import Literal

# --- Módulos del Proyecto ---
from back.modelos import Venta, VentaDetalle, Tercero, Articulo # Asegúrese de importar sus modelos

# Tipos para validación estática
TipoFormato = Literal["pdf", "ticket"]
TipoComprobante = Literal["factura", "remito", "presupuesto", "recibo"]

# Obtenemos la ruta absoluta al directorio de plantillas
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plantillas')

def generar_comprobante_venta(
    db: Session,
    id_venta: int,
    formato: TipoFormato = "pdf",
    tipo: TipoComprobante = "remito"
) -> bytes:
    """
    Genera un comprobante para una venta específica en el formato y tipo solicitados.
    
    Retorna:
        bytes: El contenido binario del archivo PDF.
    
    Lanza:
        ValueError: Si la venta no se encuentra o la plantilla no existe.
    """
    print(f"\n--- [TRACE: GENERAR COMPROBANTE] ---")
    print(f"1. Solicitud para Venta ID: {id_venta}, Formato: {formato}, Tipo: {tipo}")

    # 1. Obtener los datos completos de la venta
    consulta = (
        select(Venta)
        .where(Venta.id == id_venta)
        .options(
            selectinload(Venta.cliente),
            selectinload(Venta.detalles).selectinload(VentaDetalle.articulo)
        )
    )
    venta_db = db.exec(consulta).first()

    if not venta_db:
        raise ValueError(f"Venta con ID {id_venta} no encontrada.")

    print(f"2. Venta encontrada. Cliente: {venta_db.cliente.nombre_razon_social if venta_db.cliente else 'N/A'}")

    # 2. Construir la ruta a la plantilla correcta
    ruta_plantilla = os.path.join(TEMPLATE_DIR, formato, f"{tipo}.html")
    if not os.path.exists(ruta_plantilla):
        raise ValueError(f"La plantilla para el formato '{formato}' y tipo '{tipo}' no existe.")

    # 3. Lógica específica por tipo de comprobante
    # Aquí es donde se maneja la lógica de AFIP en el futuro
    datos_extra = {}
    if tipo == "factura":
        print("   -> Lógica de Factura: Obteniendo datos de AFIP (simulación)...")
        # Aquí iría la llamada a la API de AFIP para obtener CAE, Vto, etc.
        # Por ahora, usamos datos de ejemplo.
        datos_extra = {
            "cae": "12345678901234",
            "vencimiento_cae": "30/07/2025",
            "tipo_factura": "B" # O "A", según la condición de IVA del cliente y la empresa
        }

    # 4. Renderizar la plantilla HTML
    # Le decimos a Jinja2 que busque en el directorio raíz de plantillas
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template(f"{formato}/{tipo}.html") # Cargamos la plantilla correcta
    
    # Pasamos los datos de la venta y cualquier dato extra (como los de AFIP)
    html_renderizado = template.render(venta=venta_db, extra=datos_extra)
    print(f"3. Plantilla '{formato}/{tipo}.html' renderizada con éxito.")

    # 5. Convertir a PDF
    # Definimos estilos base según el formato
    css_string = ""
    if formato == "ticket":
        # WeasyPrint por defecto usa medidas para impresión. 80mm es estándar para tickets.
        css_string = "@page { size: 80mm auto; margin: 2mm; }"
    
    pdf_en_memoria = HTML(string=html_renderizado).write_pdf(stylesheets=[CSS(string=css_string)])
    
    print(f"4. PDF generado en memoria. Tamaño: {len(pdf_en_memoria)} bytes.")
    print("--- [FIN TRACE] ---\n")
    
    return pdf_en_memoria