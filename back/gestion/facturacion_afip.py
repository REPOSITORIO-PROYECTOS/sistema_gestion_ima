# back/gestion/facturacion_afip.py
import requests
from typing import Dict, Any
from back.config import AFIP_CERT,AFIP_KEY,FACTURACION_API_URL,AFIP_CUIT
from back.modelos import Venta, Tercero # Importa los modelos que necesites

def generar_factura_para_venta(venta: Venta, cliente: Tercero) -> Dict[str, Any]:
    """
    Prepara los datos y llama al microservicio de facturación para una venta dada.
    """
    print(f"Iniciando proceso de facturación para la Venta ID: {venta.id}")

    # 1. Preparar las credenciales
    credenciales = {
        "cuit": AFIP_CUIT,
        "certificado": AFIP_CERT.replace('\\n', '\n') if AFIP_CERT else None,
        "clave_privada": AFIP_KEY.replace('\\n', '\n') if AFIP_KEY else None
    }
    
    if not all(credenciales.values()):
        raise ValueError("Faltan credenciales de AFIP en la configuración del servidor (.env)")

    # 2. Preparar los datos de la factura
    # Esta lógica puede ser mucho más compleja, dependiendo del tipo de cliente, etc.
    # Aquí un ejemplo simple para Monotributista (Factura C) a Consumidor Final
    if cliente:
        tipo_documento = 80 if cliente.cuit else 96 # CUIT o DNI
        documento = cliente.cuit if cliente.cuit else "0" # DNI si lo tienes, o 0
        id_condicion_iva = 5 # Asumimos Consumidor Final por ahora
    else: # Venta sin cliente (mostrador)
        tipo_documento = 99
        documento = "0"
        id_condicion_iva = 5
        
    datos_factura = {
        "tipo_afip": 11,  # Factura C (Monotributo)
        "punto_venta": 1, # DEBE ser el punto de venta habilitado para Web Service
        "tipo_documento": tipo_documento,
        "documento": documento,
        "total": venta.total,
        "id_condicion_iva": id_condicion_iva,
        "neto": 0.0, # Para Factura C, esto se ajusta en el microservicio
        "iva": 0.0,
    }

    # 3. Construir el payload completo
    payload = {
        "credenciales": credenciales,
        "datos_factura": datos_factura
    }

    # 4. Llamar al microservicio
    try:
        print(f"Enviando petición a: {FACTURACION_API_URL}")
        response = requests.post(
            FACTURACION_API_URL,
            json=payload,
            timeout=20  # Timeout de 20 segundos
        )
        
        # Lanza una excepción si la respuesta es un error HTTP (4xx o 5xx)
        response.raise_for_status() 
        
        resultado_afip = response.json()
        print(f"Respuesta exitosa del microservicio: {resultado_afip}")
        return resultado_afip

    except requests.exceptions.RequestException as e:
        print(f"ERROR: No se pudo conectar con el microservicio de facturación. Detalle: {e}")
        # Aquí puedes decidir qué hacer: ¿fallar la venta, o guardarla como "pendiente de facturar"?
        # Por ahora, lanzamos el error para que el frontend se entere.
        raise RuntimeError("El servicio de facturación no está disponible en este momento.")
    except Exception as e:
        print(f"ERROR: Ocurrió un error inesperado durante la facturación. Detalle: {e}")
        raise RuntimeError(str(e))