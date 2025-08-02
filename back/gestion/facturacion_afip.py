# back/gestion/facturacion_afip.py

import os
import requests
from dotenv import load_dotenv
from typing import Dict, Any, Optional

# --- Importaciones de la aplicación ---
from back.cliente_boveda import ClienteBoveda
from back.schemas.comprobante_schemas import TransaccionData, ReceptorData, EmisorData

# --- Carga de Configuración ---
# Carga las variables desde el archivo .env.ima ubicado en el directorio padre 'back'
DOTENV_IMA_PATH = os.path.join(os.path.dirname(__file__), '..', '.env.ima')
load_dotenv(dotenv_path=DOTENV_IMA_PATH)

# Configuración para la Bóveda de Secretos
BOVEDA_URL = os.getenv("BOVEDA_URL")
BOVEDA_API_KEY = os.getenv("BOVEDA_API_KEY_INTERNA")

# Configuración para el Microservicio de Facturación Real
FACTURACION_API_URL = os.getenv("FACTURACION_API_URL")

# Verificación de configuración crítica al iniciar la aplicación
if not all([BOVEDA_URL, BOVEDA_API_KEY, FACTURACION_API_URL]):
    raise SystemExit(
        "ERROR CRÍTICO: Faltan una o más variables de entorno requeridas: "
        "BOVEDA_URL, BOVEDA_API_KEY_INTERNA, FACTURACION_API_URL."
    )

# --- Instanciación de Clientes ---
# Se crea una única instancia del cliente de la bóveda para ser reutilizada
cliente_boveda = ClienteBoveda(base_url=BOVEDA_URL, api_key=BOVEDA_API_KEY)


def generar_factura_para_venta(
    venta_data: TransaccionData,
    cliente_data: Optional[ReceptorData],
    emisor_data: EmisorData
) -> Dict[str, Any]:
    """
    Orquesta el proceso de facturación:
    1. Obtiene las credenciales del emisor de forma segura desde la Bóveda.
    2. Prepara los datos de la factura.
    3. Llama al microservicio de facturación externo con toda la información.
    """
    print(f"Iniciando proceso de facturación para Emisor CUIT: {emisor_data.cuit}")

    # --- PASO 1: OBTENER CREDENCIALES DINÁMICAS DESDE LA BÓVEDA ---
    print(f"Obteniendo credenciales para el CUIT {emisor_data.cuit} desde la bóveda...")
    try:
        secreto_emisor = cliente_boveda.obtener_secreto(emisor_data.cuit)
        if not secreto_emisor:
            # Error de negocio: el emisor no tiene credenciales cargadas.
            raise ValueError(f"No se encontraron credenciales en la bóveda para el CUIT {emisor_data.cuit}.")
            
        print("Credenciales obtenidas con éxito de la bóveda.")
        
        # Construir el diccionario de credenciales para el microservicio de facturación.
        credenciales = {
            "cuit": emisor_data.cuit,
            "certificado": secreto_emisor.certificado,
            "clave_privada": secreto_emisor.clave_privada
        }

    except (ConnectionError, PermissionError) as e:
        # Error de infraestructura: no se puede comunicar con la bóveda.
        print(f"ERROR CRÍTICO: No se pudo conectar a la bóveda. Detalle: {e}")
        raise RuntimeError(f"El servicio de bóveda de secretos no está disponible o la API Key es incorrecta.")
    
    # --- PASO 2: PREPARAR DATOS DE LA FACTURA ---
    if cliente_data and cliente_data.cuit_o_dni:
        tipo_documento = 80 if len(cliente_data.cuit_o_dni) == 11 else 96
        documento = cliente_data.cuit_o_dni
        # Aquí puedes añadir una lógica más compleja para determinar la condición de IVA del receptor
        id_condicion_iva_receptor = 5 # Asumimos Consumidor Final
    else: 
        # Venta a "Consumidor Final" genérico sin datos.
        tipo_documento = 99
        documento = "0"
        id_condicion_iva_receptor = 5
        
    datos_factura = {
        "tipo_afip": 11,  # Factura C (Monotributo). Ajustar si es necesario.
        "punto_venta": emisor_data.punto_venta,
        "tipo_documento": tipo_documento,
        "documento": documento,
        "total": venta_data.total,
        "id_condicion_iva": id_condicion_iva_receptor,
        "neto": 0.0,
        "iva": 0.0,
    }

    # --- PASO 3: LLAMAR AL MICROSERVICIO DE FACTURACIÓN REAL ---
    payload = {
        "credenciales": credenciales,
        "datos_factura": datos_factura
    }

    print(f"Enviando petición al microservicio de facturación en: {FACTURACION_API_URL}")
    try:
        response = requests.post(
            FACTURACION_API_URL,
            json=payload,
            timeout=20  # Es una buena práctica tener un timeout.
        )
        
        # Esto lanzará una excepción para respuestas de error (4xx, 5xx)
        # permitiendo capturar errores de validación del microservicio de facturación.
        response.raise_for_status() 
        
        resultado_afip = response.json()
        print(f"Respuesta exitosa del microservicio de facturación: {resultado_afip}")
        return resultado_afip

    except requests.exceptions.HTTPError as e:
        # Error específico de la API de facturación (ej: 422 Unprocessable Entity)
        error_detalle = e.response.json().get('detail', e.response.text)
        print(f"ERROR: El microservicio de facturación rechazó la petición. Status: {e.response.status_code}. Detalle: {error_detalle}")
        raise RuntimeError(f"Error en el servicio de facturación: {error_detalle}")

    except requests.exceptions.RequestException as e:
        # Error de red (no se pudo conectar, timeout, etc.)
        print(f"ERROR: No se pudo conectar con el microservicio de facturación. Detalle: {e}")
        raise RuntimeError("El servicio de facturación no está disponible en este momento.")
    
    except Exception as e:
        # Cualquier otro error inesperado
        print(f"ERROR: Ocurrió un error inesperado durante la facturación. Detalle: {e}")
        raise RuntimeError(f"Error inesperado durante la facturación: {e}")