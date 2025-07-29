# back/reportes/generador_comprobantes.py
# VERSIÓN FINAL Y COMPLETA - ORQUESTADOR DE COMPROBANTES

import os
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
from typing import Dict, Any

# --- Módulos del Proyecto ---
from back.schemas.comprobante_schemas import GenerarComprobanteRequest
# Importamos el especialista de AFIP refactorizado
from back.gestion.facturacion_afip import generar_factura_para_venta
# Importamos la excepción correcta de FastAPI
from fastapi import HTTPException
# Importamos el CUIT de la empresa desde la config para pasarlo a las plantillas
from back.config import AFIP_CUIT

# Definimos la ruta al directorio de plantillas de forma robusta
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plantillas')

def generar_comprobante_stateless(data: GenerarComprobanteRequest) -> bytes:
    """
    Genera un comprobante a partir de los datos explícitos recibidos en la petición.
    Actúa como un orquestador: prepara los datos, llama a servicios externos
    (como AFIP) solo si es necesario, y renderiza la plantilla correcta.
    """
    print(f"\n--- [TRACE: GENERAR COMPROBANTE STATELESS] ---")
    print(f"1. Solicitud para Emisor CUIT: {data.emisor.cuit}, Formato: {data.formato}, Tipo: {data.tipo}")

    datos_afip: Dict[str, Any] = {}
    
    # --- LÓGICA DE DECISIÓN PRINCIPAL ---
    # Verificamos si el tipo de comprobante requiere intervención de AFIP.
    if data.tipo == "factura":
        print("   -> Tipo 'factura' detectado. Llamando al especialista de AFIP...")
        try:
            # Llamamos a la función especialista, pasándole los datos correctos del payload.
            # La función 'generar_factura_para_venta' ahora espera los schemas.
            datos_afip = generar_factura_para_venta(
                venta_data=data.transaccion,
                cliente_data=data.receptor
            )
            print("   -> Datos de AFIP recibidos con éxito.")
        
        except (ValueError, RuntimeError) as e:
            # Si el especialista de AFIP falla (ej: credenciales malas, servicio caído),
            # propagamos el error de una forma que el router pueda entender.
            print(f"   -> ERROR: Falló la comunicación con el servicio de AFIP. Detalle: {e}")
            raise HTTPException(status_code=503, detail=f"Servicio de AFIP no disponible: {e}")
    
    else:
        # Para 'remito', 'presupuesto', 'recibo', etc., no hacemos nada especial.
        print(f"   -> Tipo '{data.tipo}' detectado. No requiere comunicación con AFIP.")

    # --- LÓGICA DE RENDERIZADO ---
    
    # 2. Verificar que la plantilla para la combinación solicitada exista
    ruta_plantilla = os.path.join(TEMPLATE_DIR, data.formato, f"{data.tipo}.html")
    if not os.path.exists(ruta_plantilla):
        print(f"   -> ERROR: La plantilla solicitada no existe en la ruta: {ruta_plantilla}")
        raise ValueError(f"La plantilla para el formato '{data.formato}' y tipo '{data.tipo}' no existe.")

    # 3. Preparar el contexto de datos para la plantilla
    contexto = {
        "data": data,         # El objeto completo de la petición (emisor, receptor, transaccion)
        "afip": datos_afip,   # El diccionario con los datos de AFIP (estará vacío si no es una factura)
        "AFIP_CUIT": AFIP_CUIT  # Pasamos el CUIT de la empresa para mostrarlo si es necesario
    }
    
    # 4. Cargar y renderizar la plantilla HTML con los datos
    try:
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        template = env.get_template(f"{data.formato}/{data.tipo}.html")
        html_renderizado = template.render(contexto)
        print(f"2. Plantilla '{data.formato}/{data.tipo}.html' renderizada con éxito.")
    except Exception as e:
        print(f"   -> ERROR: Falló el renderizado de la plantilla Jinja2. Detalle: {e}")
        raise RuntimeError(f"Error al procesar la plantilla del comprobante: {e}")

    # 5. Convertir el HTML a PDF, aplicando estilos específicos para el formato
    try:
        css_string = ""
        if data.formato == "ticket":
            # Estilos para forzar el tamaño de una impresora térmica de 80mm
            css_string = "@page { size: 80mm auto; margin: 2mm; }"

        pdf_bytes = HTML(string=html_renderizado).write_pdf(stylesheets=[CSS(string=css_string)])
        print(f"3. PDF generado en memoria. Tamaño: {len(pdf_bytes)} bytes.")
    except Exception as e:
        print(f"   -> ERROR: Falló la conversión de HTML a PDF con WeasyPrint. Detalle: {e}")
        raise RuntimeError(f"Error al generar el archivo PDF: {e}")
        
    print("--- [FIN TRACE] ---\n")
    
    return pdf_bytes