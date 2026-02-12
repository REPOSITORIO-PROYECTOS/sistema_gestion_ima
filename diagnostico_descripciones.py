#!/usr/bin/env python3
"""
Diagnóstico: Verificar artículos sin descripción en Google Sheets y Base de Datos
"""
import sys
sys.path.insert(0, '/home/sgi_user/proyectos/sistema_gestion_ima')

from back.database import SessionLocal
from back.modelos import ConfiguracionEmpresa, Articulo
from back.utils.tablas_handler import TablasHandler
from sqlmodel import select
import gspread

def main():
    print("\n" + "="*90)
    print("🔍 DIAGNÓSTICO: Artículos sin Descripción")
    print("="*90)
    
    db = SessionLocal()
    
    try:
        # ═══════════════════════════════════════════════════════════════
        # 1. VERIFICAR GOOGLE SHEETS
        # ═══════════════════════════════════════════════════════════════
        print("\n📋 Paso 1: Analizando Google Sheets...")
        print("-" * 90)
        
        config = db.get(ConfiguracionEmpresa, 32)
        sheet_id = config.link_google_sheets
        
        cred_path = '/home/sgi_user/proyectos/sistema_gestion_ima/back/credencial_IA.json'
        sa = gspread.service_account(filename=cred_path)
        spreadsheet = sa.open_by_key(sheet_id)
        
        worksheet = spreadsheet.worksheet('stock')
        registros = worksheet.get_all_records()
        
        # Analizar descripciones
        print(f"Total de registros: {len(registros)}")
        
        # Buscar columnas potenciales para descripción
        primer_registro = registros[0]
        print(f"\nColumnas disponibles en el sheet:")
        for i, col in enumerate(primer_registro.keys(), 1):
            print(f"  {i:2d}. {col}")
        
        # Contar artículos sin descripción
        sin_desc_sheets = []
        con_desc_sheets = []
        
        for registro in registros:
            codigo = registro.get('Código', '')
            nombre = registro.get('nombre', '').strip() if registro.get('nombre') else ''
            descripcion = registro.get('Descripción', '').strip() if registro.get('Descripción') else ''
            
            if not nombre and not descripcion:
                sin_desc_sheets.append(codigo)
            else:
                con_desc_sheets.append({
                    'codigo': codigo,
                    'nombre': nombre[:30] if nombre else '[vacío]',
                    'descripcion': descripcion[:30] if descripcion else '[vacío]'
                })
        
        print(f"\n📊 En Google Sheets:")
        print(f"  Artículos CON descripción/nombre: {len(con_desc_sheets)}")
        print(f"  Artículos SIN descripción: {len(sin_desc_sheets)}")
        
        if sin_desc_sheets:
            print(f"\n  Códigos SIN descripción:")
            for cod in sin_desc_sheets[:10]:
                print(f"    - {cod}")
            if len(sin_desc_sheets) > 10:
                print(f"    ... y {len(sin_desc_sheets) - 10} más")
        
        # ═══════════════════════════════════════════════════════════════
        # 2. VERIFICAR QUÉ RETORNA TABLASHANDLER
        # ═══════════════════════════════════════════════════════════════
        print("\n📋 Paso 2: Verificando TablasHandler.cargar_articulos()...")
        print("-" * 90)
        
        handler = TablasHandler(id_empresa=32, db=db)
        articulos_handler = handler.cargar_articulos()
        
        print(f"Artículos retornados: {len(articulos_handler)}")
        
        sin_desc_handler = []
        con_desc_handler = []
        
        for art in articulos_handler:
            codigo = art.get('Código', '')
            descripcion = art.get('descripcion', '').strip() if art.get('descripcion') else ''
            nombre = art.get('nombre', '').strip() if art.get('nombre') else ''
            
            if not descripcion:
                sin_desc_handler.append(codigo)
            else:
                con_desc_handler.append({
                    'codigo': codigo,
                    'descripcion': descripcion[:40]
                })
        
        print(f"\n📊 En TablasHandler:")
        print(f"  Artículos CON descripción: {len(con_desc_handler)}")
        print(f"  Artículos SIN descripción: {len(sin_desc_handler)}")
        
        if sin_desc_handler:
            print(f"\n  Primeros 10 sin descripción:")
            for cod in sin_desc_handler[:10]:
                print(f"    - {cod}")
        
        # ═══════════════════════════════════════════════════════════════
        # 3. VERIFICAR BASE DE DATOS
        # ═══════════════════════════════════════════════════════════════
        print("\n📋 Paso 3: Verificando Base de Datos...")
        print("-" * 90)
        
        articulos_db = db.exec(
            select(Articulo).where(Articulo.id_empresa == 32)
        ).all()
        
        sin_desc_db = []
        con_desc_db = []
        
        for art in articulos_db:
            if not art.descripcion or art.descripcion.strip() == '':
                sin_desc_db.append(art.codigo_interno)
            else:
                con_desc_db.append({
                    'codigo': art.codigo_interno,
                    'descripcion': art.descripcion[:40]
                })
        
        print(f"Artículos en DB: {len(articulos_db)}")
        print(f"\n📊 En Base de Datos:")
        print(f"  Artículos CON descripción: {len(con_desc_db)}")
        print(f"  Artículos SIN descripción: {len(sin_desc_db)}")
        
        if sin_desc_db:
            print(f"\n  Primeros 10 sin descripción:")
            for cod in sin_desc_db[:10]:
                print(f"    - {cod}")
        
        # ═══════════════════════════════════════════════════════════════
        # 4. ANÁLISIS COMPARATIVO
        # ═══════════════════════════════════════════════════════════════
        print("\n📋 Paso 4: Análisis Comparativo")
        print("-" * 90)
        
        # Mostrar un ejemplo de artículo sin descripción
        if sin_desc_handler:
            cod_ejemplo = sin_desc_handler[0]
            print(f"\nEjemplo: Artículo '{cod_ejemplo}'")
            
            # Buscar en sheets
            para_sheets = next((r for r in registros if r.get('Código') == cod_ejemplo), None)
            if para_sheets:
                print(f"  En Sheets:")
                print(f"    - nombre: '{para_sheets.get('nombre', '')}'")
                print(f"    - Descripción: '{para_sheets.get('Descripción', '')}'")
                print(f"    - Otras columnas descriptivas:")
                for key in para_sheets.keys():
                    if 'desc' in key.lower() or 'name' in key.lower() or 'nombre' in key.lower():
                        valor = para_sheets.get(key, '')
                        if valor:
                            print(f"      - {key}: {str(valor)[:50]}")
            
            # Buscar en handler
            para_handler = next((a for a in articulos_handler if a.get('Código') == cod_ejemplo), None)
            if para_handler:
                print(f"  En TablasHandler (mapeado):")
                print(f"    - descripcion: '{para_handler.get('descripcion', '')}'")
            
            # Buscar en DB
            para_db = next((a for a in articulos_db if a.codigo_interno == cod_ejemplo), None)
            if para_db:
                print(f"  En DB (sincronizado):")
                print(f"    - descripcion: '{para_db.descripcion}'")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
    
    print("\n" + "="*90)

if __name__ == "__main__":
    main()
