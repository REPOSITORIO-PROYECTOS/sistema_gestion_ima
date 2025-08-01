# back/__init__.py
# nuestro `__init__.py` está **vacío**, Python no sabe que `modelos` es algo que se puede importar directamente desde `back`.
# Contenido para: back/api/blueprints/__init__.py

# Añade este print para estar 100% seguros de que se está ejecutando
print("<<<<< INICIALIZANDO EL PAQUETE 'blueprints' >>>>>")

from back import admin_router
from back import articulos_router
from back import auth_router
from back import actualizacion_masiva_router
from back import clientes_router
from back import configuracion_router
from back import empresa_router
from back import importaciones_router
from back import proveedores_router
from back import comprobantes_router
from back import caja_router   # <-- LA LÍNEA CLAVE QUE FALTABA
from back import usuarios_router