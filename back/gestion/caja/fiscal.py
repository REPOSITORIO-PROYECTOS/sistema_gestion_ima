# gestion/fiscal.py

import os
from datetime import datetime
from pysimpleafipws import AfipWs # O la librería que elijas (pyafipws, etc.)
import traceback # Para un mejor log de errores

# --- CONFIGURACIÓN GLOBAL DEFAULTS (pueden ser sobrescritos por config de empresa) ---
# Estos podrían incluso venir de un config.py general de la aplicación si son comunes.
PTO_VENTA_DEFAULT = int(os.getenv("AFIP_PTO_VENTA_DEFAULT", 1))
MODO_PRODUCCION_DEFAULT = os.getenv("AFIP_MODO_PRODUCCION_DEFAULT", "False").lower() == "true"

# Cache de conectores AFIP por CUIT para reutilizar sesiones WSAA
# Clave: CUIT, Valor: {'connector': objeto_AfipWs}
# PySimpleAfipWs maneja internamente la validez y renovación del Ticket de Acceso (TA)
afip_connectors_cache = {}

class AfipFiscalError(Exception):
    """Excepción personalizada para errores fiscales de AFIP."""
    pass

# --- FUNCIONES PRIVADAS DEL MÓDULO ---

def _get_afip_connector(cuit_empresa: str, cert_path_empresa: str, key_path_empresa: str, modo_produccion_empresa: bool):
    """
    Crea o reutiliza una instancia del conector AfipWs para una empresa específica.
    Levanta AfipFiscalError si falla la creación o validación de archivos.
    """
    global afip_connectors_cache

    # Clave para el caché puede incluir el modo producción si un mismo CUIT opera en ambos
    cache_key = f"{cuit_empresa}_{'prod' if modo_produccion_empresa else 'homo'}"

    cached_data = afip_connectors_cache.get(cache_key)
    if cached_data:
        # Aquí asumimos que si los parámetros de inicialización no han cambiado
        # y el conector existe, es válido. PySimpleAfipWs maneja el TA.
        print(f"INFO: Utilizando conector AFIP existente en caché para CUIT {cuit_empresa} (Producción: {modo_produccion_empresa}).")
        return cached_data['connector']

    print(f"INFO: Creando nuevo conector AFIP para CUIT {cuit_empresa} (Producción: {modo_produccion_empresa})...")
    try:
        if not cert_path_empresa or not os.path.exists(cert_path_empresa):
            raise AfipFiscalError(f"Archivo de certificado no encontrado o ruta no especificada para CUIT {cuit_empresa}: {cert_path_empresa}")
        if not key_path_empresa or not os.path.exists(key_path_empresa):
            raise AfipFiscalError(f"Archivo de clave privada no encontrado o ruta no especificada para CUIT {cuit_empresa}: {key_path_empresa}")

        connector = AfipWs(
            cuit=cuit_empresa,
            cert_path=cert_path_empresa,
            key_path=key_path_empresa,
            production=modo_produccion_empresa
        )
        
        # Opcional: Realizar una llamada dummy para forzar la autenticación y verificar conexión
        # try:
        #     connector.wsfev1.get_server_status() 
        # except Exception as auth_e:
        #     raise AfipFiscalError(f"Fallo al autenticar/probar conexión con AFIP para CUIT {cuit_empresa}: {auth_e}")

        afip_connectors_cache[cache_key] = {'connector': connector}
        print(f"INFO: Conector AFIP creado y cacheado para CUIT {cuit_empresa} (Producción: {modo_produccion_empresa}).")
        return connector

    except Exception as e:
        if cache_key in afip_connectors_cache:
            del afip_connectors_cache[cache_key]
        # No imprimir traceback aquí, dejar que la función que llama lo maneje si es necesario.
        # Solo relanzar como AfipFiscalError con un mensaje claro.
        raise AfipFiscalError(f"Fallo al crear conector AFIP para CUIT {cuit_empresa}: {str(e)}")


def _mapear_tipo_comprobante_afip(tipo_factura_sistema: str) -> int:
    tipo_map = {
        "FACTURA_A": 1, "A": 1, "FACTURA_B": 6, "B": 6, "FACTURA_C": 11, "C": 11,
        "NOTA_CREDITO_A": 3, "NCA": 3, "NOTA_CREDITO_B": 8, "NCB": 8, "NOTA_CREDITO_C": 13, "NCC": 13,
        "NOTA_DEBITO_A": 2, "NDA": 2, "NOTA_DEBITO_B": 7, "NDB": 7, "NOTA_DEBITO_C": 12, "NDC": 12,
    }
    mapped_value = tipo_map.get(str(tipo_factura_sistema).upper().replace(" ", "_"))
    if mapped_value is None:
        raise AfipFiscalError(f"Tipo de comprobante del sistema no mapeado a AFIP: '{tipo_factura_sistema}'")
    return mapped_value

def _mapear_tipo_doc_receptor_afip(tipo_doc_sistema: str) -> int:
    tipo_map = {"CUIT": 80, "CUIL": 86, "DNI": 96, "CONSUMIDOR_FINAL": 99, "PASAPORTE": 94, "CDI": 87, "LE": 0, "LC": 1, "CI_EXTRANJERA": 91}
    mapped_value = tipo_map.get(str(tipo_doc_sistema).upper())
    if mapped_value is None: # Si no se encuentra, default a Consumidor Final o error
        print(f"ADVERTENCIA: Tipo de documento receptor '{tipo_doc_sistema}' no mapeado, usando Consumidor Final (99).")
        return 99
        # raise AfipFiscalError(f"Tipo de documento receptor no mapeado: '{tipo_doc_sistema}'")
    return mapped_value

def _mapear_codigo_iva_afip(tasa_iva_sistema: float) -> int:
    try:
        tasa_iva_sistema = float(tasa_iva_sistema)
        if tasa_iva_sistema == 0: return 3
        if tasa_iva_sistema == 10.5: return 4
        if tasa_iva_sistema == 21: return 5
        if tasa_iva_sistema == 27: return 6
        if tasa_iva_sistema == 5: return 8
        if tasa_iva_sistema == 2.5: return 9
    except ValueError:
        pass # El error se lanzará abajo
    raise AfipFiscalError(f"Tasa de IVA del sistema no mapeada a código AFIP: '{tasa_iva_sistema}'")


# --- FUNCIONES PÚBLICAS DEL MÓDULO ---

def obtener_configuracion_fiscal_empresa(id_empresa: any) -> dict:
    """
    DEBES IMPLEMENTAR ESTA FUNCIÓN DE FORMA SEGURA.
    Obtiene la configuración fiscal (CUIT, rutas de cert/key, pto vta, modo_prod)
    para una empresa específica desde tu sistema de almacenamiento (BD, archivos, etc.).
    Levanta AfipFiscalError si no se encuentra o la config es inválida.
    """
    print(f"DEBUG: Buscando configuración fiscal para empresa ID: {id_empresa}...")
    # --- EJEMPLO CON DATOS HARCODEADOS (SOLO PARA PRUEBAS INICIALES) ---
    # ¡¡¡ EN PRODUCCIÓN, ESTO DEBE VENIR DE UNA FUENTE SEGURA Y DINÁMICA !!!
    # Almacenar los archivos .key y .crt en un lugar seguro del servidor, NO en la BD.
    # La BD solo almacena las RUTAS a estos archivos.
    
    # Asegúrate que estas rutas sean VÁLIDAS en tu entorno de desarrollo/prueba.
    base_path_certs_keys = "C:/AFIP_CREDENCIALES_EMPRESAS" # EJEMPLO: Carpeta base segura
    
    config_empresas_prueba = {
        "EMPRESA_TEST_1": { # Usa un ID que identifique a tu cliente/empresa
            "cuit": "20111111110", # CUIT de prueba de AFIP Homologación
            "cert_path": os.path.join(base_path_certs_keys, "empresa_test_1", "certificado_homo.crt"),
            "key_path": os.path.join(base_path_certs_keys, "empresa_test_1", "claveprivada_homo.key"),
            "punto_venta_default": 1,
            "modo_produccion": False # Siempre empezar con False (Homologación)
        },
        "EMPRESA_PROD_EJEMPLO": {
            "cuit": "20222222220", # CUIT REAL de una empresa
            "cert_path": os.path.join(base_path_certs_keys, "empresa_prod_ejemplo", "certificado_prod.crt"),
            "key_path": os.path.join(base_path_certs_keys, "empresa_prod_ejemplo", "claveprivada_prod.key"),
            "punto_venta_default": 2,
            "modo_produccion": True # Solo cuando estés listo para producción real
        }
    }
    # --- FIN EJEMPLO HARCODEADO ---

    config = config_empresas_prueba.get(str(id_empresa))
    if not config:
        raise AfipFiscalError(f"No se encontró configuración fiscal para la empresa ID: {id_empresa}")
    
    # Validaciones básicas
    if not all(k in config for k in ["cuit", "cert_path", "key_path", "punto_venta_default", "modo_produccion"]):
        raise AfipFiscalError(f"Configuración fiscal incompleta para la empresa ID: {id_empresa}.")
    
    print(f"DEBUG: Configuración fiscal encontrada para {id_empresa}: CUIT {config['cuit']}, ModoProd: {config['modo_produccion']}")
    return config


def emitir_factura_electronica(id_empresa_cliente: any, factura_data: dict):
    """
    Emite una factura electrónica para una empresa cliente específica.
    Levanta AfipFiscalError en caso de problemas de configuración o errores de AFIP.
    Devuelve un diccionario con los datos del CAE y el comprobante si es exitoso.
    """
    print(f"INFO: Iniciando emisión de factura para Empresa ID: {id_empresa_cliente}")
    config_fiscal = obtener_configuracion_fiscal_empresa(id_empresa_cliente) # Puede levantar AfipFiscalError

    cuit_emisor = config_fiscal["cuit"]
    punto_venta_a_usar = int(factura_data.get('punto_venta', config_fiscal["punto_venta_default"]))

    try:
        connector = _get_afip_connector(
            cuit_emisor,
            config_fiscal["cert_path"],
            config_fiscal["key_path"],
            config_fiscal["modo_produccion"]
        )

        tipo_cbte_afip = _mapear_tipo_comprobante_afip(factura_data.get('tipo_comprobante', ''))
        
        print(f"INFO: Emitiendo para CUIT: {cuit_emisor}, PtoVta: {punto_venta_a_usar}, TipoCbteSistema: {factura_data.get('tipo_comprobante', '')} (AFIP: {tipo_cbte_afip})")

        fecha_cbte_obj = factura_data.get('fecha_comprobante', datetime.now())
        if isinstance(fecha_cbte_obj, str):
            try:
                fecha_cbte_obj = datetime.strptime(fecha_cbte_obj, "%Y-%m-%d")
            except ValueError:
                raise AfipFiscalError(f"Formato de 'fecha_comprobante' incorrecto: {factura_data.get('fecha_comprobante')}. Usar YYYY-MM-DD.")

        concepto_cbte = int(factura_data.get('concepto_afip', 1)) # 1: Productos, 2: Servicios, 3: Productos y Servicios
        doc_tipo_receptor = _mapear_tipo_doc_receptor_afip(factura_data.get('cliente_tipo_doc', 'CONSUMIDOR_FINAL'))
        doc_nro_receptor_str = str(factura_data.get('cliente_nro_doc', '0')).strip()
        
        if doc_tipo_receptor != 99 and not doc_nro_receptor_str: # No es Consumidor Final y no hay nro doc
             raise AfipFiscalError("Número de documento del receptor es requerido si no es Consumidor Final.")
        try:
            doc_nro_receptor = int(doc_nro_receptor_str) if doc_nro_receptor_str else 0
        except ValueError:
            raise AfipFiscalError(f"Número de documento del receptor no es un número válido: '{doc_nro_receptor_str}'")


        imp_total = round(float(factura_data.get('importe_total', 0.0)), 2)
        imp_neto = round(float(factura_data.get('importe_neto_gravado', 0.0)), 2)
        imp_iva = round(float(factura_data.get('importe_iva', 0.0)), 2)
        imp_exento = round(float(factura_data.get('importe_exento', 0.0)), 2)
        imp_no_gravado = round(float(factura_data.get('importe_no_gravado', 0.0)), 2)
        imp_trib = round(float(factura_data.get('importe_otros_tributos', 0.0)), 2)

        suma_componentes = round(imp_neto + imp_iva + imp_no_gravado + imp_exento + imp_trib, 2)
        if abs(suma_componentes - imp_total) > 0.019: # Aumentar un poco la tolerancia por múltiples redondeos
            raise AfipFiscalError(f"Descuadre de importes: Total ({imp_total}) vs Suma de Componentes ({suma_componentes}). Diferencia: {abs(suma_componentes - imp_total)}")

        array_iva = []
        if 'items_iva' in factura_data and factura_data['items_iva'] and isinstance(factura_data['items_iva'], list):
            for item_iva_data in factura_data['items_iva']:
                if not isinstance(item_iva_data, dict): continue # Saltar si no es un dict
                array_iva.append({
                    'Id': _mapear_codigo_iva_afip(item_iva_data.get('tasa_iva')),
                    'BaseImp': round(float(item_iva_data.get('base_imponible', 0.0)), 2),
                    'Importe': round(float(item_iva_data.get('importe_iva_item', 0.0)), 2)
                })
        elif imp_neto > 0 and imp_iva > 0: # Caso simplificado: un solo tipo de IVA deducido
            tasa_iva_estimada = round((imp_iva / imp_neto) * 100, 1) if imp_neto != 0 else 21.0
            array_iva.append({'Id': _mapear_codigo_iva_afip(tasa_iva_estimada), 'BaseImp': imp_neto, 'Importe': imp_iva})
        elif imp_exento > 0 and imp_neto == 0 and imp_iva == 0 : # Solo exento
             array_iva.append({'Id': _mapear_codigo_iva_afip(0), 'BaseImp': imp_exento, 'Importe': 0.00}) # WSFEV1 puede requerir esto
        
        # Si no hay IVA (ej. Factura C de monotributista), array_iva puede ser None o lista vacía.
        # PySimpleAfipWs lo maneja si se pasa None.
        if not array_iva and (tipo_cbte_afip in [1, 6, 3, 8, 2, 7]) and (imp_neto > 0 or imp_iva > 0) : # A y B deben tener IVA si hay neto
            raise AfipFiscalError("Facturas A/B con importe neto > 0 deben detallar IVA.")


        mon_id = str(factura_data.get('moneda_id', 'PES')).upper()
        mon_cotiz = float(factura_data.get('moneda_cotiz', 1.0))
        if mon_id != 'PES' and mon_cotiz <= 0:
            raise AfipFiscalError("Cotización de moneda extranjera debe ser mayor a 0.")

        # Parámetros para emitir_comprobante de PySimpleAfipWs
        params_emision = {
            "punto_venta": punto_venta_a_usar,
            "tipo_comprobante": tipo_cbte_afip,
            "fecha_comprobante": fecha_cbte_obj, # PySimpleAfipWs espera objeto datetime
            "concepto": concepto_cbte,
            "tipo_documento_comprador": doc_tipo_receptor,
            "numero_documento_comprador": doc_nro_receptor,
            "importe_total": imp_total,
            "importe_neto_gravado": imp_neto,
            "importe_iva": imp_iva,
            "importe_exento": imp_exento,
            "importe_no_gravado": imp_no_gravado,
            "importe_otros_tributos": imp_trib,
            "items_iva": array_iva if array_iva else None,
            "comprobantes_asociados": factura_data.get('comprobantes_asociados'), # Lista de dicts
            "otros_tributos": factura_data.get('otros_tributos'), # Lista de dicts
            "moneda_id": mon_id,
            "moneda_cotizacion": mon_cotiz,
            # Campos para servicios si Concepto es 2 o 3
            "fecha_servicio_desde": factura_data.get('fecha_servicio_desde'), # "YYYYMMDD" o datetime
            "fecha_servicio_hasta": factura_data.get('fecha_servicio_hasta'), # "YYYYMMDD" o datetime
            "fecha_vencimiento_pago": factura_data.get('fecha_vencimiento_pago') # "YYYYMMDD" o datetime
        }
        
        # Limpiar Nones de los parámetros opcionales
        params_emision_limpio = {k: v for k, v in params_emision.items() if v is not None}

        print(f"INFO: Llamando a AFIP WSFEV1 emitir_comprobante para CUIT {cuit_emisor} con params: {params_emision_limpio}")
        resultado = connector.wsfev1.emitir_comprobante(**params_emision_limpio)
        
        # `resultado` es un diccionario con la respuesta parseada.
        # Campos clave: 'cae', 'fecha_vencimiento_cae', 'numero_comprobante', 'resultado' (A:Aprobado, R:Rechazado, P:Parcial)
        # 'observaciones_array', 'eventos_array', 'errores_array'

        if resultado.get('resultado','').upper() != 'A': # No Aprobado
            msg_error = f"AFIP no aprobó el comprobante para CUIT {cuit_emisor}. Resultado: {resultado.get('resultado')}. "
            if resultado.get('errores_array'):
                msg_error += "Errores: " + " ".join([f"Cod: {e.get('Code', '')} Msg: {e.get('Msg', '')}" for e in resultado['errores_array']])
            elif resultado.get('observaciones_array'):
                 msg_error += "Observaciones: " + " ".join([f"Cod: {e.get('Code', '')} Msg: {e.get('Msg', '')}" for e in resultado['observaciones_array']])
            else:
                msg_error += f"Respuesta AFIP completa: {resultado}"
            raise AfipFiscalError(msg_error)

        cae = resultado.get('cae')
        fecha_vto_cae_str = resultado.get('fecha_vencimiento_cae') # Formato YYYYMMDD
        nro_cbte_emitido = resultado.get('numero_comprobante')

        if not cae or not fecha_vto_cae_str:
            raise AfipFiscalError(f"AFIP aprobó pero no devolvió CAE o Fecha Vto. CAE. CUIT {cuit_emisor}. Respuesta: {resultado}")
        
        try:
            fecha_vto_cae_obj = datetime.strptime(fecha_vto_cae_str, "%Y%m%d")
        except ValueError:
            fecha_vto_cae_obj = fecha_vto_cae_str # Mantener como string si no se puede parsear

        print(f"INFO: CAE Obtenido para CUIT {cuit_emisor}: {cae}, Vto: {fecha_vto_cae_str}, Cbte Nro: {nro_cbte_emitido}")
        return {
            "status": "success", "message": "Factura autorizada por AFIP.",
            "cuit_emisor": cuit_emisor, "cae": cae, "fecha_vencimiento_cae": fecha_vto_cae_obj, # Devolver objeto datetime
            "numero_comprobante_emitido": nro_cbte_emitido, "punto_venta": punto_venta_a_usar,
            "tipo_comprobante_afip": tipo_cbte_afip, "raw_response_afip": resultado
        }

    except AfipFiscalError as afe:
        # Errores ya logueados o específicos de AFIP
        print(f"ERROR_FISCAL: {afe} (CUIT: {cuit_emisor if 'cuit_emisor' in locals() else 'N/A'}, EmpresaID: {id_empresa_cliente})")
        return {"status": "error", "message": str(afe)}
    except Exception as e:
        # Errores inesperados de la librería, conexión, etc.
        print(f"ERROR_INESPERADO: Emitiendo factura para Empresa ID {id_empresa_cliente}, CUIT {cuit_emisor if 'cuit_emisor' in locals() else 'N/A'}: {e}")
        traceback.print_exc()
        return {"status": "error", "message": f"Error inesperado durante la comunicación con AFIP: {str(e)}"}


def consultar_estado_servidores_afip_para_empresa(id_empresa: any):
    """Consulta el estado de los servidores de AFIP usando las credenciales de una empresa."""
    config_fiscal = obtener_configuracion_fiscal_empresa(id_empresa)
    cuit_emisor = config_fiscal["cuit"]
    try:
        connector = _get_afip_connector(
            cuit_emisor,
            config_fiscal["cert_path"],
            config_fiscal["key_path"],
            config_fiscal["modo_produccion"]
        )
        status_data = connector.wsfev1.get_server_status()
        print(f"INFO: Estado Servidores AFIP (para CUIT {cuit_emisor}): {status_data}")
        return {"status": "success", "data": status_data, "cuit_consultado": cuit_emisor}
    except AfipFiscalError as afe:
        print(f"ERROR_FISCAL: Consultando estado AFIP para empresa ID {id_empresa}: {afe}")
        return {"status": "error", "message": str(afe), "cuit_consultado": cuit_emisor}
    except Exception as e:
        print(f"ERROR_INESPERADO: Consultando estado AFIP para empresa ID {id_empresa}: {e}")
        traceback.print_exc()
        return {"status": "error", "message": str(e), "cuit_consultado": cuit_emisor}

def obtener_ultimo_comprobante_autorizado(id_empresa: any, punto_venta: int, tipo_comprobante_afip: int):
    """Obtiene el último número de comprobante autorizado para un PtoVta y TipoCbte."""
    config_fiscal = obtener_configuracion_fiscal_empresa(id_empresa)
    cuit_emisor = config_fiscal["cuit"]
    try:
        connector = _get_afip_connector(
            cuit_emisor,
            config_fiscal["cert_path"],
            config_fiscal["key_path"],
            config_fiscal["modo_produccion"]
        )
        ultimo_nro = connector.wsfev1.get_ultimo_cmp_auth(punto_venta, tipo_comprobante_afip)
        print(f"INFO: Último comprobante para CUIT {cuit_emisor}, PtoVta {punto_venta}, Tipo {tipo_comprobante_afip}: {ultimo_nro}")
        return {"status": "success", "ultimo_numero": ultimo_nro if ultimo_nro is not None else 0}
    except AfipFiscalError as afe:
        print(f"ERROR_FISCAL: Obteniendo último comprobante para CUIT {cuit_emisor}: {afe}")
        return {"status": "error", "message": str(afe)}
    except Exception as e:
        print(f"ERROR_INESPERADO: Obteniendo último comprobante para CUIT {cuit_emisor}: {e}")
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


# --- Flujo de ejemplo de uso MULTI-CLIENTE ---
if __name__ == '__main__':
    print("--- INICIO EJEMPLO DE FACTURACIÓN ELECTRÓNICA AFIP (MULTI-CLIENTE) ---")
    
    # Simular que este ID viene de la sesión de caja del cliente actual
    # DEBE COINCIDIR CON UNA DE LAS CLAVES EN `config_empresas_prueba`
    # dentro de `obtener_configuracion_fiscal_empresa`
    id_empresa_a_facturar = "EMPRESA_TEST_1" 
    
    print(f"\n--- Probando para Empresa ID: {id_empresa_a_facturar} ---")

    # 1. Verificar estado de servidores (opcional, bueno para diagnóstico)
    # print("\n1. Consultando estado de servidores AFIP...")
    # estado_servidores = consultar_estado_servidores_afip_para_empresa(id_empresa_a_facturar)
    # if estado_servidores["status"] == "success":
    #     if estado_servidores["data"].get("AppServer") != "OK" or \
    #        estado_servidores["data"].get("DbServer") != "OK" or \
    #        estado_servidores["data"].get("AuthServer") != "OK":
    #         print(f"  ADVERTENCIA: Servidores AFIP no totalmente OK: {estado_servidores['data']}")
    # else:
    #     print(f"  ERROR: No se pudo obtener estado de servidores: {estado_servidores['message']}")

    # 2. Obtener último comprobante (ejemplo)
    print("\n2. Consultando último comprobante autorizado...")
    try:
        pv = obtener_configuracion_fiscal_empresa(id_empresa_a_facturar)["punto_venta_default"]
        tipo_cbte_b_afip = _mapear_tipo_comprobante_afip("FACTURA_B")
        res_ultimo_cbte = obtener_ultimo_comprobante_autorizado(id_empresa_a_facturar, pv, tipo_cbte_b_afip)
        if res_ultimo_cbte["status"] == "success":
            print(f"  Última Factura B para PtoVta {pv}: {res_ultimo_cbte['ultimo_numero']}")
        else:
            print(f"  ERROR al obtener último comprobante: {res_ultimo_cbte['message']}")
    except AfipFiscalError as e:
         print(f"  ERROR al obtener datos para consultar último comprobante: {e}")


    # 3. Preparar datos de una factura de ejemplo
    print("\n3. Preparando datos para factura de ejemplo...")
    factura_ejemplo = {
        'tipo_comprobante': "FACTURA_B",
        'fecha_comprobante': datetime.now().strftime("%Y-%m-%d"), # "YYYY-MM-DD"
        # 'punto_venta': pv, # Si no se pasa, usa el default de la empresa
        'cliente_tipo_doc': "DNI",
        'cliente_nro_doc': "20000000", # DNI de prueba
        'importe_neto_gravado': 100.00,
        'importe_iva': 21.00,
        'importe_total': 121.00,
        'items_iva': [{'tasa_iva': 21.0, 'base_imponible': 100.00, 'importe_iva_item': 21.00}],
        'moneda_id': "PES", 'moneda_cotiz': 1.0,
        'concepto_afip': 1 # Productos
    }

    print(f"\n4. Intentando emitir Factura de ejemplo para Empresa ID: {id_empresa_a_facturar}...")
    resultado_emision = emitir_factura_electronica(id_empresa_a_facturar, factura_ejemplo)
    
    print("\n--- Resultado Final de la Emisión ---")
    print(resultado_emision)

    if resultado_emision and resultado_emision.get("status") == "success":
        print(f"\n  ¡ÉXITO!")
        print(f"  CUIT Emisor: {resultado_emision.get('cuit_emisor')}")
        print(f"  CAE: {resultado_emision.get('cae')}")
        print(f"  Vence CAE: {resultado_emision.get('fecha_vencimiento_cae').strftime('%Y-%m-%d') if isinstance(resultado_emision.get('fecha_vencimiento_cae'), datetime) else resultado_emision.get('fecha_vencimiento_cae')}")
        print(f"  Nro Cbte Emitido: {resultado_emision.get('numero_comprobante_emitido')}")
        print(f"  Punto de Venta: {resultado_emision.get('punto_venta')}")
        print(f"  Tipo Cbte AFIP: {resultado_emision.get('tipo_comprobante_afip')}")
    else:
        print(f"\n  FALLO LA EMISIÓN.")
        print(f"  Mensaje: {resultado_emision.get('message', 'Sin mensaje específico.')}")

    print("\n--- FIN EJEMPLO ---")