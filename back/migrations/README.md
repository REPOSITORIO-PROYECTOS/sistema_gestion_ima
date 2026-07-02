# Migraciones de Base de Datos

## Agregar columna catalogo_version

Ruta del script: back/migrations/20260122_add_catalogo_version.sql

Descripción: añade la columna `catalogo_version INT NOT NULL DEFAULT 0` a la tabla `configuracion_empresa`. Requerida para el auto-refresco del catálogo en front.

Aplicación (MySQL):

1. Ubicarse en el servidor con acceso a la base de datos
2. Ejecutar:
   mysql -u <usuario> -p <nombre_db> < back/migrations/20260122_add_catalogo_version.sql

Verificación:
- SELECT catalogo_version FROM configuracion_empresa LIMIT 1;
- Debe existir y devolver 0 por defecto
