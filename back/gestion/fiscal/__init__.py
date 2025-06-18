# gestion/fiscal/__init__.py

# Exponer las funciones principales que se usarán desde otros módulos
from .afip_wsfe_service import (
    emitir_factura_electronica,
    consultar_estado_servidores_afip, # Renombrado para claridad
    obtener_ultimo_comprobante_autorizado
)

# Exponer excepciones personalizadas si es necesario
from .afip_config_loader import AfipFiscalConfigError
from .afip_connector import AfipConnectionError
from .afip_mappers import AfipMappingError
from .afip_wsfe_service import AfipWsfeServiceError


__all__ = [
    "emitir_factura_electronica",
    "consultar_estado_servidores_afip",
    "obtener_ultimo_comprobante_autorizado",
    "AfipFiscalConfigError",
    "AfipConnectionError",
    "AfipMappingError",
    "AfipWsfeServiceError"
]