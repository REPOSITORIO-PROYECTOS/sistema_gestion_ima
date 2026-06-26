# back/main.py

import logging
import os
import threading
from back.api.blueprints import admin_router, afip_tools_router, articulos_router, auth_router,actualizacion_masiva_router,clientes_router, configuracion_router, empresa_router, importaciones_router, proveedores_router, comprobantes_router, mesas_router, scanner_router, ordenes_router, impresion_router, modo_especial_router
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

logger = logging.getLogger(__name__)

# La inicialización pesada corre en hilo: Uvicorn abre el puerto al instante (menos "servidor no responde").
_startup_complete = threading.Event()


def _startup_heavy() -> None:
    try:
        print("--- Evento de Inicio de la API (segundo plano) ---")
        print(f"Verificando conexión a la base de datos '{config.DB_NAME}' en '{config.DB_HOST}'...")
        conn = get_db_connection()
        if conn:
            print("✅ Conexión a la base de datos MySQL verificada exitosamente.")
            conn.close()
        else:
            print("❌ ERROR CRÍTICO: No se pudo conectar a la base de datos MySQL.")

        if config.GOOGLE_SHEET_ID:
            print(f"ℹ️  Google Sheets configurado para reportes (ID: {config.GOOGLE_SHEET_ID[:10]}...).")
        try:
            print("⛏️ Creando tablas nuevas si faltan...")
            create_db_and_tables()
        except Exception as e:
            print(f"⚠️ No se pudieron crear tablas automáticamente: {e}")

        try:
            from back.scheduler import init_scheduler

            init_scheduler()
            print("✅ Background scheduler de sincronización iniciado")
        except Exception as e:
            print(f"⚠️ No se pudo iniciar el scheduler: {e}")
    except Exception as e:
        logger.exception("Fallo en inicialización en segundo plano: %s", e)
    finally:
        _startup_complete.set()


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

# --- Verificación inicial en segundo plano (no bloquea el bind de Uvicorn) ---
@app.on_event("startup")
def startup_event():
    print("--- API escuchando; inicialización pesada en segundo plano ---")
    threading.Thread(target=_startup_heavy, daemon=True, name="ima-api-startup").start()


@app.on_event("shutdown")
def shutdown_event():
    """
    Código que se ejecuta al detener la API.
    """
    print("--- Evento de Cierre de la API ---")
    try:
        from back.scheduler import shutdown_scheduler
        shutdown_scheduler()
    except Exception as e:
        print(f"⚠️ No se pudo detener el scheduler correctamente: {e}")


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
app.include_router(modo_especial_router.router)


@app.get("/api/health", tags=["General"])
def api_health():
    """
    Ligero: responde enseguida. `startup_complete` indica si ya corrió DB + tablas + scheduler.
    Útil para Nginx/Hostinger y para ver si el proceso está arriba sin esperar el arranque pesado.
    """
    return {
        "status": "ready" if _startup_complete.is_set() else "starting",
        "startup_complete": _startup_complete.is_set(),
    }


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
