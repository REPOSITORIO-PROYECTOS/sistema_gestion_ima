# back/gestion/facturacion_afip.py

import os
import requests
from dotenv import load_dotenv
from typing import Dict, Any, Optional
from sqlmodel import Session # <-- PASO 1: Importar Session
from datetime import datetime

from enum import Enum
# --- Importaciones de la aplicación ---
from back.cliente_boveda import ClienteBoveda
from back.schemas.comprobante_schemas import TransaccionData, ReceptorData, EmisorData
from typing import Dict, Any
from back.modelos import Venta

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
        # --- LÓGICA CORREGIDA ---
        # Para un RI, el IVA se calcula siempre. La única diferencia es el tipo de comprobante.
        neto = round(total / (1 + TASA_IVA_21), 2)
        iva = round(total - neto, 2)
        
        if condicion_receptor == CondicionIVA.RESPONSABLE_INSCRIPTO:
            # Si el receptor es RI, es Factura A
            return {"tipo_afip": 1, "neto": neto, "iva": iva}
        else:
            # Si el receptor es CF, Monotributista, etc., es Factura B
            return {"tipo_afip": 6, "neto": neto, "iva": iva}

    elif condicion_emisor in [CondicionIVA.MONOTRIBUTO, CondicionIVA.EXENTO]:
        # La lógica para Factura C está bien
        return {"tipo_afip": 11, "neto": total, "iva": 0.0}
    else:
        raise ValueError(f"Condición de IVA del emisor no soportada: {condicion_emisor.name}")


# --- FUNCIÓN PRINCIPAL COMPLETA (ADAPTADA PARA STRINGS) ---

def generar_factura_para_venta(
    db: Session,
    venta_a_facturar: Venta,
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
    print(f"LLAS CREDENCIALES QUE ESTOY ENVIANDO SON : {credenciales}")
    print(f"LOS DATOS QUE LE ESTOY ENVIANDO A FACTURAR SON : {datos_factura}")

    payload = {
        "credenciales": credenciales,
        "datos_factura": datos_factura,
    }
    


    print(f"Enviando petición al microservicio de facturación en: {FACTURACION_API_URL}")
    try:
        response = requests.post(
            FACTURACION_API_URL,
            json=payload,
            timeout=20,
        )
        
        response.raise_for_status() 
        
        resultado_afip = response.json()
        print(f"Respuesta exitosa del microservicio de facturación: {resultado_afip}")
        if resultado_afip.get("cae"):
            
            # 1. Obtenemos la venta de la base de datos
            venta_a_actualizar = db.get(Venta, venta_a_facturar.id)
            if not venta_a_actualizar:
                print(f"ERROR: No se encontró la Venta con ID {venta_a_facturar.id} para actualizar.")
                # Aunque no se guarde, devolvemos el resultado para no romper el flujo
                return resultado_afip

            # 2. Construimos el diccionario completo que se guardará
            datos_completos_para_guardar = {
                "estado": "EXITOSO",
                "resultado": resultado_afip.get("resultado", "A"),
                "cae": resultado_afip.get("cae"),
                "vencimiento_cae": resultado_afip.get("vencimiento_cae"),
                "numero_comprobante": resultado_afip.get("numero_comprobante"),
                "punto_venta": datos_factura.get("punto_venta"),
                "tipo_comprobante": datos_factura.get("tipo_afip"),
                "fecha_comprobante": datetime.now().strftime('%Y-%m-%d'),
                "importe_total": total,
                "cuit_emisor": int(emisor_data.cuit),
                "tipo_doc_receptor": datos_factura.get("tipo_documento"),
                "nro_doc_receptor": int(datos_factura.get("documento")),
                "tipo_documento": datos_factura.get("tipo_documento"),
                "documento": datos_factura.get("documento"),
                "tipo_afip": datos_factura.get("tipo_afip"),
                "total": total,
                "neto": datos_factura.get("neto"),
                "iva": datos_factura.get("iva"),
                "id_condicion_iva": datos_factura.get("id_condicion_iva")
            }
            
            # 3. Asignamos el diccionario al campo JSON y actualizamos el estado
            venta_a_actualizar.datos_factura = datos_completos_para_guardar
            venta_a_actualizar.facturada = True
            
            db.add(venta_a_actualizar)
            db.commit()
            db.refresh(venta_a_actualizar)
            
            print(f"Venta ID: {venta_a_facturar.id} actualizada correctamente en la base de datos.")
        
        # 4. Devolvemos el resultado original del microservicio, como antes
            return datos_completos_para_guardar
        else:
            # Si el estado no es exitoso, lanzamos un error
            error_msg = resultado_afip.get('errores') or resultado_afip.get('error', 'Error desconocido de AFIP.')
            raise RuntimeError(f"AFIP devolvió un error: {error_msg}")

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
    


# --- NUEVA FUNCIÓN PARA NOTAS DE CRÉDITO ---
def determinar_tipo_nota_credito(
    condicion_emisor: CondicionIVA,
    condicion_receptor: CondicionIVA,
) -> int:
    """
    Determina el código AFIP para el tipo de Nota de Crédito (A, B, o C).
    """
    if condicion_emisor == CondicionIVA.RESPONSABLE_INSCRIPTO:
        if condicion_receptor == CondicionIVA.RESPONSABLE_INSCRIPTO:
            return 3  # Nota de Crédito A
        else:
            return 8  # Nota de Crédito B
    elif condicion_emisor in [CondicionIVA.MONOTRIBUTO, CondicionIVA.EXENTO]:
        return 13 # Nota de Crédito C
    else:
        raise ValueError(f"Condición de IVA del emisor no soportada: {condicion_emisor.name}")

def generar_nota_credito_para_venta(
    total: float,
    cliente_data: Optional[ReceptorData],
    emisor_data: EmisorData,
    comprobante_asociado: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Genera una Nota de Crédito en AFIP, referenciando a una factura original.
    Esta función es independiente y no modifica la de generar facturas.
    """
    print(f"Iniciando proceso de NOTA DE CRÉDITO para Emisor CUIT: {emisor_data.cuit}")

    # --- PASO 1: Obtener Credenciales (Lógica Reutilizada) ---
    try:
        secreto_emisor = cliente_boveda.obtener_secreto(emisor_data.cuit)
        if not secreto_emisor:
            raise ValueError(f"No se encontraron credenciales en la bóveda para el CUIT {emisor_data.cuit}.")
        credenciales = {
            "cuit": emisor_data.cuit,
            "certificado": secreto_emisor.certificado,
            "clave_privada": secreto_emisor.clave_privada
        }
    except Exception as e:
        raise RuntimeError(f"El servicio de bóveda no está disponible: {e}")

    # --- PASO 2: Preparar Datos del Comprobante (Lógica Adaptada) ---
    try:
        cond_emisor_str = emisor_data.condicion_iva.upper().replace(' ', '_')
        condicion_emisor = CondicionIVA[cond_emisor_str]
    except (KeyError, AttributeError):
        raise ValueError(f"La condición de IVA del emisor '{emisor_data.condicion_iva}' no es válida.")

    if cliente_data and cliente_data.cuit_o_dni and cliente_data.cuit_o_dni != "0":
        documento = cliente_data.cuit_o_dni
        tipo_documento_receptor = TipoDocumento.CUIT if len(documento) == 11 else TipoDocumento.DNI
        try:
            cond_receptor_str = cliente_data.condicion_iva.upper().replace(' ', '_')
            condicion_receptor = CondicionIVA[cond_receptor_str]
        except (KeyError, AttributeError):
            condicion_receptor = CondicionIVA.CONSUMIDOR_FINAL
    else: 
        documento = "0"
        tipo_documento_receptor = TipoDocumento.CONSUMIDOR_FINAL
        condicion_receptor = CondicionIVA.CONSUMIDOR_FINAL
    
    # --- CAMBIO CLAVE 1: Determinar el tipo de NC ---
    tipo_nota_credito = determinar_tipo_nota_credito(
        condicion_emisor=condicion_emisor,
        condicion_receptor=condicion_receptor,
    )
    
    # La lógica de neto/iva es la misma que para una factura
    neto, iva = (round(total / (1 + TASA_IVA_21), 2), round(total - (total / (1 + TASA_IVA_21)), 2)) if condicion_emisor == CondicionIVA.RESPONSABLE_INSCRIPTO else (total, 0.0)

    datos_nota_credito = {
        "tipo_afip": tipo_nota_credito,
        "punto_venta": emisor_data.punto_venta,
        "tipo_documento": tipo_documento_receptor.value,
        "documento": documento,
        "total": total,
        "neto": neto,
        "iva": iva,
        # --- CAMBIO CLAVE 2: Añadir la referencia a la factura original ---
        "comprobantes_asociados": [
            {
                "tipo": comprobante_asociado.get("tipo_afip"),
                "punto_venta": comprobante_asociado.get("punto_venta"),
                "numero": comprobante_asociado.get("numero_comprobante")
            }
        ]
    }
    
    payload = {
        "credenciales": credenciales,
        "datos_factura": datos_nota_credito, # El microservicio espera este nombre de clave
    }

    # --- PASO 3: Enviar al Microservicio (Lógica Reutilizada) ---
    print(f"Enviando petición de Nota de Crédito al microservicio...")
    try:
        response = requests.post(
            FACTURACION_API_URL,
            json=payload,
            timeout=20,
        )
        response.raise_for_status() 
        return response.json()
    except requests.exceptions.HTTPError as e:
        error_detalle = e.response.json().get('detail', e.response.text) if e.response else str(e)
        raise RuntimeError(f"Error en el servicio de facturación: {error_detalle}")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"El servicio de facturación no está disponible: {e}")