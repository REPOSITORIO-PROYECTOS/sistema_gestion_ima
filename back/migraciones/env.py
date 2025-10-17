# back/migraciones/env.py

import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# --- INICIO DE LA CONFIGURACIÓN DE RUTA ---
# Esto asegura que Python pueda encontrar tu paquete 'back' cuando
# ejecutes alembic desde la carpeta raíz del proyecto.
# Añade la ruta actual (.) al path de Python.
sys.path.append(os.getcwd())
# --- FIN DE LA CONFIGURACIÓN DE RUTA ---


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Ahora sí, importamos nuestros módulos
from back import modelos
from back import config as app_config

# Le decimos a Alembic que el "metadata" de nuestras tablas está en SQLModel
target_metadata = modelos.SQLModel.metadata 

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- INICIO DE LA CONFIGURACIÓN DE LA BASE DE DATOS ---
# Construimos la URL de la DB y se la pasamos a Alembic.
# Incluimos el puerto (por defecto 3306 si no está especificado)
db_port = getattr(app_config, 'DB_PORT', '3306')  # Usamos getattr para evitar errores si no existe
db_url = f"mysql+pymysql://{app_config.DB_USER}:{app_config.DB_PASSWORD}@{app_config.DB_HOST}:{db_port}/{app_config.DB_NAME}"
config.set_main_option('sqlalchemy.url', db_url)
# --- FIN DE LA CONFIGURACIÓN DE LA BASE DE DATOS ---


# --- INICIO DE LA CONFIGURACIÓN DEL METADATA ---
# Le decimos a Alembic que las tablas a "autogenerar" están
# definidas en nuestros modelos de SQLModel.
target_metadata = modelos.SQLModel.metadata
# --- FIN DE LA CONFIGURACIÓN DEL METADATA ---


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
