# back/database.py
# VERSIÓN CORREGIDA Y COMPATIBLE

import os
from sqlmodel import create_engine, Session, SQLModel
from sqlalchemy.orm import sessionmaker # <--- 1. IMPORTAMOS sessionmaker
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME")

if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_NAME]):
    raise ValueError("Faltan variables de entorno para la base de datos. Asegúrate de que el archivo .env esté configurado correctamente.")

# Línea corregida
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def _env_truthy(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


# Solo en APP_ENV=development/local y SQL_ECHO=true (nunca en producción).
_app_env = os.getenv("APP_ENV", "production").strip().lower()
_is_dev_env = _app_env in ("dev", "development", "local")
_sql_echo = _is_dev_env and _env_truthy("SQL_ECHO", "false")

_pool_size = _env_int("DB_POOL_SIZE", 20)
_max_overflow = _env_int("DB_MAX_OVERFLOW", 20)
_pool_timeout = _env_int("DB_POOL_TIMEOUT", 30)

engine = create_engine(
    DATABASE_URL,
    echo=_sql_echo,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=_pool_size,
    max_overflow=_max_overflow,
    pool_timeout=_pool_timeout,
)

# --- ESTA ES LA ADICIÓN CLAVE ---
# Creamos una "Fábrica de Sesiones" que puede ser importada y usada por scripts externos.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session) # <--- 2. AÑADIMOS ESTA LÍNEA

# --- TU CÓDIGO ORIGINAL SE MANTIENE ---
# Esta función sigue siendo perfecta para la inyección de dependencias de FastAPI.
def get_db():
    db = SessionLocal() # Ahora usamos SessionLocal para crear la sesión
    try:
        yield db
    finally:
        db.close()

def create_db_and_tables():
    # Para evitar importaciones circulares, importamos los modelos aquí dentro
    from back import modelos 
    print("Creando tablas en la base de datos...")
    SQLModel.metadata.create_all(engine)
    print("Tablas creadas exitosamente.")