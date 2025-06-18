# gestion/fiscal/afip_wsfe_service.py
from datetime import datetime
import traceback # Para loguear errores completos

# Importaciones desde los otros módulos del paquete fiscal
from .afip_config_loader import obtener_configuracion_fiscal_empresa, AfipFiscalConfigError
from .afip_connector import get_afip_connector, AfipConnectionError
from .afip_mappers import (
    map_tipo_comprobante_afip, map_tipo_doc_receptor_afip,
    map_codigo_iva_afip, map_concepto_afip, AfipMappingError
)

# Definir una excepción base para este servicio
class AfipWsfeServiceError(Exception):
    pass


PTO_VENTA_DEFAULT_APP = 1 # Podría venir de una config global de la app, si es necesario un default general

def emitir_factura_electronica(id_empresa_cliente: any, factura_data: dict):
    """
    Emite una factura electrónica para una empresa cliente específica.
    Levanta AfipWsfeServiceError en caso de problemas.
    Devuelve un diccionario con los datos del CAE y el comprobante si es exitoso.
    """
    print(f"INFO (wsfe_service): Iniciando emisión factura para Empresa ID: {id_empresa_cliente}")
    
    # Usaremos una variable local para el CUIT para mensajes de error
    cuit_emisor_para_log = "N/A" 
    
    try:
        config_fiscal = obtener_configuracion_fiscal_empresa(id_empresa_cliente)
        cuit_emisor_para_log = config_fiscal["cuit"]

        connector = get_afip_connector(
            config_fiscal["cuit"],
            config_fiscal["cert_path"],
            config_fiscal["key_path"],
            config_fiscal["modo_produccion"]
        )

        # --- Preparación de Datos ---
        pto_vta_usar = int(factura_data.get('punto_venta', config_fiscal.get("punto_venta_default", PTO_VENTA_DEFAULT_APP)))
        tipo_cbte_afip = map_tipo_comprobante_afip(factura_data.get('tipo_comprobante', ''))
        
        print(f"INFO (wsfe_service): Emitiendo para CUIT {cuit_emisor_para_log}, PtoVta {pto_vta_usar}, TipoCbteAFIP {tipo_cbte_afip}")

        fecha_cbte_obj = factura_data.get('fecha_comprobante', datetime.now())
        if isinstance(fecha_cbte_obj, str):
            try: fecha_cbte_obj = datetime.strptime(fecha_cbte_obj, "%Y-%m-%d")
            except ValueError: raise AfipWsfeServiceError(f"Formato 'fecha_comprobante' incorrecto: {factura_data.get('fecha_comprobante')}. Usar YYYY-MM-DD.")

        concepto_cbte = map_concepto_afip(factura_data.get('concepto_operacion', factura_data.get('concepto_afip', 'PRODUCTOS')))
        doc_tipo_receptor = map_tipo_doc_receptor_afip(factura_data.get('cliente_tipo_doc', 'CONSUMIDOR_FINAL'))
        
        doc_nro_receptor_str = str(factura_data.get('cliente_nro_doc', '0')).strip()
        if doc_tipo_receptor != 99 and not doc_nro_receptor_str:
             raise AfipWsfeServiceError("Nro. doc. receptor es requerido si no es Consumidor Final.")
        try: doc_nro_receptor = int(doc_nro_receptor_str) if doc_nro_receptor_str else 0
        except ValueError: raise AfipWsfeServiceError(f"Nro. doc. receptor no es válido: '{doc_nro_receptor_str}'")

        # Importes (robustecer la conversión a float)
        def get_float(key, default=0.0):
            val = factura_data.get(key, default)
            try: return float(val)
            except (ValueError, TypeError): raise AfipWsfeServiceError(f"Importe '{key}' no es un número válido: '{val}'")

        imp_total = round(get_float('importe_total'), 2)
        imp_neto = round(get_float('importe_neto_gravado'), 2)
        imp_iva = round(get_float('importe_iva'), 2)
        imp_exento = round(get_float('importe_exento'), 2)
        imp_no_gravado = round(get_float('importe_no_gravado'), 2)
        imp_trib = round(get_float('importe_otros_tributos'), 2)

        suma_componentes = round(imp_neto + imp_iva + imp_no_gravado + imp_exento + imp_trib, 2)
        if abs(suma_componentes - imp_total) > 0.019:
            raise AfipWsfeServiceError(f"Descuadre de importes: Total ({imp_total}) vs Suma Componentes ({suma_componentes}).")

        array_iva = []
        items_iva_data = factura_data.get('items_iva')
        if items_iva_data and isinstance(items_iva_data, list):
            for item_iva_data in items_iva_data:
                if not isinstance(item_iva_data, dict): continue
                try:
                    array_iva.append({
                        'Id': map_codigo_iva_afip(item_iva_data.get('tasa_iva')),
                        'BaseImp': round(float(item_iva_data.get('base_imponible', 0.0)), 2),
                        'Importe': round(float(item_iva_data.get('importe_iva_item', 0.0)), 2)
                    })
                except (AfipMappingError, ValueError, TypeError) as map_err:
                    raise AfipWsfeServiceError(f"Error en item_iva '{item_iva_data}': {map_err}")
        elif imp_neto > 0 and imp_iva > 0:
            tasa_iva_estimada = round((imp_iva / imp_neto) * 100, 1) if imp_neto != 0 else 21.0
            array_iva.append({'Id': map_codigo_iva_afip(tasa_iva_estimada), 'BaseImp': imp_neto, 'Importe': imp_iva})
        elif imp_exento > 0 and not (imp_neto > 0 or imp_iva > 0):
             array_iva.append({'Id': map_codigo_iva_afip(0), 'BaseImp': imp_exento, 'Importe': 0.00})
        
        if not array_iva and tipo_cbte_afip in [1, 6, 3, 8, 2, 7] and (imp_neto > 0 or imp_iva > 0):
            raise AfipWsfeServiceError("Facturas A/B con importe neto > 0 deben detallar IVA.")

        mon_id = str(factura_data.get('moneda_id', 'PES')).upper()
        mon_cotiz = get_float('moneda_cotiz', 1.0)
        if mon_id != 'PES' and mon_cotiz <= 0:
            raise AfipWsfeServiceError("Cotización de moneda extranjera debe ser > 0.")

        # --- Preparar parámetros para PySimpleAfipWs ---
        params_emision = {
            "punto_venta": pto_vta_usar, "tipo_comprobante": tipo_cbte_afip,
            "fecha_comprobante": fecha_cbte_obj, "concepto": concepto_cbte,
            "tipo_documento_comprador": doc_tipo_receptor, "numero_documento_comprador": doc_nro_receptor,
            "importe_total": imp_total, "importe_neto_gravado": imp_neto, "importe_iva": imp_iva,
            "importe_exento": imp_exento, "importe_no_gravado": imp_no_gravado,
            "importe_otros_tributos": imp_trib, "items_iva": array_iva if array_iva else None,
            "comprobantes_asociados": factura_data.get('comprobantes_asociados'),
            "otros_tributos": factura_data.get('otros_tributos'),
            "moneda_id": mon_id, "moneda_cotizacion": mon_cotiz,
            "fecha_servicio_desde": factura_data.get('fecha_servicio_desde'),
            "fecha_servicio_hasta": factura_data.get('fecha_servicio_hasta'),
            "fecha_vencimiento_pago": factura_data.get('fecha_vencimiento_pago')
        }
        params_emision_limpio = {k: v for k, v in params_emision.items() if v is not None}
        
        print(f"DEBUG (wsfe_service): Parámetros para emitir_comprobante: {params_emision_limpio}")
        resultado = connector.wsfev1.emitir_comprobante(**params_emision_limpio)
        
        if str(resultado.get('resultado','R')).upper() != 'A': # Si no es Aprobado
            msg_error = f"AFIP no aprobó el comprobante. Resultado: {resultado.get('resultado')}. "
            detalles_error = []
            if resultado.get('errores_array'):
                detalles_error.extend([f"Err(Cod:{e.get('Code','?')},Msg:{e.get('Msg','?')})" for e in resultado['errores_array']])
            if resultado.get('observaciones_array'):
                 detalles_error.extend([f"Obs(Cod:{e.get('Code','?')},Msg:{e.get('Msg','?')})" for e in resultado['observaciones_array']])
            if detalles_error: msg_error += " ".join(detalles_error)
            else: msg_error += f"Respuesta AFIP: {resultado}" # Respuesta completa si no hay errores/obs específicas
            raise AfipWsfeServiceError(msg_error)

        cae = resultado.get('cae')
        fecha_vto_cae_str = resultado.get('fecha_vencimiento_cae')
        nro_cbte_emitido = resultado.get('numero_comprobante')

        if not cae or not fecha_vto_cae_str:
            raise AfipWsfeServiceError(f"AFIP aprobó pero no devolvió CAE o FechaVtoCAE. Respuesta: {resultado}")
        
        try: fecha_vto_cae_obj = datetime.strptime(fecha_vto_cae_str, "%Y%m%d")
        except ValueError: fecha_vto_cae_obj = fecha_vto_cae_str # Dejar como string si no se puede parsear

        print(f"INFO (wsfe_service): CAE Obtenido: {cae}, Vto: {fecha_vto_cae_str}, Cbte Nro: {nro_cbte_emitido}")
        return {
            "status": "success", "message": "Factura autorizada por AFIP.",
            "cuit_emisor": cuit_emisor_para_log, "cae": cae, "fecha_vencimiento_cae": fecha_vto_cae_obj,
            "numero_comprobante_emitido": nro_cbte_emitido, "punto_venta": pto_vta_usar,
            "tipo_comprobante_afip": tipo_cbte_afip, "raw_response_afip": resultado
        }

    except (AfipFiscalConfigError, AfipConnectionError, AfipMappingError, AfipWsfeServiceError) as afe_err:
        # Errores controlados de nuestra lógica fiscal
        print(f"ERROR_FISCAL_CONTROLADO (wsfe_service): {afe_err} (CUIT: {cuit_emisor_para_log}, EmpresaID: {id_empresa_cliente})")
        return {"status": "error", "message": str(afe_err)}
    except Exception as e:
        # Errores inesperados (ej. de la librería PySimpleAfipWs, red, etc.)
        print(f"ERROR_INESPERADO (wsfe_service): Emitiendo para Empresa ID {id_empresa_cliente}, CUIT {cuit_emisor_para_log}: {e}")
        traceback.print_exc()
        return {"status": "error", "message": f"Error inesperado durante comunicación con AFIP: {str(e)}"}


def consultar_estado_servidores_afip(id_empresa: any):
    """Consulta el estado de los servidores de AFIP usando las credenciales de una empresa."""
    cuit_emisor_para_log = "N/A"
    try:
        config_fiscal = obtener_configuracion_fiscal_empresa(id_empresa)
        cuit_emisor_para_log = config_fiscal["cuit"]
        connector = get_afip_connector(
            config_fiscal["cuit"], config_fiscal["cert_path"],
            config_fiscal["key_path"], config_fiscal["modo_produccion"]
        )
        status_data = connector.wsfev1.get_server_status()
        print(f"INFO (wsfe_service): Estado Servidores AFIP (para CUIT {cuit_emisor_para_log}): {status_data}")
        return {"status": "success", "data": status_data, "cuit_consultado": cuit_emisor_para_log}
    except (AfipFiscalConfigError, AfipConnectionError) as afe_err:
        print(f"ERROR_FISCAL_CONTROLADO (wsfe_service): Consultando estado AFIP para empresa ID {id_empresa}: {afe_err}")
        return {"status": "error", "message": str(afe_err), "cuit_consultado": cuit_emisor_para_log}
    except Exception as e:
        print(f"ERROR_INESPERADO (wsfe_service): Consultando estado AFIP para empresa ID {id_empresa}: {e}")
        traceback.print_exc()
        return {"status": "error", "message": str(e), "cuit_consultado": cuit_emisor_para_log}


def obtener_ultimo_comprobante_autorizado(id_empresa: any, punto_venta: int, tipo_comprobante_sistema: str):
    """Obtiene el último número de comprobante autorizado para un PtoVta y Tipo de Comprobante del Sistema."""
    cuit_emisor_para_log = "N/A"
    try:
        config_fiscal = obtener_configuracion_fiscal_empresa(id_empresa)
        cuit_emisor_para_log = config_fiscal["cuit"]
        connector = get_afip_connector(
            config_fiscal["cuit"], config_fiscal["cert_path"],
            config_fiscal["key_path"], config_fiscal["modo_produccion"]
        )
        tipo_cbte_afip = map_tipo_comprobante_afip(tipo_comprobante_sistema)
        
        ultimo_nro = connector.wsfev1.get_ultimo_cmp_auth(int(punto_venta), tipo_cbte_afip)
        ultimo_nro_val = ultimo_nro if ultimo_nro is not None else 0
        print(f"INFO (wsfe_service): Último Cbte para CUIT {cuit_emisor_para_log}, PtoVta {punto_venta}, TipoAFIP {tipo_cbte_afip}: {ultimo_nro_val}")
        return {"status": "success", "ultimo_numero": ultimo_nro_val}
    except (AfipFiscalConfigError, AfipConnectionError, AfipMappingError) as afe_err:
        print(f"ERROR_FISCAL_CONTROLADO (wsfe_service): Obteniendo último cbte para CUIT {cuit_emisor_para_log}: {afe_err}")
        return {"status": "error", "message": str(afe_err)}
    except Exception as e:
        print(f"ERROR_INESPERADO (wsfe_service): Obteniendo último cbte para CUIT {cuit_emisor_para_log}: {e}")
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


# --- Ejemplo de Uso (para probar este módulo directamente) ---
if __name__ == '__main__':
    print("--- INICIO PRUEBA DIRECTA MODULO afip_wsfe_service ---")
    
    # Configurar .env o variables de entorno para AFIP_EMPRESA_TEST_1_...
    # y AFIP_CERTS_BASE_PATH si es necesario.
    # Asegúrate de tener archivos .crt y .key de prueba en la ruta esperada.
    
    id_empresa_prueba = "EMPRESA_TEST_1"
    
    print(f"\n--- Probando para Empresa ID: {id_empresa_prueba} ---")

    print("\n1. Consultando estado de servidores AFIP...")
    estado_servidores = consultar_estado_servidores_afip(id_empresa_prueba)
    print(f"   Resultado consulta estado: {estado_servidores}")
    if estado_servidores["status"] == "success":
        data = estado_servidores['data']
        if not (data.get("AppServer") == "OK" and data.get("DbServer") == "OK" and data.get("AuthServer") == "OK"):
            print(f"  ADVERTENCIA: Servidores AFIP no totalmente OK: {data}")

    print("\n2. Consultando último comprobante autorizado...")
    try:
        # Obtener punto de venta de la configuración para la prueba
        config_emp = obtener_configuracion_fiscal_empresa(id_empresa_prueba)
        pv_prueba = config_emp["punto_venta_default"]
        
        res_ultimo_cbte = obtener_ultimo_comprobante_autorizado(id_empresa_prueba, pv_prueba, "FACTURA_B")
        if res_ultimo_cbte["status"] == "success":
            print(f"  Última Factura B para PtoVta {pv_prueba}: {res_ultimo_cbte['ultimo_numero']}")
        else:
            print(f"  ERROR al obtener último comprobante: {res_ultimo_cbte['message']}")
    except Exception as e_conf:
         print(f"  ERROR obteniendo config para consultar último comprobante: {e_conf}")

    print("\n3. Preparando datos para factura de ejemplo...")
    factura_ejemplo = {
        'tipo_comprobante': "FACTURA_B",
        'fecha_comprobante': datetime.now().strftime("%Y-%m-%d"),
        # 'punto_venta': pv_prueba, # Usa el default de la empresa si no se pasa
        'cliente_tipo_doc': "DNI",
        'cliente_nro_doc': "20000000", # DNI de prueba válido
        'importe_neto_gravado': 1.00, # Usar montos bajos para pruebas de homologación
        'importe_iva': 0.21,
        'importe_total': 1.21,
        'items_iva': [{'tasa_iva': 21.0, 'base_imponible': 1.00, 'importe_iva_item': 0.21}],
        'moneda_id': "PES", 'moneda_cotiz': 1.0,
        'concepto_operacion': 'PRODUCTOS' # O 1
    }

    print(f"\n4. Intentando emitir Factura de ejemplo para Empresa ID: {id_empresa_prueba}...")
    resultado_emision = emitir_factura_electronica(id_empresa_prueba, factura_ejemplo)
    
    print("\n--- Resultado Final de la Emisión de Prueba ---")
    print(resultado_emision)

    if resultado_emision and resultado_emision.get("status") == "success":
        print(f"\n  ¡ÉXITO EMISIÓN PRUEBA!")
        print(f"  CUIT Emisor: {resultado_emision.get('cuit_emisor')}")
        print(f"  CAE: {resultado_emision.get('cae')}")
        vto_cae = resultado_emision.get('fecha_vencimiento_cae')
        vto_cae_str = vto_cae.strftime('%Y-%m-%d') if isinstance(vto_cae, datetime) else str(vto_cae)
        print(f"  Vence CAE: {vto_cae_str}")
        print(f"  Nro Cbte Emitido: {resultado_emision.get('numero_comprobante_emitido')}")
    else:
        print(f"\n  FALLO LA EMISIÓN DE PRUEBA.")
        print(f"  Mensaje: {resultado_emision.get('message', 'Sin mensaje específico.')}")

    print("\n--- FIN PRUEBA DIRECTA MODULO ---")