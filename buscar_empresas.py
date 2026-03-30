#!/usr/bin/env python3
"""
Script para buscar empresas en la base de datos y verificar su configuración de Google Sheets.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'back'))

from sqlmodel import Session, select
from back.database import engine
from back.modelos import Empresa, ConfiguracionEmpresa

def buscar_empresas():
    """Busca todas las empresas y muestra su información."""
    with Session(engine) as session:
        # Obtener TODAS las empresas
        statement = select(Empresa).order_by(Empresa.id)
        empresas = session.exec(statement).all()
        
        print("\n" + "="*80)
        print("📋 LISTADO DE TODAS LAS EMPRESAS EN EL SISTEMA")
        print("="*80 + "\n")
        
        if not empresas:
            print("❌ No hay empresas registradas en la base de datos.")
            return
        
        for empresa in empresas:
            print(f"\n{'─'*80}")
            print(f"🏢 ID: {empresa.id}")
            print(f"   Nombre Legal: {empresa.nombre_legal}")
            print(f"   Nombre Fantasía: {empresa.nombre_fantasia or 'N/A'}")
            print(f"   CUIT: {empresa.cuit}")
            print(f"   Activa: {'✅ Sí' if empresa.activa else '❌ No'}")
            print(f"   Fecha de Creación: {empresa.creada_en.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Obtener configuración
            config = session.get(ConfiguracionEmpresa, empresa.id)
            if config:
                print(f"   Google Sheets Link: {config.link_google_sheets or '❌ NO CONFIGURADO'}")
                print(f"   Nombre Negocio: {config.nombre_negocio or 'N/A'}")
            else:
                print(f"   ❌ NO TIENE CONFIGURACIÓN")
        
        print(f"\n{'─'*80}")
        print(f"\n📊 TOTAL DE EMPRESAS: {len(empresas)}")
        
        # Buscar empresas con "Swing" en el nombre
        print("\n" + "="*80)
        print("🔍 BÚSQUEDA: EMPRESAS CON 'SWING' EN EL NOMBRE")
        print("="*80 + "\n")
        
        swing_empresas = [e for e in empresas if 'swing' in e.nombre_legal.lower() or 
                         (e.nombre_fantasia and 'swing' in e.nombre_fantasia.lower())]
        
        if swing_empresas:
            for empresa in swing_empresas:
                print(f"\n✅ ENCONTRADA:")
                print(f"   ID: {empresa.id}")
                print(f"   Nombre Legal: {empresa.nombre_legal}")
                print(f"   Nombre Fantasía: {empresa.nombre_fantasia or 'N/A'}")
                print(f"   CUIT: {empresa.cuit}")
                print(f"   Activa: {'✅ Sí' if empresa.activa else '❌ No'}")
                
                config = session.get(ConfiguracionEmpresa, empresa.id)
                if config:
                    print(f"   Google Sheets: {config.link_google_sheets or '❌ NO CONFIGURADO'}")
                else:
                    print(f"   ❌ NO TIENE CONFIGURACIÓN")
        else:
            print("❌ No se encontraron empresas con 'Swing' en el nombre.")
        
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    buscar_empresas()
