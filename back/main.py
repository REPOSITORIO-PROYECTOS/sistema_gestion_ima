# back/main.py
from back.api import blueprints
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


# Importamos los routers que acabamos de crear


# Importamos la configuración para la conexión inicial y CORS
from back import config # (y otros que necesites)
from back.utils.mysql_handler import get_db_connection

# --- Inicialización de FastAPI ---
app = FastAPI(
    title="API Sistema de Gestión IMA",
    description="API para interactuar con el backend del sistema de gestión, ahora con arquitectura de routers.",
    version="1.0.0" # ¡Versión 1.0.0 de la nueva arquitectura!
)

# --- Configuración de CORS ---
origins = [
    "http://localhost",
    "http://localhost:3000",
    "https://swingjugos.netlify.app",
    "https://sistema-ima.sistemataup.online",
    "https://www.sistema-ima.sistemataup.online",
    "https://imaconsultora.netlify.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Verificación Inicial ---
@app.on_event("startup")
def startup_event():
    """
    Código que se ejecuta una sola vez al iniciar la API.
    Ideal para verificar conexiones a bases de datos.
    """
    print("--- Evento de Inicio de la API ---")
    print(f"Verificando conexión a la base de datos '{config.DB_NAME}' en '{config.DB_HOST}'...")
    conn = get_db_connection()
    if conn:
        print("✅ Conexión a la base de datos MySQL verificada exitosamente.")
        conn.close()
    else:
        print("❌ ERROR CRÍTICO: No se pudo conectar a la base de datos MySQL.")
        # En un entorno real, podrías decidir si la app debe detenerse aquí.
    
    if config.GOOGLE_SHEET_ID:
        print(f"ℹ️  Google Sheets configurado para reportes (ID: {config.GOOGLE_SHEET_ID[:10]}...).")


# --- Inclusión de Routers ---
# Aquí es donde conectamos los archivos de endpoints a la aplicación principal.
app.include_router(blueprints.caja_router.router, prefix="/caja", tags=["Caja"])
app.include_router(blueprints.admin_router.router, prefix="/admin", tags=["Admin"])
app.include_router(blueprints.auth_router.router, prefix="/auth", tags=["Autenticación"])
app.include_router(blueprints.articulos_router.router, prefix="/articulos", tags=["Artículos"])
app.include_router(blueprints.actualizacion_masiva_router.router, prefix="/masiva", tags=["Actualización Masiva"])
app.include_router(blueprints.clientes_router.router, prefix="/clientes", tags=["Clientes"])
app.include_router(blueprints.usuarios_router.router, prefix="/usuarios", tags=["Usuarios"])
app.include_router(blueprints.importaciones_router.router, prefix="/importaciones", tags=["Importaciones"])
app.include_router(blueprints.proveedores_router.router, prefix="/proveedores", tags=["Proveedores"])
app.include_router(blueprints.configuracion_router.router, prefix="/configuracion", tags=["Configuración"])
app.include_router(blueprints.empresa_router.router, prefix="/empresa", tags=["Empresa"])
app.include_router(blueprints.comprobantes_router.router, prefix="/comprobantes", tags=["Comprobantes"])



# --- Endpoint Raíz ---
@app.get("/", tags=["General"])
async def read_root():
    """
    Endpoint principal que da la bienvenida a la API.
    """
    return {"message": "Bienvenido a la API del Sistema de Gestión IMA v1.0. La arquitectura ha sido actualizada."}

app.mount("/static", StaticFiles(directory="back/static"), name="static")
