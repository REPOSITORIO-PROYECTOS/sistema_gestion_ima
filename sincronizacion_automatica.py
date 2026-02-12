#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════╗
║  SINCRONIZACIÓN AUTOMÁTICA DE GOOGLE SHEETS - CRON JOB       ║
║  Ejecutado cada 5 minutos (Proceso automático NO MALIGNO)    ║
║  Sistema de Gestión IMA                                       ║
╚═══════════════════════════════════════════════════════════════╝

Este script se ejecuta automáticamente cada 5 minutos vía cron.
Sincroniza artículos, clientes y proveedores desde Google Sheets
a la base de datos local. Es un proceso legítimo del sistema.

Configuración: /etc/crontab o crontab -l
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, '/home/sgi_user/proyectos/sistema_gestion_ima')

from back.gestion.actualizaciones import actualizaciones_masivas as mod_sync
from back.database import SessionLocal
from back.modelos import ConfiguracionEmpresa
from sqlmodel import select

# ═══════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════

LOG_DIR = '/home/sgi_user/proyectos/sistema_gestion_ima/logs'
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, 'cron_sync.log')
EMPRESAS_A_SINCRONIZAR = [32]  # admin_ropa


# ═══════════════════════════════════════════════════════════════
# FUNCIONES DE LOGGING RECONOCIBLE
# ═══════════════════════════════════════════════════════════════

def log(mensaje, nivel="INFO", mostrar_consola=True):
    """
    Registra mensajes con timestamp y nivel claro.
    Fácil de reconocer como proceso automático legítimo.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Emojis y prefijos identificables
    nivel_map = {
        "INFO": "ℹ️  [INFO]",
        "SYNC": "🔄 [SYNC]",
        "SUCCESS": "✅ [OK]",
        "ERROR": "❌ [ERROR]",
        "WARN": "⚠️  [WARN]",
        "START": "🚀 [START]",
        "END": "🏁 [END]",
    }
    
    prefix = nivel_map.get(nivel, f"📌 [{nivel}]")
    mensaje_formateado = f"{timestamp} {prefix} {mensaje}"
    
    # Escribir al log
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(mensaje_formateado + "\n")
    except Exception as e:
        print(f"Error escribiendo log: {e}")
    
    # Mostrar también en consola (para cron)
    if mostrar_consola:
        print(mensaje_formateado)


def main():
    """Ejecuta la sincronización automática - Cron Job"""
    
    log("╔" + "═" * 58 + "╗", "START", False)
    log("║  CRON JOB: SINCRONIZACIÓN AUTOMÁTICA                      ║", "START", False)
    log("╚" + "═" * 58 + "╝", "START", False)
    log("")
    
    db = SessionLocal()
    
    try:
        # Obtener configuración de empresas
        empresas = db.exec(select(ConfiguracionEmpresa)).all()
        
        if not empresas:
            log("❌ No hay empresas configuradas en el sistema", "ERROR")
            return False
        
        log(f"Se sincronizarán {len(EMPRESAS_A_SINCRONIZAR)} empresa(s)...", "SYNC")
        log("")
        
        resultados_totales = {
            'exito': 0,
            'error': 0,
            'articulos_procesados': 0,
            'articulos_protegidos': 0,
        }
        
        # Sincronizar cada empresa
        for id_empresa in EMPRESAS_A_SINCRONIZAR:
            try:
                # Encontrar nombre de empresa
                config = next((c for c in empresas if c.id_empresa == id_empresa), None)
                empresa_nombre = config.nombre_negocio if config else f"Empresa {id_empresa}"
                
                log(f"➜ Sincronizando: {empresa_nombre} (ID: {id_empresa})", "SYNC")
                
                # ─────────────────────────────────────────────────────────
                # SINCRONIZAR ARTÍCULOS
                # ─────────────────────────────────────────────────────────
                try:
                    resultado_art = mod_sync.sincronizar_articulos_desde_sheets(db, id_empresa)
                    
                    leidos = resultado_art.get('leidos', 0)
                    creados = resultado_art.get('creados', 0)
                    actualizados = resultado_art.get('actualizados', 0)
                    eliminados = resultado_art.get('eliminados', 0)
                    protegidos = resultado_art.get('no_eliminados_con_movimientos', 0)
                    
                    log(f"   📦 Artículos: L={leidos} C={creados} U={actualizados} E={eliminados} P={protegidos}", "SYNC")
                    
                    resultados_totales['articulos_procesados'] += leidos or 0
                    resultados_totales['articulos_protegidos'] += protegidos or 0
                    
                except Exception as e:
                    log(f"   ❌ Error en sincronización de artículos: {str(e)}", "ERROR")
                    resultados_totales['error'] += 1
                
                # ─────────────────────────────────────────────────────────
                # SINCRONIZAR CLIENTES
                # ─────────────────────────────────────────────────────────
                try:
                    resultado_cli = mod_sync.sincronizar_clientes_desde_sheets(db, id_empresa)
                    creados_cli = resultado_cli.get('creados', 0)
                    actualizados_cli = resultado_cli.get('actualizados', 0)
                    log(f"   👥 Clientes: C={creados_cli} U={actualizados_cli}", "SYNC")
                except Exception as e:
                    log(f"   ⚠️  Aviso en clientes: {str(e)[:50]}", "WARN")
                
                # ─────────────────────────────────────────────────────────
                # SINCRONIZAR PROVEEDORES
                # ─────────────────────────────────────────────────────────
                try:
                    resultado_prov = mod_sync.sincronizar_proveedores_desde_sheets(db, id_empresa)
                    creados_prov = resultado_prov.get('creados', 0)
                    actualizados_prov = resultado_prov.get('actualizados', 0)
                    log(f"   🏭 Proveedores: C={creados_prov} U={actualizados_prov}", "SYNC")
                except Exception as e:
                    log(f"   ⚠️  Aviso en proveedores: {str(e)[:50]}", "WARN")
                
                log(f"✅ {empresa_nombre} sincronizado exitosamente", "SUCCESS")
                resultados_totales['exito'] += 1
                
            except Exception as e:
                log(f"❌ Error critico para empresa {id_empresa}: {str(e)}", "ERROR")
                resultados_totales['error'] += 1
                continue
        
        # ═════════════════════════════════════════════════════════════════
        # REPORTE FINAL
        # ═════════════════════════════════════════════════════════════════
        log("")
        log("╔" + "═" * 58 + "╗", "END", False)
        log("║  REPORTE DE SINCRONIZACIÓN CRON                         ║", "END", False)
        log("╠" + "═" * 58 + "╣", "END", False)
        log(f"║ ✅ Exitosas: {resultados_totales['exito']:2d}   ❌ Errores: {resultados_totales['error']:2d}                         ║", "END", False)
        log(f"║ 📦 Artículos: {resultados_totales['articulos_procesados']:3d}   🔒 Protegidos: {resultados_totales['articulos_protegidos']:3d}                ║", "END", False)
        log("╚" + "═" * 58 + "╝", "END", False)
        log("")
        
        return resultados_totales['error'] == 0
        
    except Exception as e:
        log(f"❌ ERROR CRÍTICO: {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()


if __name__ == "__main__":
    exito = main()
    sys.exit(0 if exito else 1)
