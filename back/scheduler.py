"""
Background scheduler para sincronización automática configurable
Integrado en el API FastAPI
Sincroniza TODAS las empresas configuradas
"""
import logging
import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import Session, select
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from back.database import engine
from back.modelos import Empresa
from back.gestion.sincronizacion_orquestador import sincronizar_empresa_unificada

logger = logging.getLogger(__name__)

scheduler = None

def _get_int_env(name: str, default: int) -> int:
    valor = os.getenv(name, str(default))
    try:
        return int(valor)
    except (TypeError, ValueError):
        logger.warning(f"Valor inválido para {name}={valor!r}. Usando default {default}.")
        return default


def _get_bool_env(name: str, default: bool) -> bool:
    valor = os.getenv(name)
    if valor is None:
        return default
    return str(valor).strip().lower() in {"1", "true", "yes", "y", "on"}

SYNC_INTERVAL_SECONDS = _get_int_env("SYNC_INTERVAL_SECONDS", 60)
SYNC_JOB_MISFIRE_GRACE_SECONDS = _get_int_env("SYNC_JOB_MISFIRE_GRACE_SECONDS", 30)
SYNC_INCLUDE_PROVEEDORES = _get_bool_env("SYNC_INCLUDE_PROVEEDORES", False)
SYNC_REFRESH_COMPANIES_SECONDS = _get_int_env("SYNC_REFRESH_COMPANIES_SECONDS", 120)

# Requisito operativo: sincronización automática fija cada 10 segundos.
SYNC_INTERVAL_SECONDS = 10

def obtener_todas_las_empresas():
    """Obtiene todas las empresas activas de la base de datos"""
    try:
        with Session(engine) as db:
            empresas = db.exec(select(Empresa).where(Empresa.activa == True)).all()
            return [emp.id for emp in empresas if emp.id is not None]
    except Exception as e:
        print(f"⚠️ Error al obtener empresas: {e}")
        return []

def sincronizar_empresa_background(id_empresa: int):
    """Función que se ejecuta en background cada 5 minutos"""
    try:
        with Session(engine) as db:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] Iniciando sincronización automática para empresa {id_empresa}...")
            resultado = sincronizar_empresa_unificada(
                db=db,
                id_empresa=id_empresa,
                incluir_articulos=True,
                incluir_clientes=True,
                incluir_proveedores=SYNC_INCLUDE_PROVEEDORES,
                detener_en_error=False,
            )
            status_sync = resultado.get("status", "unknown")
            if status_sync == "busy":
                print(f"  ℹ️ Sincronización omitida (empresa {id_empresa} ocupada): {resultado.get('message')}")
            else:
                print(f"  ✓ Resultado sincronización: {resultado}")
            
            print(f"[{timestamp}] ✅ Sincronización completada")
            
    except Exception as e:
        print(f"❌ Error en sincronización: {e}")
        logger.error(f"Error en sincronización automática: {e}", exc_info=True)


def _reconciliar_jobs_empresas():
    """Sincroniza jobs del scheduler con las empresas activas actuales."""
    global scheduler
    if scheduler is None:
        return

    empresas_activas = set(obtener_todas_las_empresas())
    jobs_actuales = {job.id: job for job in scheduler.get_jobs()}
    jobs_empresas_ids = {
        job_id for job_id in jobs_actuales.keys() if job_id.startswith("sync_empresa_")
    }

    # Crear faltantes
    for id_empresa in empresas_activas:
        job_id = f"sync_empresa_{id_empresa}"
        if job_id not in jobs_actuales:
            scheduler.add_job(
                sincronizar_empresa_background,
                'interval',
                seconds=SYNC_INTERVAL_SECONDS,
                args=[id_empresa],
                id=job_id,
                name=f'Sincronización Empresa {id_empresa}',
                replace_existing=True,
                max_instances=1,
                coalesce=True,
                misfire_grace_time=SYNC_JOB_MISFIRE_GRACE_SECONDS,
            )
            print(f"➕ Job agregado para empresa activa {id_empresa}")

    # Eliminar jobs de empresas inactivas o inexistentes
    for job_id in jobs_empresas_ids:
        id_empresa_job = int(job_id.replace("sync_empresa_", ""))
        if id_empresa_job not in empresas_activas:
            scheduler.remove_job(job_id)
            print(f"➖ Job removido para empresa inactiva {id_empresa_job}")

def init_scheduler():
    """Inicializar el scheduler con TODAS las empresas activas"""
    global scheduler
    
    if scheduler is None:
        scheduler = BackgroundScheduler()

        # Carga inicial de jobs de empresas activas
        _reconciliar_jobs_empresas()

        # Job de mantenimiento: refresca altas/bajas de empresas sin reiniciar API
        scheduler.add_job(
            _reconciliar_jobs_empresas,
            'interval',
            seconds=SYNC_REFRESH_COMPANIES_SECONDS,
            id='sync_refresh_empresas',
            name='Reconciliación de empresas para sincronización',
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=max(SYNC_JOB_MISFIRE_GRACE_SECONDS, 30),
        )
        
        scheduler.start()
        print(
            f"✅ Background scheduler iniciado - "
            f"Sincronización cada {SYNC_INTERVAL_SECONDS} segundos - "
            f"Refresh de empresas cada {SYNC_REFRESH_COMPANIES_SECONDS} segundos - "
            f"Proveedores={'ON' if SYNC_INCLUDE_PROVEEDORES else 'OFF'}"
        )
        
        # Imprimir próximas ejecuciones
        for job in scheduler.get_jobs():
            print(f"  - {job.name}: Próxima ejecución: {job.next_run_time}")

def shutdown_scheduler():
    """Detener el scheduler"""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        print("✅ Background scheduler detenido")
