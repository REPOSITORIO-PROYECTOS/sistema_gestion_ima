#!/usr/bin/env python3
"""
Script para probar la sincronización manual de artículos de admin_ropa
"""
import sys
sys.path.insert(0, '/home/sgi_user/proyectos/sistema_gestion_ima')

from sqlmodel import Session, select
from back.database import engine
from back.gestion.sincronizacion_manager import sincronizar_articulos_desde_sheet
from sqlalchemy import text

# ID de empresa para Distribuidora El Negro
ID_EMPRESA = 33

print(f"\n{'='*60}")
print(f"PRUEBA DE SINCRONIZACIÓN MANUAL - Empresa ID: {ID_EMPRESA}")
print(f"{'='*60}\n")

with Session(engine) as db:
    try:
        print("Iniciando sincronización...")
        resultado = sincronizar_articulos_desde_sheet(db, ID_EMPRESA)
        
        print(f"\n{'='*60}")
        print("RESULTADO DE LA SINCRONIZACIÓN:")
        print(f"{'='*60}")
        for clave, valor in resultado.items():
            print(f"  {clave}: {valor}")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"\n❌ ERROR CAPTURADO:")
        print(f"   Tipo: {type(e).__name__}")
        print(f"   Mensaje: {str(e)}")
        import traceback
        print(f"\n   Traceback completo:")
        traceback.print_exc()
