# back/gestion/facturacion_afip.py

import os
import requests
from dotenv import load_dotenv
from typing import Dict, Any, Optional

from enum import Enum
# --- Importaciones de la aplicación ---
from back.cliente_boveda import ClienteBoveda
from back.schemas.comprobante_schemas import TransaccionData, ReceptorData, EmisorData
from typing import Dict, Any


TASA_IVA_21 = 0.21
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


class CondicionIVA(Enum):
    RESPONSABLE_INSCRIPTO = 1
    EXENTO = 4
    CONSUMIDOR_FINAL = 5
    MONOTRIBUTO = 6
    NO_CATEGORIZADO = 7

class TipoDocumento(Enum):
    CUIT = 80
    CUIL = 86
    DNI = 96
    CONSUMIDOR_FINAL = 99




def determinar_datos_factura_segun_iva(
    condicion_emisor: CondicionIVA,
    condicion_receptor: CondicionIVA,
    total: float
) -> Dict[str, Any]:
    if condicion_emisor == CondicionIVA.RESPONSABLE_INSCRIPTO:
        if condicion_receptor == CondicionIVA.RESPONSABLE_INSCRIPTO:
            neto = round(total / (1 + TASA_IVA_21), 2)
            iva = round(total - neto, 2)
            return {"tipo_afip": 1, "neto": neto, "iva": iva}
        else:
            return {"tipo_afip": 6, "neto": total, "iva": 0.0}
    elif condicion_emisor in [CondicionIVA.MONOTRIBUTO, CondicionIVA.EXENTO]:
        return {"tipo_afip": 11, "neto": total, "iva": 0.0}
    else:
        raise ValueError(f"Condición de IVA del emisor no soportada: {condicion_emisor.name}")

# --- FUNCIÓN PRINCIPAL COMPLETA (ADAPTADA PARA STRINGS) ---

def generar_factura_para_venta(
    total: float,
    cliente_data: Optional[ReceptorData],
    emisor_data: EmisorData
) -> Dict[str, Any]:
    
    print(f"Iniciando proceso de facturación para Emisor CUIT: {emisor_data.cuit}")

    print(f"Obteniendo credenciales para el CUIT {emisor_data.cuit} desde la bóveda...")
    try:
        # Asumimos que estas clases y funciones existen en tu código
        # secreto_emisor = cliente_boveda.obtener_secreto(emisor_data.cuit)
        # if not secreto_emisor:
        #     raise ValueError(f"No se encontraron credenciales en la bóveda para el CUIT {emisor_data.cuit}.")
        secreto_emisor = cliente_boveda.obtener_secreto(emisor_data.cuit)
        if not secreto_emisor:
            # Error de negocio: el emisor no tiene credenciales cargadas.
            raise ValueError(f"No se encontraron credenciales en la bóveda para el CUIT {emisor_data.cuit}.")
        print("Credenciales obtenidas con éxito de la bóveda (simulado).")
        
        credenciales = {
            "cuit": emisor_data.cuit,
            "certificado": secreto_emisor.certificado,
            "clave_privada": secreto_emisor.clave_privada
        }

    except (ConnectionError, PermissionError) as e:
        print(f"ERROR CRÍTICO: No se pudo conectar a la bóveda. Detalle: {e}")
        raise RuntimeError(f"El servicio de bóveda de secretos no está disponible o la API Key es incorrecta.")
    
    print("Preparando datos de la factura con lógica dinámica...")

    try:
        # Normalizamos el string: a mayúsculas y reemplazamos espacios por guiones bajos
        cond_emisor_str = emisor_data.condicion_iva.upper().replace(' ', '_')
        condicion_emisor = CondicionIVA[cond_emisor_str]
    except (KeyError, AttributeError):
        raise ValueError(f"La condición de IVA del emisor '{emisor_data.condicion_iva}' no es válida o no está soportada.")

    if cliente_data and cliente_data.cuit_o_dni and cliente_data.cuit_o_dni != "0":
        documento = cliente_data.cuit_o_dni
        tipo_documento_receptor = TipoDocumento.CUIT if len(documento) == 11 else TipoDocumento.DNI
        try:
            cond_receptor_str = cliente_data.condicion_iva.upper().replace(' ', '_')
            condicion_receptor = CondicionIVA[cond_receptor_str]
        except (KeyError, AttributeError):
             raise ValueError(f"La condición de IVA del receptor '{cliente_data.condicion_iva}' no es válida o no está soportada.")
    else: 
        documento = "0"
        tipo_documento_receptor = TipoDocumento.CONSUMIDOR_FINAL
        condicion_receptor = CondicionIVA.CONSUMIDOR_FINAL
        
    print(f"Emisor: {condicion_emisor.name}, Receptor: {condicion_receptor.name}, Total: {total}")

    logica_factura = determinar_datos_factura_segun_iva(
        condicion_emisor=condicion_emisor,
        condicion_receptor=condicion_receptor,
        total=total
    )
    print(f"Lógica determinada: {logica_factura}")

    datos_factura = {
        "tipo_afip": logica_factura["tipo_afip"],
        "punto_venta": emisor_data.punto_venta,
        "tipo_documento": tipo_documento_receptor.value,
        "documento": documento,
        "total": total,
        "id_condicion_iva": condicion_receptor.value,
        "neto": logica_factura["neto"],
        "iva": logica_factura["iva"],
    }

    payload = {
        "credenciales": credenciales,
        "datos_factura": datos_factura
    }
    


    print(f"Enviando petición al microservicio de facturación en: {FACTURACION_API_URL}")
    try:
        response = requests.post(
            FACTURACION_API_URL,
            json=payload,
            timeout=20
        )
        
        response.raise_for_status() 
        
        resultado_afip = response.json()
        print(f"Respuesta exitosa del microservicio de facturación: {resultado_afip}")
        return resultado_afip

    except requests.exceptions.HTTPError as e:
        error_detalle = "Sin detalles adicionales"
        try:
            # Intenta obtener un JSON del cuerpo de la respuesta de error
            error_detalle = e.response.json().get('detail', e.response.text)
        except requests.exceptions.JSONDecodeError:
            error_detalle = e.response.text

        print(f"ERROR: El microservicio de facturación rechazó la petición. Status: {e.response.status_code}. Detalle: {error_detalle}")
        raise RuntimeError(f"Error en el servicio de facturación: {error_detalle}")

    except requests.exceptions.RequestException as e:
        print(f"ERROR: No se pudo conectar con el microservicio de facturación. Detalle: {e}")
        raise RuntimeError("El servicio de facturación no está disponible en este momento.")
    
    except Exception as e:
        print(f"ERROR: Ocurrió un error inesperado durante la facturación. Detalle: {e}")
        raise RuntimeError(f"Error inesperado durante la facturación: {e}")