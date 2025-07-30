# back/gestion/facturacion_afip.py

import requests
from typing import Dict, Any, Optional
from back.schemas.comprobante_schemas import TransaccionData, ReceptorData, EmisorData

def generar_factura_para_venta(
    venta_data: TransaccionData,
    cliente_data: Optional[ReceptorData],
    emisor_data: EmisorData
) -> Dict[str, Any]:
    """
    Prepara los datos y llama al microservicio de facturación.
    Esta función es ahora "agnóstica": no sabe si la petición viene de
    una venta única o de un lote, solo recibe los datos que necesita.
    """
    print(f"Iniciando proceso de facturación para Emisor CUIT: {emisor_data.cuit}")

    # --- CAMBIO 1: LAS CREDENCIALES AHORA VIENEN EN EL PAYLOAD ---
    # El orquestador (caja_router o facturacion_lotes_manager) es responsable
    # de obtener estas credenciales (desde la Bóveda) y pasarlas aquí.
    credenciales = {
        "cuit": emisor_data.cuit,
        "certificado": emisor_data.afip_certificado.replace('\\n', '\n') if emisor_data.afip_certificado else None,
        "clave_privada": emisor_data.afip_clave_privada.replace('\\n', '\n') if emisor_data.afip_clave_privada else None
    }
    
    if not all(credenciales.values()):
        raise ValueError("Faltan credenciales de AFIP en los datos del emisor.")

    # --- CAMBIO 2: LOS DATOS SE OBTIENEN DE LOS SCHEMAS, NO DE LOS MODELOS ---
    if cliente_data:
        tipo_documento = 80 if cliente_data.cuit_o_dni and len(cliente_data.cuit_o_dni) == 11 else 96
        documento = cliente_data.cuit_o_dni if cliente_data.cuit_o_dni else "0"
        # La condición de IVA del cliente también viene en el schema
        id_condicion_iva_receptor = 5 # Aquí iría tu lógica para mapear texto a ID, ej: "Consumidor Final" -> 5
    else: # Venta a "Consumidor Final" genérico
        tipo_documento = 99
        documento = "0"
        id_condicion_iva_receptor = 5
        
    datos_factura = {
        "tipo_afip": 11,  # Factura C (Monotributo)
        "punto_venta": emisor_data.punto_venta, # El punto de venta del emisor
        "tipo_documento": tipo_documento,
        "documento": documento,
        "total": venta_data.total, # El total viene de TransaccionData
        "id_condicion_iva": id_condicion_iva_receptor,
        "neto": 0.0,
        "iva": 0.0,
        # Aquí podrías añadir un detalle de los items si tu microservicio lo requiere
        # "items": [item.model_dump() for item in venta_data.items]
    }

    # El resto del código permanece igual, ya que es la lógica de comunicación
    payload = {
        "credenciales": credenciales,
        "datos_factura": datos_factura
    }

    try:
        # Asumimos que la URL del microservicio viene del emisor_data o de un config global
        # from back.config import FACTURACION_API_URL
        # response = requests.post(FACTURACION_API_URL, json=payload, ...)
        
        # Simulación para el ejemplo
        print(f"SIMULACIÓN: Enviando petición al microservicio de facturación con total: {datos_factura['total']}")
        resultado_afip = {"cae": "SIMULADO_123456789", "comprobante_numero": "0001-00001234", "vencimiento_cae": "2025-12-31"}
        print(f"Respuesta simulada del microservicio: {resultado_afip}")
        return resultado_afip

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"El servicio de facturación no está disponible: {e}")
    except Exception as e:
        raise RuntimeError(f"Error inesperado durante la facturación: {e}")