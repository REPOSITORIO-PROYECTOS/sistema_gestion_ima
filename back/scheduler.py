"""
Background scheduler para sincronización automática cada 10 segundos
Integrado en el API FastAPI
Sincroniza TODAS las empresas configuradas
"""
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import Session, select
import sys

sys.path.insert(0, '/home/sgi_user/proyectos/sistema_gestion_ima')

from back.database import engine
from back.modelos import Empresa
from back.gestion.actualizaciones.actualizaciones_masivas import (
    sincronizar_articulos_desde_sheets,
    sincronizar_clientes_desde_sheets,
)

logger = logging.getLogger(__name__)

scheduler = None

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
                seconds=10,  # Sincronizar cada 10 segundos
                args=[id_empresa],
                id=f'sync_empresa_{id_empresa}',
                name=f'Sincronización Empresa {id_empresa}',
                replace_existing=True
            )
        
        scheduler.start()
        print(f"✅ Background scheduler iniciado - {len(empresas_a_sincronizar)} empresa(s) - Sincronización cada 10 segundos")
        
        # Imprimir próximas ejecuciones
        for job in scheduler.get_jobs():
            print(f"  - {job.name}: Próxima ejecución: {job.next_run_time}")

def shutdown_scheduler():
    """Detener el scheduler"""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        print("✅ Background scheduler detenido")
