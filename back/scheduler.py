"""
Background scheduler para sincronización automática cada 5 minutos
Integrado en el API FastAPI
"""
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import Session
import sys

sys.path.insert(0, '/home/sgi_user/proyectos/sistema_gestion_ima')

from back.database import engine
from back.gestion.actualizaciones.actualizaciones_masivas import (
    sincronizar_articulos_desde_sheets,
    sincronizar_clientes_desde_sheets,
)

logger = logging.getLogger(__name__)

# IDs de empresas a sincronizar
EMPRESAS_A_SINCRONIZAR = [32]  # admin_ropa

scheduler = None

def sincronizar_empresa_background(id_empresa: int):
    """Función que se ejecuta en background cada 5 minutos"""
    try:
        with Session(engine) as db:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] Iniciando sincronización automática para empresa {id_empresa}...")
            
            # Sincronizar artículos
            resultado_artículos = sincronizar_articulos_desde_sheets(db, id_empresa)
            print(f"  ✓ Artículos: {resultado_artículos}")
            
            # Sincronizar clientes
            resultado_clientes = sincronizar_clientes_desde_sheets(db, id_empresa)
            print(f"  ✓ Clientes: {resultado_clientes}")
            
            print(f"[{timestamp}] ✅ Sincronización completada")
            
    except Exception as e:
        print(f"❌ Error en sincronización: {e}")
        logger.error(f"Error en sincronización automática: {e}", exc_info=True)

def init_scheduler():
    """Inicializar el scheduler"""
    global scheduler
    
    if scheduler is None:
        scheduler = BackgroundScheduler()
        
        # Agregar jobs para cada empresa
        for id_empresa in EMPRESAS_A_SINCRONIZAR:
            scheduler.add_job(
                sincronizar_empresa_background,
                'interval',
                minutes=5,
                args=[id_empresa],
                id=f'sync_empresa_{id_empresa}',
                name=f'Sincronización Empresa {id_empresa}',
                replace_existing=True
            )
        
        scheduler.start()
        print("✅ Background scheduler iniciado - Sincronización cada 5 minutos")
        
        # Imprimir próximas ejecuciones
        for job in scheduler.get_jobs():
            print(f"  - {job.name}: Próxima ejecución: {job.next_run_time}")

def shutdown_scheduler():
    """Detener el scheduler"""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        print("✅ Background scheduler detenido")
