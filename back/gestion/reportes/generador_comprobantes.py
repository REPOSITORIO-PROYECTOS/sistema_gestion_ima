# back/gestion/reportes/generador_comprobantes.py

import os
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
from datetime import datetime # <--- 1. Importamos datetime
import traceback

# --- Módulos del Proyecto ---
from back.schemas.comprobante_schemas import GenerarComprobanteRequest


TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plantillas')

# --- 2. CREAMOS NUESTRA FUNCIÓN DE FILTRO PERSONALIZADA ---
def format_datetime(value, format='%d/%m/%Y %H:%M'):
    """
    Filtro personalizado de Jinja2 para formatear fechas y horas.
    """
    if isinstance(value, str):
        try:
            # Intenta convertir strings en formato ISO (común en JSON) a objetos datetime
            value = datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return value # Si no se puede convertir, devuelve el string original
    if isinstance(value, datetime):
        return value.strftime(format)
    return value

def generar_comprobante_stateless(data: GenerarComprobanteRequest) -> bytes:
    """
    Genera un comprobante en PDF.
    Esta función es simple: toma los datos y los renderiza en una plantilla.
    NO se comunica con AFIP ni otros servicios.
    """
    print(f"\n--- [TRACE: GENERAR COMPROBANTE SIMPLE] ---")
    print(f"1. Solicitud para generar: {data.formato}/{data.tipo}.html")

    # --- PASO 1: PREPARAR EL CONTEXTO ---
    # Creamos un contexto limpio que pasa los datos del payload directamente a la plantilla.
    # La plantilla tendrá acceso a 'emisor', 'receptor' y 'transaccion'.
    contexto = {
        "emisor": data.emisor,
        "receptor": data.receptor,
        "transaccion": data.transaccion,
        "fecha_emision": datetime.now(),
        "afip": getattr(data, 'afip', {})
    }
    
    # --- PASO 2: RENDERIZAR LA PLANTILLA ---
    try:
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        env.filters['date'] = format_datetime
        
        # Busca la plantilla dinámicamente (ej: ticket/recibo.html)
        template = env.get_template(f"{data.formato}/{data.tipo}.html")
        
        # Renderiza el HTML con los datos del contexto
        html_renderizado = template.render(contexto)
        
        print(f"2. Plantilla renderizada con éxito.")
    except Exception as e:
        # Si esto falla, el siguiente print te dirá EXACTAMENTE por qué.
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!!      ERROR GRAVE AL RENDERIZAR JINJA2     !!!")
        traceback.print_exc() # Imprime el error completo y la línea exacta
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        raise RuntimeError(f"Error al procesar la plantilla del comprobante: {e}")

    # --- PASO 3: CONVERTIR A PDF (sin cambios) ---
    try:
        css_string = ""
        if data.formato == "ticket":
            css_string = "@page { size: 80mm auto; margin: 2mm; }"
        
        pdf_bytes = HTML(string=html_renderizado).write_pdf(stylesheets=[CSS(string=css_string)])
        print(f"3. PDF generado en memoria.")
    except Exception as e:
        raise RuntimeError(f"Error al generar el archivo PDF: {e}")
        
    print("--- [FIN TRACE] ---\n")
    return pdf_bytes

def generar_ticket_cierre_pdf(datos: dict) -> bytes:
    """
    Genera un PDF para el ticket de cierre de lote detallado.
    """
    print(f"\n--- [TRACE: GENERAR TICKET CIERRE] ---")
    
    try:
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        env.filters['date'] = format_datetime # Reutilizamos tu filtro de fecha
        
        # Apunta a la plantilla correcta
        template = env.get_template("ticket/cierre_lote_detallado.html")
        
        # Añadimos la fecha de emisión al contexto aquí
        contexto = {
            "datos": datos,
            "fecha_emision": datetime.now()
        }
        html_renderizado = template.render(contexto)
        print("1. Plantilla 'cierre_lote_detallado.html' renderizada con éxito.")
    except Exception as e:
        # Imprime un error más detallado si la plantilla falla
        print(f"ERROR DETALLADO DE JINJA2: {e}")
        raise RuntimeError(f"Error al procesar la plantilla del ticket de cierre: {e}")

    try:
        # Forzamos el formato de 58mm
        css_string = "@page { size: 58mm auto; margin: 2mm; }"
        pdf_bytes = HTML(string=html_renderizado).write_pdf(stylesheets=[CSS(string=css_string)])
        print(f"2. PDF de cierre generado. Tamaño: {len(pdf_bytes)} bytes.")
    except Exception as e:
        print(f"ERROR DETALLADO DE WEASYPRINT: {e}")
        raise RuntimeError(f"Error al generar el PDF del ticket de cierre: {e}")
        
    return pdf_bytes
