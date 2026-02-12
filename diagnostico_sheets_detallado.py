#!/usr/bin/env python3
"""
Diagnóstico Detallado de Google Sheets
Verifica qué hojas se están leyendo y cuántos artículos hay en cada una
"""
import sys
sys.path.insert(0, '/home/sgi_user/proyectos/sistema_gestion_ima')

from back.utils.tablas_handler import TablasHandler
from back.database import SessionLocal
from back.modelos import ConfiguracionEmpresa
from sqlmodel import select
import gspread
from back import config

def main():
    print("\n" + "="*80)
    print("🔍 DIAGNÓSTICO DETALLADO DE GOOGLE SHEETS - admin_ropa (Empresa 32)")
    print("="*80)
    
    db = SessionLocal()
    handler = TablasHandler(id_empresa=32, db=db)
    
    try:
        # Obtener configuración de la empresa
        config_empresa = db.get(ConfiguracionEmpresa, 32)
        if not config_empresa or not config_empresa.link_google_sheets:
            print("❌ No hay configuración de Google Sheets para empresa 32")
            return
        
        # Extraer SHEET_ID del link
        # Link típico: https://docs.google.com/spreadsheets/d/SHEET_ID/edit
        sheet_id = None
        if '/d/' in config_empresa.link_google_sheets:
            sheet_id = config_empresa.link_google_sheets.split('/d/')[1].split('/')[0]
        
        print(f"✅ Link Google Sheets: {config_empresa.link_google_sheets[:50]}...")
        print(f"✅ SHEET_ID: {sheet_id}")
        
        # 1. Conectar a Google Sheets
        print("\n📋 Paso 1: Conectando a Google Sheets...")
        # Usar ruta absoluta
        cred_path = '/home/sgi_user/proyectos/sistema_gestion_ima/back/credencial_IA.json'
        sa = gspread.service_account(filename=cred_path)
        spreadsheet = sa.open_by_key(sheet_id)
        print(f"✅ Conectado. Spreadsheet: {spreadsheet.title}")
        
        # 2. Listar todas las hojas
        print("\n📑 Paso 2: Hojas disponibles en el spreadsheet:")
        print("-" * 80)
        todas_hojas = spreadsheet.worksheets()
        for i, hoja in enumerate(todas_hojas, 1):
            print(f"  {i}. '{hoja.title}' - {hoja.row_count} filas, {hoja.col_count} columnas")
        
        # 3. Buscar la hoja de stock/artículos
        print("\n🎯 Paso 3: Buscando hoja de artículos (stock/articulos)...")
        print("-" * 80)
        hoja_stock = None
        for hoja in todas_hojas:
            if 'stock' in hoja.title.lower():
                hoja_stock = hoja
                print(f"✅ Encontrada hoja: '{hoja.title}'")
                break
        
        if not hoja_stock:
            print("❌ No se encontró hoja con 'stock' en el nombre")
            hoja_stock = todas_hojas[0]  # Usar la primera por defecto
            print(f"⚠️  Usando primera hoja: '{hoja_stock.title}'")
        
        # 4. Obtener datos de la hoja
        print(f"\n📊 Paso 4: Leyendo datos de '{hoja_stock.title}'...")
        print("-" * 80)
        registros_crudos = hoja_stock.get_all_records()
        print(f"✅ Total de registros leídos: {len(registros_crudos)}")
        
        if len(registros_crudos) == 0:
            print("❌ La hoja está vacía!")
            return
        
        # 5. Mostrar primeras filas
        print("\n📝 Primeras 3 filas raw del sheet:")
        for i, registro in enumerate(registros_crudos[:3], 1):
            print(f"\n  Fila {i}:")
            for k, v in list(registro.items())[:5]:
                print(f"    {k}: {v}")
        
        # 6. Analizar columnas
        print("\n🔬 Paso 5: Análisis de columnas")
        print("-" * 80)
        if registros_crudos:
            primer_registro = registros_crudos[0]
            columnas = list(primer_registro.keys())
            print(f"Total de columnas: {len(columnas)}")
            print("Columnas encontradas:")
            for i, col in enumerate(columnas, 1):
                print(f"  {i:2d}. {col}")
        
        # 7. Contar artículos únicospor código
        print("\n🔢 Paso 6: Análisis de códigos únicos")
        print("-" * 80)
        codigos = [str(r.get('Código', '')).strip() for r in registros_crudos if r.get('Código')]
        codigos_unicos = set(codigo for codigo in codigos if codigo)
        
        print(f"Total registros en hoja: {len(registros_crudos)}")
        print(f"Registros con código: {len(codigos)}")
        print(f"Códigos únicos: {len(codigos_unicos)}")
        
        # Detectar duplicados
        from collections import Counter
        contador_codigos = Counter(codigos)
        duplicados = {cod: count for cod, count in contador_codigos.items() if count > 1}
        if duplicados:
            print(f"⚠️  Encontrados {len(duplicados)} códigos duplicados:")
            for cod, count in list(duplicados.items())[:5]:
                print(f"     '{cod}': {count} veces")
        
        # 8. Llamar a cargar_articulos() del handler
        print("\n🚀 Paso 7: Llamando a cargar_articulos() del TablasHandler")
        print("-" * 80)
        articulos_handler = handler.cargar_articulos()
        print(f"✅ Articulos retornados por handler: {len(articulos_handler)}")
        
        if articulos_handler:
            print("\nPrimeros 3 artículos del handler:")
            for i, art in enumerate(articulos_handler[:3], 1):
                print(f"\n  {i}. Código: {art.get('Código')} | Nombre: {art.get('nombre', 'SIN NOMBRE')[:40]}")
        
        # 9. Comparación
        print("\n📊 Paso 8: Comparación")
        print("-" * 80)
        print(f"Registros raw del sheet: {len(registros_crudos)}")
        print(f"Articulos después de mapeo: {len(articulos_handler)}")
        print(f"Diferencia: {len(registros_crudos) - len(articulos_handler)}")
        
        if len(articulos_handler) < len(registros_crudos):
            print("⚠️  Se están perdiendo registros en el mapeo")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()
