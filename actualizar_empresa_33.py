#!/usr/bin/env python3
"""
Script para actualizar la empresa 33:
- Nombre legal: Lucas Pasten
- Punto de venta: 4
"""

import sys
sys.path.insert(0, '/home/sgi_user/proyectos/sistema_gestion_ima')

from sqlmodel import Session, select
from back.database import engine
from back.modelos import Empresa, ConfiguracionEmpresa

def actualizar_empresa_33():
    """Actualiza la empresa 33 con los datos solicitados"""
    
    with Session(engine) as db:
        try:
            # 1. Obtener la empresa 33
            empresa = db.exec(select(Empresa).where(Empresa.id == 33)).first()
            
            if not empresa:
                print(f"❌ Error: Empresa con ID 33 no encontrada")
                return False
            
            print(f"✅ Empresa encontrada:")
            print(f"   - Nombre legal actual: {empresa.nombre_legal}")
            print(f"   - CUIT: {empresa.cuit}")
            
            # 2. Obtener la configuración de la empresa
            config = db.exec(
                select(ConfiguracionEmpresa).where(ConfiguracionEmpresa.id_empresa == 33)
            ).first()
            
            if not config:
                print(f"❌ Error: Configuración de empresa 33 no encontrada")
                return False
            
            print(f"✅ Configuración encontrada:")
            print(f"   - Punto de venta actual: {config.afip_punto_venta_predeterminado}")
            
            # 3. Actualizar el nombre legal de la empresa
            empresa.nombre_legal = "Lucas Pasten"
            print(f"\n📝 Actualizando nombre legal a: {empresa.nombre_legal}")
            
            # 4. Actualizar el punto de venta
            config.afip_punto_venta_predeterminado = 3
            print(f"📝 Actualizando punto de venta a: {config.afip_punto_venta_predeterminado}")
            
            # 5. Guardar los cambios
            db.add(empresa)
            db.add(config)
            db.commit()
            
            print(f"\n✅ ¡Cambios realizados exitosamente!")
            print(f"   - Nombre legal: {empresa.nombre_legal}")
            print(f"   - Punto de venta: {config.afip_punto_venta_predeterminado}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error durante la actualización: {e}")
            db.rollback()
            return False

if __name__ == "__main__":
    print("=" * 60)
    print("ACTUALIZAR EMPRESA 33")
    print("=" * 60)
    
    exito = actualizar_empresa_33()
    
    print("=" * 60)
    sys.exit(0 if exito else 1)
