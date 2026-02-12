#!/usr/bin/env python3
"""
Diagnóstico: Verificar discrepancias entre datos en Google Sheets vs lo que carga TablasHandler
"""
import sys
sys.path.insert(0, '/home/sgi_user/proyectos/sistema_gestion_ima')

from back.database import SessionLocal
from back.modelos import ConfiguracionEmpresa
from back.utils.tablas_handler import TablasHandler
import gspread

def main():
    print("\n" + "="*90)
    print("🔍 DIAGNÓSTICO: Conteo Real de Artículos en Google Sheets")
    print("="*90)
    
    db = SessionLocal()
    
    try:
        # Obtener config
        config = db.get(ConfiguracionEmpresa, 32)
        if not config or not config.link_google_sheets:
            print("❌ No hay configuración de Google Sheets")
            return
        
        sheet_id = config.link_google_sheets
        print(f"✅ SHEET_ID: {sheet_id}")
        
        # Conectar directamente a Google Sheets
        print("\n📋 Conectando directamente a Google Sheets...")
        cred_path = '/home/sgi_user/proyectos/sistema_gestion_ima/back/credencial_IA.json'
        sa = gspread.service_account(filename=cred_path)
        spreadsheet = sa.open_by_key(sheet_id)
        print(f"✅ Spreadsheet: {spreadsheet.title}")
        
        # Listar todas las hojas
        print("\n📑 Hojas disponibles:")
        print("-" * 90)
        todas_hojas = spreadsheet.worksheets()
        for i, hoja in enumerate(todas_hojas, 1):
            print(f"  {i}. '{hoja.title}' ({hoja.row_count} filas, {hoja.col_count} columnas)")
        
        # Contar artículos en cada hoja posible
        hojas_buscadas = ['stock', 'articulos', 'productos', 'inventory', 'inventario', 'items']
        print("\n📊 Contando artículos por hoja:")
        print("-" * 90)
        
        totales = {
            'raw': 0,
            'con_codigo': 0,
            'codigos_unicos': set(),
        }
        
        for nombre_hoja in hojas_buscadas:
            try:
                worksheet = spreadsheet.worksheet(nombre_hoja)
                registros = worksheet.get_all_records()
                
                if not registros:
                    print(f"  {nombre_hoja:15} - Vacía")
                    continue
                
                # Contar registros
                total_registros = len(registros)
                registros_con_codigo = len([r for r in registros if r.get('Código', '').strip()])
                
                # Contar códigos únicos
                codigos = [str(r.get('Código', '')).strip() for r in registros if r.get('Código', '').strip()]
                codigos_unicos = set(codigos)
                duplicados = len(codigos) - len(codigos_unicos)
                
                print(f"  {nombre_hoja:15} - {total_registros:3d} registros | {registros_con_codigo:3d} con código | {len(codigos_unicos):3d} códigos únicos | {duplicados:2d} duplicados")
                
                totales['raw'] += total_registros
                totales['con_codigo'] += registros_con_codigo
                totales['codigos_unicos'].update(codigos_unicos)
                
            except gspread.exceptions.WorksheetNotFound:
                pass
            except Exception as e:
                print(f"  {nombre_hoja:15} - Error: {e}")
        
        print(f"\n  {'TOTAL':15} - {totales['raw']} registros | {totales['con_codigo']} con código | {len(totales['codigos_unicos'])} códigos únicos")
        
        # Ahora usar TablasHandler para ver qué retorna
        print("\n🚀 Viendo qué retorna TablasHandler.cargar_articulos():")
        print("-" * 90)
        
        handler = TablasHandler(id_empresa=32, db=db)
        articulos = handler.cargar_articulos()
        
        print(f"✅ TablasHandler retornó: {len(articulos)} artículos")
        
        # Extraer códigos de lo que retorna
        codigos_handler = set([str(a.get('Código', '')).strip() for a in articulos if a.get('Código', '').strip()])
        print(f"✅ Códigos únicos retornados: {len(codigos_handler)}")
        
        # Comparar
        print("\n📊 ANÁLISIS DE DIFERENCIAS:")
        print("-" * 90)
        print(f"Artículos en Sheets:         {len(totales['codigos_unicos'])}")
        print(f"Artículos retorna Handler:  {len(codigos_handler)}")
        print(f"Diferencia:                 {len(totales['codigos_unicos']) - len(codigos_handler)}")
        
        faltantes = totales['codigos_unicos'] - codigos_handler
        if faltantes:
            print(f"\n⚠️  Artículos en Sheet pero NO en Handler ({len(faltantes)}):")
            for cod in sorted(list(faltantes))[:10]:
                print(f"    - {cod}")
            if len(faltantes) > 10:
                print(f"    ... y {len(faltantes) - 10} más")
        
        extras = codigos_handler - totales['codigos_unicos']
        if extras:
            print(f"\n⚠️  Artículos en Handler pero NO en Sheet ({len(extras)}):")
            for cod in sorted(list(extras))[:10]:
                print(f"    - {cod}")
            if len(extras) > 10:
                print(f"    ... y {len(extras) - 10} más")
        
        if not faltantes and not extras:
            print("\n✅ Todos los artículos coinciden entre Sheet y Handler")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
    
    print("\n" + "="*90)

if __name__ == "__main__":
    main()
