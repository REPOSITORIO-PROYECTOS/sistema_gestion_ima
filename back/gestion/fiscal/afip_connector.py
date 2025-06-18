# gestion/fiscal/afip_connector.py
import os
from pysimpleafipws import AfipWs
# No necesita importar de afip_config_loader directamente aquí,
# recibirá los paths de cert/key como parámetros.

# Cache de conectores AFIP por CUIT y modo_produccion
afip_connectors_cache = {} # Clave: "cuit_modo", Valor: objeto_AfipWs

class AfipConnectionError(Exception): # Excepción específica para este módulo
    pass

def get_afip_connector(cuit_empresa: str, cert_path_empresa: str, key_path_empresa: str, modo_produccion_empresa: bool):
    """
    Crea o reutiliza una instancia del conector AfipWs para una empresa específica.
    Levanta AfipConnectionError si falla.
    """
    global afip_connectors_cache
    cache_key = f"{cuit_empresa}_{'prod' if modo_produccion_empresa else 'homo'}"

    if cache_key in afip_connectors_cache:
        print(f"INFO (afip_connector): Usando conector AFIP de caché para CUIT {cuit_empresa} (Producción: {modo_produccion_empresa}).")
        return afip_connectors_cache[cache_key]

    print(f"INFO (afip_connector): Creando nuevo conector AFIP para CUIT {cuit_empresa} (Producción: {modo_produccion_empresa})...")
    try:
        # Las validaciones de existencia de cert_path y key_path ya se hicieron en afip_config_loader
        connector = AfipWs(
            cuit=cuit_empresa,
            cert_path=cert_path_empresa,
            key_path=key_path_empresa,
            production=modo_produccion_empresa
        )
        
        # Opcional: Probar la conexión/autenticación inmediatamente
        # try:
        #     status = connector.wsfev1.get_server_status() # Llama a un método simple para forzar TA
        #     print(f"DEBUG (afip_connector): Prueba de conexión WSFEV1 OK. Status: {status}")
        # except Exception as test_conn_e:
        #     raise AfipConnectionError(f"Fallo en prueba de conexión/autenticación con AFIP para CUIT {cuit_empresa}: {test_conn_e}")

        afip_connectors_cache[cache_key] = connector
        print(f"INFO (afip_connector): Conector AFIP creado y cacheado para CUIT {cuit_empresa}.")
        return connector

    except Exception as e:
        # No relanzar con traceback completo aquí, solo mensaje claro.
        raise AfipConnectionError(f"Fallo al crear conector AfipWs para CUIT {cuit_empresa}: {str(e)}")

def clear_afip_connector_cache():
    """Limpia el caché de conectores AFIP."""
    global afip_connectors_cache
    afip_connectors_cache.clear()
    print("INFO (afip_connector): Caché de conectores AFIP limpiado.")