# back/__init__.py
# nuestro `__init__.py` está **vacío**, Python no sabe que `modelos` es algo que se puede importar directamente desde `back`.
# Contenido para: back/api/blueprints/__init__.py

# Añade este print para estar 100% seguros de que se está ejecutando
print("<<<<< INICIALIZANDO EL PAQUETE 'blueprints' >>>>>")

from . import admin_router
from . import articulos_router
from . import auth_router
from . import actualizacion_masiva_router
from . import clientes_router
from . import configuracion_router
from . import empresa_router
from . import importaciones_router
from . import proveedores_router
from . import comprobantes_router
from . import caja_router   # <-- LA LÍNEA CLAVE QUE FALTABA
from . import usuarios_router