# back/main.py

import os
from back.api.blueprints import admin_router, afip_tools_router, articulos_router, auth_router,actualizacion_masiva_router,clientes_router, configuracion_router, empresa_router, importaciones_router, proveedores_router, comprobantes_router, mesas_router, scanner_router, ordenes_router, impresion_router
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


# Importamos los routers que acabamos de crear
from back.api.blueprints import caja_router
from back.api.blueprints import usuarios_router


# Importamos la configuración para la conexión inicial y CORS
from back import config # (y otros que necesites)
from back.utils.mysql_handler import get_db_connection
from back.database import create_db_and_tables

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
    try:
        print("⛏️ Creando tablas nuevas si faltan...")
        create_db_and_tables()
    except Exception as e:
        print(f"⚠️ No se pudieron crear tablas automáticamente: {e}")


@app.on_event("shutdown")
def shutdown_event():
    """
    Código que se ejecuta al detener la API.
    """
    print("--- Evento de Cierre de la API ---")


# --- Inclusión de Routers ---
# Aquí es donde conectamos los archivos de endpoints a la aplicación principal.
app.include_router(caja_router.router)
app.include_router(admin_router.router)
app.include_router(auth_router.router)
app.include_router(articulos_router.router)
app.include_router(actualizacion_masiva_router.router)
app.include_router(clientes_router.router)
app.include_router(usuarios_router.router)
app.include_router(importaciones_router.router)
app.include_router(proveedores_router.router)
app.include_router(configuracion_router.router)
app.include_router(empresa_router.router)  # Asegúrate de importar el router de empresas
app.include_router(comprobantes_router.router)
app.include_router(afip_tools_router.router)
app.include_router(mesas_router.router)
app.include_router(scanner_router.router)
app.include_router(ordenes_router.router)
app.include_router(impresion_router.router)


# --- Endpoint Raíz ---
@app.get("/", tags=["General"])
async def read_root():
    """
    Endpoint principal que da la bienvenida a la API.
    """
    return {"message": "Bienvenido a la API del Sistema de Gestión IMA v1.0. La arquitectura ha sido actualizada."}

app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
# Montamos también en /api/static para que coincida con next.config.ts images.remotePatterns
app.mount("/api/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="api_static")
