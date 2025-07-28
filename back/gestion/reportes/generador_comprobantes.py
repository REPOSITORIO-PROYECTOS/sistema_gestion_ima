# back/reportes/generador_comprobantes.py
# VERSIÓN MULTI-EMPRESA

from http.client import HTTPException
import os
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS

# --- Módulos del Proyecto ---
# Ya no necesitamos los modelos de la DB para esta función
from back.schemas.comprobante_schemas import GenerarComprobanteRequest
# Seguimos usando el especialista de AFIP
from back.gestion.facturacion_afip import generar_factura_para_venta # Asumimos un nuevo nombre

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plantillas')

def generar_comprobante_stateless(data: GenerarComprobanteRequest) -> bytes:
    """
    Genera un comprobante a partir de los datos explícitos recibidos en la petición.
    Es "stateless" porque no depende de la base de datos interna.
    """
    print(f"\n--- [TRACE: GENERAR COMPROBANTE STATELESS] ---")
    print(f"1. Solicitud para Emisor CUIT: {data.emisor.cuit}, Formato: {data.formato}, Tipo: {data.tipo}")

    datos_afip = {}
    if data.tipo == "factura":
        print("   -> Tipo 'factura' detectado. Llamando al especialista de AFIP...")
        try:
            # Pasamos los datos del emisor y la transacción al especialista
            datos_afip = generar_factura_para_venta(emisor=data.emisor, receptor=data.receptor, transaccion=data.transaccion)
            print("   -> Datos de AFIP recibidos con éxito.")
        except (ValueError, RuntimeError) as e:
            raise HTTPException(status_code=503, detail=f"Servicio de AFIP no disponible: {e}")
            
    ruta_plantilla = os.path.join(TEMPLATE_DIR, data.formato, f"{data.tipo}.html")
    if not os.path.exists(ruta_plantilla):
        raise ValueError(f"La plantilla para '{data.formato}/{data.tipo}.html' no existe.")

    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template(f"{data.formato}/{data.tipo}.html")
    
    # El contexto para la plantilla ahora es el propio objeto 'data'
    html_renderizado = template.render(data=data, afip=datos_afip)
    print(f"2. Plantilla renderizada con éxito.")
    
    css_string = ""
    if data.formato == "ticket":
        css_string = "@page { size: 80mm auto; margin: 2mm; }"

    pdf_bytes = HTML(string=html_renderizado).write_pdf(stylesheets=[CSS(string=css_string)])
    print(f"3. PDF generado en memoria.")
    print("--- [FIN TRACE] ---\n")
    
    return pdf_bytes