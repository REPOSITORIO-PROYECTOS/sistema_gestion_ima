# back/gestion/facturacion_afip.py

import os
import requests
from dotenv import load_dotenv
from typing import Dict, Any, Optional
from sqlmodel import Session # <-- PASO 1: Importar Session
from datetime import datetime

from enum import Enum
# --- Importaciones de la aplicación ---
from back import config
from back.cliente_boveda import ClienteBoveda
from back.schemas.comprobante_schemas import TransaccionData, ReceptorData, EmisorData
from typing import Dict, Any
from back.modelos import Venta

TASA_IVA_21 = 0.21

# Configuración para la Bóveda de Secretos
BOVEDA_URL = config.URL_BOVEDA
BOVEDA_API_KEY = config.API_KEY_INTERNA

# Configuración para el Microservicio de Facturación Real
FACTURACION_API_URL = config.FACTURACION_API_URL

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


def determinar_logica_comprobante(
    condicion_emisor: CondicionIVA,
    condicion_receptor: CondicionIVA,
    total: float,
    formato: str = "pdf",  # Nuevo parámetro para determinar si es ticket
    receptor_tiene_cuit: bool = False,
    tipo_solicitado: Optional[str] = None,
    TASA_IVA_21: float = 0.21
) -> Dict[str, Any]:
    # Normalizar formato
    if isinstance(formato, str):
        formato_norm = formato.strip().lower()
    else:
        formato_norm = str(formato)

    # Si es formato ticket, siempre es código 83 (Ticket Fiscal)
    if formato_norm == "ticket":
        neto = round(total / (1 + TASA_IVA_21), 2)
        iva = round(total - neto, 2)
        return {"tipo_afip": 83, "neto": neto, "iva": iva}
    # --- MAPEOS RÁPIDOS (Aceptar strings como 'factura_a', 'factura b', 'a', 'b', etc.) ---
    TIPO_AFIP_MAP = {
        # Facturas
        'factura_a': 1, 'facturaa': 1, 'a': 1,
        'factura_b': 6, 'facturab': 6, 'b': 6,
        'factura_c': 11, 'facturac': 11, 'c': 11,
        # Variantes con espacios/guiones
        'factura b': 6, 'factura c': 11, 'factura a': 1,
        'nota_credito_a': 3, 'nota_credito_b': 8, 'nota_credito_c': 13,
        'nota-de-credito-a': 3, 'nota-de-credito-b': 8, 'nota-de-credito-c': 13,
        'nota credito a': 3,
        'nota_debito_a': 2, 'nota_debito_b': 7, 'nota_debito_c': 12,
        'nota-de-debito-a': 2, 'nota-de-debito-b': 7, 'nota-de-debito-c': 12,
        'nota debito a': 2,
        # Ticket fiscal common alias
        'ticket': 83, 't': 83
    }

    if tipo_solicitado:
        key = tipo_solicitado.strip().lower().replace('-', '_')
        # Normalize spaces to underscores as well
        key = '_'.join(key.split())

        # Handle a generic "factura" request: decide A/B based on receptor identification
        if key == 'factura':
            # Monotributo/Exento del emisor siempre -> C (11)
            if condicion_emisor in [CondicionIVA.MONOTRIBUTO, CondicionIVA.EXENTO]:
                return {"tipo_afip": 11, "neto": total, "iva": 0.0}
            # Para RI: si receptor tiene CUIT => A (1), si no => B (6)
            if condicion_emisor == CondicionIVA.RESPONSABLE_INSCRIPTO:
                if receptor_tiene_cuit:
                    neto = round(total / (1 + TASA_IVA_21), 2)
                    iva = round(total - neto, 2)
                    return {"tipo_afip": 1, "neto": neto, "iva": iva}
                else:
                    neto = round(total / (1 + TASA_IVA_21), 2)
                    iva = round(total - neto, 2)
                    return {"tipo_afip": 6, "neto": neto, "iva": iva}

        if key in TIPO_AFIP_MAP:
            tipo_map = TIPO_AFIP_MAP[key]
            # Business rule: if someone requests Factura A but receptor lacks CUIT, downgrade to B
            if tipo_map == 1 and not receptor_tiene_cuit and condicion_emisor == CondicionIVA.RESPONSABLE_INSCRIPTO:
                tipo_map = 6
            # Monotributo/Exento should map to 11 regardless
            if condicion_emisor in [CondicionIVA.MONOTRIBUTO, CondicionIVA.EXENTO]:
                tipo_map = 11

            if tipo_map == 11:
                return {"tipo_afip": 11, "neto": total, "iva": 0.0}
            else:
                neto = round(total / (1 + TASA_IVA_21), 2)
                iva = round(total - neto, 2)
                return {"tipo_afip": tipo_map, "neto": neto, "iva": iva}
    
    if condicion_emisor == CondicionIVA.RESPONSABLE_INSCRIPTO:
        # --- LÓGICA CORREGIDA ---
        # Para un RI, el IVA se calcula siempre. La única diferencia es el tipo de comprobante.
        neto = round(total / (1 + TASA_IVA_21), 2)
        iva = round(total - neto, 2)
        # Reglas solicitadas por el negocio:
        # - Si el receptor tiene CUIT (identificado), emitir Factura A (1).
        # - Si el receptor no tiene CUIT (consumidor final sin identificación), emitir Factura B (6).
        # - Mantener Monotributo/Exento -> Factura C (11) en su propia rama más abajo.
        if receptor_tiene_cuit:
            return {"tipo_afip": 1, "neto": neto, "iva": iva}
        else:
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
    emisor_data: EmisorData,
    formato_comprobante: str = "pdf",
    tipo_solicitado: Optional[str] = None
) -> Dict[str, Any]:
    
    print(f"Iniciando proceso de facturación para Emisor CUIT: {emisor_data.cuit}")

    # --- Verificación de URL de facturación ---
    if not FACTURACION_API_URL:
        raise ValueError("La URL del microservicio de facturación (FACTURACION_API_URL) no está configurada.")

    # Ya no obtenemos credenciales manualmente, delegamos al servicio de facturación
    # que las obtendrá de la bóveda usando el CUIT emisor.
    
    print("Preparando datos de la factura con lógica dinámica...")

    try:
        if not emisor_data.condicion_iva:
            raise ValueError("La condición de IVA del emisor es obligatoria.")
        cond_emisor_str = emisor_data.condicion_iva.upper().replace(' ', '_')
        condicion_emisor = CondicionIVA[cond_emisor_str]
    except (KeyError, AttributeError):
        raise ValueError(f"La condición de IVA del emisor '{emisor_data.condicion_iva}' no es válida o no está soportada.")

    nombre_receptor = "Consumidor Final"
    domicilio_receptor = "-"
    condicion_iva_receptor_str = "CONSUMIDOR_FINAL"

    if cliente_data and cliente_data.cuit_o_dni and cliente_data.cuit_o_dni != "0":
        documento = cliente_data.cuit_o_dni
        tipo_documento_receptor = TipoDocumento.CUIT if len(documento) == 11 else TipoDocumento.DNI
        nombre_receptor = getattr(cliente_data, "nombre", "Cliente") or "Cliente"
        domicilio_receptor = getattr(cliente_data, "domicilio", "-") or "-"
        
        try:
            if not cliente_data.condicion_iva:
                raise ValueError("La condición de IVA del receptor es obligatoria para clientes identificados.")
            cond_receptor_str = cliente_data.condicion_iva.upper().replace(' ', '_')
            condicion_receptor = CondicionIVA[cond_receptor_str]
            condicion_iva_receptor_str = cliente_data.condicion_iva # Usamos el string original o mapeado según convenga
        except (KeyError, AttributeError):
             raise ValueError(f"La condición de IVA del receptor '{cliente_data.condicion_iva}' no es válida o no está soportada.")
    else: 
        documento = "0"
        tipo_documento_receptor = TipoDocumento.CONSUMIDOR_FINAL
        condicion_receptor = CondicionIVA.CONSUMIDOR_FINAL
        
    print(f"Emisor: {condicion_emisor.name}, Receptor: {condicion_receptor.name}, Total: {total}")

    # Obtener credenciales si no vienen en el emisor_data
    cert = getattr(emisor_data, "afip_certificado", None)
    clave = getattr(emisor_data, "afip_clave_privada", None)
    if not cert or not clave:
        try:
            secreto_emisor = cliente_boveda.obtener_secreto(emisor_data.cuit)
            if not secreto_emisor:
                raise ValueError(f"No se encontraron credenciales en la bóveda para el CUIT {emisor_data.cuit}.")
            cert = secreto_emisor.certificado
            clave = secreto_emisor.clave_privada
        except Exception as e:
            raise RuntimeError(f"El servicio de bóveda no está disponible: {e}")

    # Decide si el receptor está identificado con CUIT (longitud 11 en documento)
    receptor_tiene_cuit = False
    try:
        if cliente_data and cliente_data.cuit_o_dni and cliente_data.cuit_o_dni != "0":
            receptor_tiene_cuit = len(str(cliente_data.cuit_o_dni)) == 11
    except Exception:
        receptor_tiene_cuit = False

    # Normalizar formato localmente (usado por la lógica de fallback)
    formato_norm = formato_comprobante.strip().lower() if isinstance(formato_comprobante, str) else str(formato_comprobante)

    logica_factura = determinar_logica_comprobante(
        condicion_emisor=condicion_emisor,
        condicion_receptor=condicion_receptor,
        total=total,
        formato=formato_comprobante,
        receptor_tiene_cuit=receptor_tiene_cuit,
        tipo_solicitado=tipo_solicitado
    )
    print(f"Lógica determinada: {logica_factura}")

    # Estructuramos datos_factura según guía del microservicio (objeto, no lista)
    datos_factura = {
        "tipo_afip": logica_factura["tipo_afip"],
        "punto_venta": emisor_data.punto_venta,
        "tipo_documento": tipo_documento_receptor.value,
        "documento": str(documento),
        "total": total,
        "neto": logica_factura.get("neto", total),
        "iva": logica_factura.get("iva", 0.0),
        "id_condicion_iva": getattr(condicion_receptor, "value", None)
    }

    payload = {
        "credenciales": {
            "cuit": str(emisor_data.cuit),
                "certificado": cert,
                "clave_privada": clave
        },
        "datos_factura": datos_factura,
    }
    
    print(f"Enviando petición al microservicio de facturación en: {FACTURACION_API_URL}")
    
    # Sistema de reintentos para errores SSL de AFIP
    max_intentos = 3
    tiempo_espera = [2, 5, 10]  # Espera progresiva entre reintentos
    # Flag para intentar un fallback cuando AFIP rechaza el tipo de comprobante (CbteTipo no habilitado)
    fallback_intentado = False
    
    for intento in range(max_intentos):
        try:
            print(f"Intento {intento + 1} de {max_intentos}")
            
            # --- AUTH: Enviamos API Key interna para autenticación ---
            headers = {
                "X-API-KEY": BOVEDA_API_KEY, # Reutilizamos la misma key interna
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                FACTURACION_API_URL,
                json=payload,
                headers=headers,
                timeout=30,  # Aumentamos timeout
            )
        
            response.raise_for_status() 
            
            # La respuesta puede ser dict o lista; normalizamos a dict
            resultados = response.json()
            if isinstance(resultados, list):
                if not resultados:
                    raise ValueError("Respuesta vacía del servicio de facturación")
                resultado_afip = resultados[0]
            elif isinstance(resultados, dict):
                resultado_afip = resultados
            else:
                raise ValueError("Formato de respuesta de facturación no reconocido")

            print(f"SERVICIO EXTERNO - Respuesta exitosa del microservicio de facturación: {resultado_afip}")
            print(f"SERVICIO EXTERNO - Campos recibidos: {list(resultado_afip.keys())}")
            
            if resultado_afip.get("cae"):
                print(f"SERVICIO EXTERNO - CAE obtenido: {resultado_afip.get('cae')}")
                
                # 1. Obtenemos la venta de la base de datos
                venta_a_actualizar = db.get(Venta, venta_a_facturar.id) if venta_a_facturar.id else None
                
                if not venta_a_actualizar:
                    print(f"ADVERTENCIA: No se encontró la Venta con ID {getattr(venta_a_facturar, 'id', 'TEMPORAL')} para actualizar en BD.")
                    print("SERVICIO EXTERNO - Construyendo respuesta sin actualizar BD...")
                    
                    # Construimos el diccionario completo sin actualizar BD
                    datos_completos_para_guardar = {
                        "estado": "EXITOSO",
                        "resultado": resultado_afip.get("resultado", "A"),
                        "cae": resultado_afip.get("cae"),
                        "vencimiento_cae": resultado_afip.get("vencimiento_cae"),
                        "numero_comprobante": resultado_afip.get("numero_comprobante"),
                        "qr_base64": resultado_afip.get("qr_base64"),
                        "punto_venta": datos_factura.get("punto_venta"),
                        "tipo_comprobante": datos_factura.get("tipo_afip"),
                        "fecha_comprobante": datetime.now().strftime('%Y-%m-%d'),
                        "importe_total": total,
                        "cuit_emisor": int(emisor_data.cuit),
                        "tipo_doc_receptor": datos_factura.get("tipo_documento"),
                        "nro_doc_receptor": int(datos_factura.get("documento") or 0),
                        "documento": datos_factura.get("documento"),
                        "tipo_afip": datos_factura.get("tipo_afip"),
                        "total": total,
                        "neto": datos_factura.get("neto"),
                        "iva": datos_factura.get("iva"),
                        "id_condicion_iva": datos_factura.get("id_condicion_iva")
                    }
                    print(f"SERVICIO EXTERNO - Respuesta construida: {datos_completos_para_guardar}")
                    return datos_completos_para_guardar

                # 2. Construimos el diccionario completo que se guardará
                datos_completos_para_guardar = {
                    "estado": "EXITOSO",
                    "resultado": resultado_afip.get("resultado", "A"),
                    "cae": resultado_afip.get("cae"),
                    "vencimiento_cae": resultado_afip.get("vencimiento_cae"),
                    "numero_comprobante": resultado_afip.get("numero_comprobante"),
                    "qr_base64": resultado_afip.get("qr_base64"), # <-- PASO 2: Guardar el QR
                    "punto_venta": datos_factura.get("punto_venta"),
                    "tipo_comprobante": datos_factura.get("tipo_afip"),
                    "fecha_comprobante": datetime.now().strftime('%Y-%m-%d'),
                    "importe_total": total,
                    "cuit_emisor": int(emisor_data.cuit),
                    "tipo_doc_receptor": datos_factura.get("tipo_documento"),
                    "nro_doc_receptor": int(datos_factura.get("documento") or 0),
                    # --- Unificamos para consistencia ---
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
            
                # 4. Devolvemos el resultado construido
                print(f"SERVICIO EXTERNO - Devolviendo respuesta final: {datos_completos_para_guardar}")
                return datos_completos_para_guardar
            else:
                # Si el estado no es exitoso, lanzamos un error
                error_msg = resultado_afip.get('errores') or resultado_afip.get('error', 'Error desconocido de AFIP.')
                raise RuntimeError(f"AFIP devolvió un error: {error_msg}")

        except requests.exceptions.HTTPError as e:
            error_detalle = "Sin detalles adicionales"
            try:
                # Intenta obtener un JSON del cuerpo de la respuesta de error
                error_response = e.response.json()
                error_detalle = error_response.get('message', error_response.get('detail', e.response.text))
                
                # Manejo específico para errores SSL/conexión de AFIP
                if any(err in str(error_detalle) for err in ["ssl.SSLError", "Connection reset by peer", "TypeError: 'ssl.SSLError' object is not subscriptable"]):
                    if intento < max_intentos - 1:  # Si no es el último intento
                        print(f"Error SSL detectado. Esperando {tiempo_espera[intento]} segundos antes del siguiente intento...")
                        import time
                        time.sleep(tiempo_espera[intento])
                        continue  # Continuar con el siguiente intento
                    else:
                        error_detalle = "Error de conexión SSL con AFIP. Los servidores de AFIP pueden estar temporalmente no disponibles. Se agotaron los reintentos."
                # Manejo específico para rechazo por tipo de comprobante no habilitado (ej: 10007 / CbteTipo)
                # A veces la respuesta viene en HTML/texto (500) en lugar de JSON, así que también comprobamos e.response.text
                error_texto = e.response.text if e.response is not None else ''
                combined_error = str(error_detalle) + '\n' + (error_texto or '')
                if ("CbteTipo" in combined_error or "FEParamGetTiposCbte" in combined_error or "10007" in combined_error):
                    # Si el cliente solicitó un ticket y AFIP no lo habilita para el punto de venta,
                    # intentamos hacer un fallback a un tipo de factura compatible (B o A) una sola vez.
                    if not fallback_intentado and formato_norm == "ticket":
                        print("AFIP indicó que el tipo de comprobante no está habilitado. Intentando fallback a tipo distinto (no-ticket)...")
                        # Decidir fallback: si receptor tiene CUIT -> A (1), si no -> B (6)
                        fallback_tipo = 1 if receptor_tiene_cuit and condicion_emisor == CondicionIVA.RESPONSABLE_INSCRIPTO else 6
                        datos_factura['tipo_afip'] = fallback_tipo
                        payload['datos_factura'] = datos_factura
                        fallback_intentado = True
                        # Reintentar inmediatamente (no incrementar el intento extra)
                        continue
                # Si no era un caso de fallback, mantenemos el message ya extraído en error_detalle
                    
            except:
                # Si no se pudo parsear JSON, usar el texto raw de la respuesta
                error_detalle = e.response.text if e.response else str(e)

            if intento == max_intentos - 1:  # Si es el último intento
                print(f"ERROR: El microservicio de facturación rechazó la petición después de {max_intentos} intentos. Status: {e.response.status_code}. Detalle: {error_detalle}")
                raise RuntimeError(f"Error en el servicio de facturación: {error_detalle}")

        except requests.exceptions.RequestException as e:
            error_str = str(e)
            if any(err in error_str for err in ["Connection reset by peer", "SSL", "ssl.SSLError", "UNEXPECTED_EOF_WHILE_READING"]):
                if intento < max_intentos - 1:  # Si no es el último intento
                    print(f"Error de conexión SSL detectado: {error_str}")
                    print(f"Esperando {tiempo_espera[intento]} segundos antes del siguiente intento...")
                    import time
                    time.sleep(tiempo_espera[intento])
                    continue  # Continuar con el siguiente intento
                else:
                    print(f"ERROR: Conexión SSL falló después de {max_intentos} intentos. Detalle: {e}")
                    raise RuntimeError("Error de conexión con AFIP. Los servidores pueden estar temporalmente no disponibles. Se agotaron los reintentos.")
            else:
                print(f"ERROR: No se pudo conectar con el microservicio de facturación. Detalle: {e}")
                raise RuntimeError("El servicio de facturación no está disponible en este momento.")
        
        except Exception as e:
            print(f"ERROR: Ocurrió un error inesperado durante la facturación. Detalle: {e}")
            if intento == max_intentos - 1:  # Si es el último intento
                raise RuntimeError(f"Error inesperado durante la facturación: {e}")
    
    # Si llegamos aquí es porque se agotaron todos los reintentos
    raise RuntimeError("Se agotaron todos los intentos de conexión con AFIP. Los servidores pueden estar temporalmente no disponibles.")
    


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

    # --- Verificación de URL de facturación ---
    if not FACTURACION_API_URL:
        raise ValueError("La URL del microservicio de facturación (FACTURACION_API_URL) no está configurada.")

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
        if not emisor_data.condicion_iva:
            raise ValueError("La condición de IVA del emisor es obligatoria.")
        cond_emisor_str = emisor_data.condicion_iva.upper().replace(' ', '_')
        condicion_emisor = CondicionIVA[cond_emisor_str]
    except (KeyError, AttributeError):
        raise ValueError(f"La condición de IVA del emisor '{emisor_data.condicion_iva}' no es válida.")

    if cliente_data and cliente_data.cuit_o_dni and cliente_data.cuit_o_dni != "0":
        documento = cliente_data.cuit_o_dni
        tipo_documento_receptor = TipoDocumento.CUIT if len(documento) == 11 else TipoDocumento.DNI
        try:
            if not cliente_data.condicion_iva:
                # Para NC, si no viene la condición, asumimos CF para no fallar
                print("Advertencia: Condición de IVA del receptor no provista para NC. Asumiendo Consumidor Final.")
                condicion_receptor = CondicionIVA.CONSUMIDOR_FINAL
            else:
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

    # --- PASO 3: Enviar al Microservicio con Reintentos ---
    print(f"Enviando petición de Nota de Crédito al microservicio...")
    
    max_intentos = 3
    tiempo_espera = [2, 5, 10]
    
    for intento in range(max_intentos):
        try:
            print(f"Intento {intento + 1} de {max_intentos} para Nota de Crédito")
            response = requests.post(
                FACTURACION_API_URL,
                json=payload,
                timeout=30,
            )
            response.raise_for_status() 
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            error_detalle = e.response.json().get('detail', e.response.text) if e.response else str(e)
            
            if any(err in str(error_detalle) for err in ["ssl.SSLError", "Connection reset by peer", "TypeError: 'ssl.SSLError' object is not subscriptable"]):
                if intento < max_intentos - 1:
                    print(f"Error SSL en NC. Esperando {tiempo_espera[intento]} segundos...")
                    import time
                    time.sleep(tiempo_espera[intento])
                    continue
                    
            if intento == max_intentos - 1:
                raise RuntimeError(f"Error en el servicio de facturación para NC: {error_detalle}")
                
        except requests.exceptions.RequestException as e:
            if any(err in str(e) for err in ["Connection reset by peer", "SSL", "ssl.SSLError"]):
                if intento < max_intentos - 1:
                    print(f"Error de conexión SSL en NC: {e}")
                    print(f"Esperando {tiempo_espera[intento]} segundos...")
                    import time
                    time.sleep(tiempo_espera[intento])
                    continue
                    
            if intento == max_intentos - 1:
                raise RuntimeError(f"El servicio de facturación no está disponible para NC: {e}")
    
    raise RuntimeError("Se agotaron todos los intentos de conexión con AFIP para Nota de Crédito.")