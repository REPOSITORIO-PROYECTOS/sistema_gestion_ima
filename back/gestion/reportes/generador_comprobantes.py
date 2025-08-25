# back/gestion/reportes/generador_comprobantes.py

import os
import traceback
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS

# --- Módulos del Proyecto ---
from back.schemas.comprobante_schemas import GenerarComprobanteRequest
# Importamos la nueva función modularizada para generar el QR
from .qr_generator import generar_qr_para_comprobante

# --- Constantes y Configuración ---
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plantillas')

def format_datetime(value, format='%d/%m/%Y %H:%M'):
    """Filtro de Jinja2 para formatear fechas y horas de manera consistente."""
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return value
    if isinstance(value, datetime):
        return value.strftime(format)
    return value

# --- Funciones Principales de Generación de PDF ---

def generar_comprobante_stateless(data: GenerarComprobanteRequest) -> bytes:
    """
    Genera un comprobante en PDF. Ahora lee las aclaraciones legales desde los
    datos del emisor, haciéndolo 100% multi-empresa.
    """
    print(f"\n--- [TRACE: Iniciando generación de comprobante] ---")
    print(f"Tipo: {data.tipo}, Formato: {data.formato}")

    # --- PASO 1: Generar Código QR ---
    qr_base64_string = generar_qr_para_comprobante(data)
    if qr_base64_string:
        print("-> Código QR de AFIP generado con éxito.")

    # --- PASO 2: Procesar Observaciones y Aclaraciones Legales (Multi-Empresa) ---
    observaciones_usuario = data.transaccion.observaciones or ""
    
    # Obtenemos las aclaraciones de la empresa específica desde el payload
    aclaraciones_de_la_empresa = data.emisor.aclaraciones_legales or {}
    texto_legal = aclaraciones_de_la_empresa.get(data.tipo) # Busca el texto para el tipo de comprobante actual
    
    observaciones_finales = observaciones_usuario
    if texto_legal:
        if observaciones_finales:
            observaciones_finales = f"{observaciones_finales}\n\n---\n\n{texto_legal}"
        else:
            observaciones_finales = texto_legal
        print(f"-> Aclaración legal personalizada para '{data.tipo}' añadida.")

    # --- PASO 3: Preparar Contexto para la Plantilla ---
    transaccion_para_renderizar = data.transaccion.model_copy(deep=True)
    transaccion_para_renderizar.observaciones = observaciones_finales

    contexto = {
        "emisor": data.emisor,
        "receptor": data.receptor,
        "transaccion": transaccion_para_renderizar,
        "fecha_emision": datetime.now(),
        "qr_base64": qr_base64_string,
        "afip": getattr(data.transaccion, 'afip', None)
    }
    
    # --- PASO 4: Renderizar Plantilla HTML ---
    try:
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        env.filters['date'] = format_datetime
        template = env.get_template(f"{data.formato}/{data.tipo}.html")
        html_renderizado = template.render(contexto)
        print(f"-> Plantilla renderizada con éxito.")
    except Exception as e:
        print("!!!!!!!!!!!!!!!! ERROR GRAVE AL RENDERIZAR JINJA2 !!!!!!!!!!!!!!")
        traceback.print_exc()
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        raise RuntimeError(f"Error al procesar la plantilla: {e}")

    # --- PASO 5: Convertir a PDF ---
    try:
        css_string = ""
        if data.formato == "ticket":
            css_string = "@page { size: 80mm auto; margin: 2mm; }"
        pdf_bytes = HTML(string=html_renderizado).write_pdf(stylesheets=[CSS(string=css_string)])
        print(f"-> PDF generado. Tamaño: {len(pdf_bytes)} bytes.")
    except Exception as e:
        raise RuntimeError(f"Error al generar el archivo PDF: {e}")
        
    print("--- [FIN TRACE: Generación exitosa] ---\n")
    return pdf_bytes

def generar_ticket_cierre_pdf(datos: dict) -> bytes:
    """
    Genera un PDF para el ticket de cierre de lote detallado.
    (Esta función no se modifica ya que no lleva QR de AFIP).
    """
    print(f"\n--- [TRACE: GENERAR TICKET CIERRE] ---")
    
    try:
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        env.filters['date'] = format_datetime
        
        template = env.get_template("ticket/cierre_lote_detallado.html")
        
        contexto = {
            "datos": datos,
            "fecha_emision": datetime.now()
        }
        html_renderizado = template.render(contexto)
        print("1. Plantilla 'cierre_lote_detallado.html' renderizada con éxito.")
    except Exception as e:
        print(f"ERROR DETALLADO DE JINJA2: {e}")
        raise RuntimeError(f"Error al procesar la plantilla del ticket de cierre: {e}")

    try:
        css_string = "@page { size: 58mm auto; margin: 2mm; }"
        pdf_bytes = HTML(string=html_renderizado).write_pdf(stylesheets=[CSS(string=css_string)])
        print(f"2. PDF de cierre generado. Tamaño: {len(pdf_bytes)} bytes.")
    except Exception as e:
        print(f"ERROR DETALLADO DE WEASYPRINT: {e}")
        raise RuntimeError(f"Error al generar el PDF del ticket de cierre: {e}")
        
    return pdf_bytes