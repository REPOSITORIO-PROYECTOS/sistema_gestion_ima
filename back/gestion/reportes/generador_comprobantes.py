# back/gestion/reportes/generador_comprobantes.py

import os
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
from typing import Dict, Any
from datetime import datetime # <--- 1. Importamos datetime

# --- Módulos del Proyecto ---
from back.schemas.comprobante_schemas import GenerarComprobanteRequest
from back.gestion.facturacion_afip import generar_factura_para_venta
from fastapi import HTTPException
from back.config import AFIP_CUIT

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
    Genera un comprobante a partir de los datos explícitos recibidos en la petición.
    """
    print(f"\n--- [TRACE: GENERAR COMPROBANTE STATELESS] ---")
    print(f"1. Solicitud para Emisor CUIT: {data.emisor.cuit}, Formato: {data.formato}, Tipo: {data.tipo}")

    datos_afip: Dict[str, Any] = {}
    
    if data.tipo == "factura":
        print("   -> Tipo 'factura' detectado. Llamando al especialista de AFIP...")
        try:
            datos_afip = generar_factura_para_venta(
                venta_data=data.transaccion,
                cliente_data=data.receptor
            )
            print("   -> Datos de AFIP recibidos con éxito.")
        except (ValueError, RuntimeError) as e:
            print(f"   -> ERROR: Falló la comunicación con el servicio de AFIP. Detalle: {e}")
            raise HTTPException(status_code=503, detail=f"Servicio de AFIP no disponible: {e}")
    else:
        print(f"   -> Tipo '{data.tipo}' detectado. No requiere comunicación con AFIP.")

    # --- LÓGICA DE RENDERIZADO ---
    
    ruta_plantilla = os.path.join(TEMPLATE_DIR, data.formato, f"{data.tipo}.html")
    if not os.path.exists(ruta_plantilla):
        print(f"   -> ERROR: La plantilla solicitada no existe en la ruta: {ruta_plantilla}")
        raise ValueError(f"La plantilla para el formato '{data.formato}' y tipo '{data.tipo}' no existe.")

    contexto = {
        "data": data,
        "venta": data.transaccion, # <-- La clave es añadir esto
        "afip": datos_afip,
        "AFIP_CUIT": AFIP_CUIT,
        "fecha_emision": datetime.now() 
        }
    
    try:
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        
        # --- 3. LE ENSEÑAMOS EL NUEVO FILTRO A JINJA2 ---
        # Registramos nuestra función 'format_datetime' para que se pueda usar como '| date' en la plantilla.
        env.filters['date'] = format_datetime
        
        template = env.get_template(f"{data.formato}/{data.tipo}.html")
        html_renderizado = template.render(contexto)
        print(f"2. Plantilla '{data.formato}/{data.tipo}.html' renderizada con éxito.")
    except Exception as e:
        print(f"   -> ERROR: Falló el renderizado de la plantilla Jinja2. Detalle: {e}")
        raise RuntimeError(f"Error al procesar la plantilla del comprobante: {e}")

    try:
        css_string = ""
        if data.formato == "ticket":
            css_string = "@page { size: 80mm auto; margin: 2mm; }"
        pdf_bytes = HTML(string=html_renderizado).write_pdf(stylesheets=[CSS(string=css_string)])
        print(f"3. PDF generado en memoria. Tamaño: {len(pdf_bytes)} bytes.")
    except Exception as e:
        print(f"   -> ERROR: Falló la conversión de HTML a PDF con WeasyPrint. Detalle: {e}")
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
