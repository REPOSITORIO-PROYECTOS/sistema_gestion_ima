# back/gestion/reportes/generador_comprobantes.py

import os
import traceback
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS

# --- Módulos del Proyecto ---
from back.schemas.comprobante_schemas import GenerarComprobanteRequest
# Importamos la nueva función modularizada para generar el QR
from .qr_generator import generar_qr_para_comprobante

# --- Utilidades internas ---
_MAP_TIPO_AFIP_LETRA = {
    1: 'A',    # Factura A
    6: 'B',    # Factura B
    11: 'C',   # Factura C
    3: 'A',    # Nota de Crédito A
    8: 'B',    # Nota de Crédito B
    13: 'C',   # Nota de Crédito C
    83: 'T',   # Ticket Fiscal
}
_NC_TYPES = {3, 8, 13}

def _get_attr_or_key(obj: Any, name: str, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)

def _set_attr_or_key(obj: Any, name: str, value: Any):
    if isinstance(obj, dict):
        obj[name] = value
    else:
        setattr(obj, name, value)

def _afip_build_or_enrich(transaccion, qr_base64: Optional[str]) -> Optional[Any]:
    """Asegura que el objeto AFIP contenga los campos requeridos por las plantillas.
    Deriva letra, nombre de comprobante, y agrega el QR si se generó.
    """
    afip_obj = _get_attr_or_key(transaccion, 'afip', None)
    if afip_obj is None:
        # No es un comprobante fiscal (aún) => devolvemos None y la plantilla mostrará leyenda alternativa
        if qr_base64:
            # Guardamos de todos modos por si se desea mostrar un previsual
            afip_obj = {"qr_base64": qr_base64}
        else:
            return None

    # Normalizamos a dict si es posible (si no, operamos por atributos)
    is_dict = isinstance(afip_obj, dict)
    tipo_afip = _get_attr_or_key(afip_obj, 'tipo_afip', None) or _get_attr_or_key(afip_obj, 'tipo_comprobante', None)

    # Letra
    if _get_attr_or_key(afip_obj, 'tipo_comprobante_letra', None) is None and isinstance(tipo_afip, int):
        letra = _MAP_TIPO_AFIP_LETRA.get(tipo_afip)
        if letra:
            _set_attr_or_key(afip_obj, 'tipo_comprobante_letra', letra)

    # Nombre
    if _get_attr_or_key(afip_obj, 'tipo_comprobante_nombre', None) is None:
        if isinstance(tipo_afip, int) and tipo_afip in _NC_TYPES:
            _set_attr_or_key(afip_obj, 'tipo_comprobante_nombre', 'NOTA DE CRÉDITO')
        else:
            _set_attr_or_key(afip_obj, 'tipo_comprobante_nombre', 'FACTURA')

    # QR
    if qr_base64 and not _get_attr_or_key(afip_obj, 'qr_base64', None):
        _set_attr_or_key(afip_obj, 'qr_base64', qr_base64)

    # Neto / IVA: si faltan pero tenemos total y quizá alícuota implícita 21%
    neto = _get_attr_or_key(afip_obj, 'neto', None)
    iva = _get_attr_or_key(afip_obj, 'iva', None)
    total = _get_attr_or_key(afip_obj, 'total', None) or _get_attr_or_key(transaccion, 'total', None)
    if (neto is None or iva is None) and total is not None:
        try:
            # Intento de cálculo simple para facturas con IVA 21%
            calculado_neto = round(total / 1.21, 2)
            calculado_iva = round(total - calculado_neto, 2)
            if neto is None:
                _set_attr_or_key(afip_obj, 'neto', calculado_neto)
            if iva is None:
                _set_attr_or_key(afip_obj, 'iva', calculado_iva)
        except Exception:
            pass

    return afip_obj

def _enrich_transaccion(transaccion) -> Any:
    """Rellena valores por defecto en la transacción (descuentos, listas, etc.)."""
    # Pagos
    if _get_attr_or_key(transaccion, 'pagos', None) is None:
        _set_attr_or_key(transaccion, 'pagos', [])
    # Items siempre lista
    items = _get_attr_or_key(transaccion, 'items', []) or []
    for it in items:
        if _get_attr_or_key(it, 'descuento_especifico', None) is None:
            _set_attr_or_key(it, 'descuento_especifico', 0.0)
        if _get_attr_or_key(it, 'descuento_especifico_por', None) is None:
            _set_attr_or_key(it, 'descuento_especifico_por', 0.0)
    # Subtotal fallback
    subtotal = _get_attr_or_key(transaccion, 'subtotal', None)
    total = _get_attr_or_key(transaccion, 'total', None)
    desc_general = _get_attr_or_key(transaccion, 'descuento_general', 0.0) or 0.0
    if subtotal is None and total is not None:
        try:
            calculado = total + desc_general
            _set_attr_or_key(transaccion, 'subtotal', round(calculado, 2))
        except Exception:
            pass
    return transaccion

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

    # Enriquecer transacción (defaults)
    transaccion_para_renderizar = _enrich_transaccion(transaccion_para_renderizar)

    # Construir / enriquecer AFIP
    afip_context = _afip_build_or_enrich(transaccion_para_renderizar, qr_base64_string)

    contexto = {
        "emisor": data.emisor,
        "receptor": data.receptor,
        "transaccion": transaccion_para_renderizar,
        "fecha_emision": datetime.now(),
        # Se deja qr_base64 para retrocompatibilidad, pero las plantillas nuevas usan afip.qr_base64
        "qr_base64": qr_base64_string,
        "afip": afip_context
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

    # --- PASO 4.5: Renderizar Ticket de Cambio (Opcional) ---
    html_cambio_renderizado = None
    if data.incluir_ticket_cambio:
        try:
            # Calcular fecha límite
            fecha_limite = "30 días"
            if data.plazo_cambio:
                fecha_limite = str(data.plazo_cambio)
                
                # Intentar calcular fecha exacta si es un número de días
                try:
                    dias_str = ''.join(filter(str.isdigit, fecha_limite))
                    if dias_str:
                        dias = int(dias_str)
                        fecha_limite_dt = datetime.now() + timedelta(days=dias)
                        fecha_limite = fecha_limite_dt.strftime('%d/%m/%Y')
                except Exception as e_date:
                    print(f"No se pudo calcular fecha límite exacta: {e_date}")

            # Obtener configuración de ancho (default 80mm)
            ancho_ticket = aclaraciones_de_la_empresa.get('ticket_cambio_ancho', '80mm')
            
            # Pre-calcular estilos para evitar lógica en el template (y errores de linter)
            estilos = {
                "font_size": "10px",
                "max_width": "80mm",
                "padding": "2mm",
                "page_size": "80mm auto", # auto permite largo variable
                "print_width": "76mm"
            }
            
            if ancho_ticket == '58mm':
                estilos = {
                    "font_size": "9px",
                    "max_width": "58mm",
                    "padding": "1mm",
                    "page_size": "58mm auto", # auto permite largo variable
                    "print_width": "54mm"
                }

            contexto_cambio = {
                "emisor": data.emisor,
                "receptor": data.receptor,
                "transaccion": transaccion_para_renderizar,
                "fecha_emision": datetime.now(),
                "numero": data.numero_comprobante if hasattr(data, 'numero_comprobante') else "",
                "fecha_limite_cambio": fecha_limite,
                "estilos": estilos
            }
            template_cambio = env.get_template("ticket/ticket_cambio.html")
            html_cambio_renderizado = template_cambio.render(contexto_cambio)
            print("-> Ticket de cambio renderizado con éxito.")
        except Exception as e:
            print(f"Error al renderizar ticket de cambio: {e}")
            # No fallamos todo el proceso si falla el ticket de cambio

    # --- PASO 5: Convertir a PDF ---
    try:
        css_string = ""
        if data.formato == "ticket":
            # CSS adaptable para impresoras de diferentes tamaños
            css_string = """
            @page { 
                size: 80mm auto; 
                margin: 1mm; 
            }
            @media (max-width: 60mm) {
                @page { 
                    size: 58mm auto; 
                    margin: 0.5mm; 
                }
            }
            """
        
        # Renderizar documento principal
        main_doc = HTML(string=html_renderizado).render(stylesheets=[CSS(string=css_string)])
        
        # Si hay ticket de cambio, renderizar y unir
        if html_cambio_renderizado:
            # El ticket de cambio ya tiene sus estilos completos incrustados (incluyendo @page),
            # así que no le pasamos el CSS global para evitar conflictos de tamaño.
            cambio_doc = HTML(string=html_cambio_renderizado).render()
            
            # Unir páginas (esto agrega el contenido como nuevas páginas)
            # Para tickets continuos, esto funciona bien si el driver de impresora corta al final del trabajo
            # o si el tamaño de página es variable.
            main_doc.pages.extend(cambio_doc.pages)
            
        pdf_bytes = main_doc.write_pdf()
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