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

sys.path.insert(0, '/home/sgi_user/proyectos/sistema_gestion_ima')

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

# Requisito operativo: sincronización automática fija cada 10 segundos.
SYNC_INTERVAL_SECONDS = 10

def obtener_todas_las_empresas():
    """Obtiene todas las empresas activas de la base de datos"""
    try:
        with Session(engine) as db:
            empresas = db.exec(select(Empresa).where(Empresa.activa == True)).all()
            return [emp.id_empresa for emp in empresas]
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
            print(f"  ✓ Resultado sincronización: {resultado}")
            
            print(f"[{timestamp}] ✅ Sincronización completada")
            
    except Exception as e:
        print(f"❌ Error en sincronización: {e}")
        logger.error(f"Error en sincronización automática: {e}", exc_info=True)

def init_scheduler():
    """Inicializar el scheduler con TODAS las empresas activas"""
    global scheduler
    
    if scheduler is None:
        scheduler = BackgroundScheduler()
        
        # Obtener todas las empresas activas
        empresas_a_sincronizar = obtener_todas_las_empresas()
        
        if not empresas_a_sincronizar:
            print("⚠️ No hay empresas activas para sincronizar")
            return
        
        print(f"📋 Empresas a sincronizar: {empresas_a_sincronizar}")
        
        # Agregar jobs para cada empresa
        for id_empresa in empresas_a_sincronizar:
            scheduler.add_job(
                sincronizar_empresa_background,
                'interval',
                seconds=SYNC_INTERVAL_SECONDS,
                args=[id_empresa],
                id=f'sync_empresa_{id_empresa}',
                name=f'Sincronización Empresa {id_empresa}',
                replace_existing=True,
                max_instances=1,
                coalesce=True,
                misfire_grace_time=SYNC_JOB_MISFIRE_GRACE_SECONDS,
            )
        
        scheduler.start()
        print(
            f"✅ Background scheduler iniciado - {len(empresas_a_sincronizar)} empresa(s) - "
            f"Sincronización cada {SYNC_INTERVAL_SECONDS} segundos - "
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
