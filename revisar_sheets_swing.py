#!/usr/bin/env python3
"""
Revisa el Google Sheets de Swing (ID 1) y compara con la BD
Identifica problemas de sincronización
"""

import sys
sys.path.insert(0, '/home/sgi_user/proyectos/sistema_gestion_ima')

from sqlalchemy.orm import Session
from back.database import engine
from back.modelos import (
    Empresa, Articulo, ConfiguracionEmpresa
)
from back.utils.tablas_handler import TablasHandler

ID_EMPRESA = 1

print("\n" + "="*88)
print("🔍 REVISIÓN DE GOOGLE SHEETS: SWING (ID 1)")
print("="*88 + "\n")

try:
    with Session(engine) as session:
        # ================================================================
        # PASO 1: Obtener configuración de Swing
        # ================================================================
        print("📋 PASO 1: Obtener configuración de Swing")
        print("-" * 88)
        
        empresa = session.query(Empresa).filter(Empresa.id == ID_EMPRESA).first()
        print(f"✅ Empresa: {empresa.nombre_legal}\n")
        
        config = session.query(ConfiguracionEmpresa).filter(
            ConfiguracionEmpresa.id_empresa == ID_EMPRESA
        ).first()
        
        if not config:
            print("❌ No hay configuración para Swing")
            sys.exit(1)
        
        sheet_id = config.link_google_sheets
        print(f"✅ Google Sheets ID: {sheet_id}\n")
        
        # ================================================================
        # PASO 2: Conectar a Google Sheets
        # ================================================================
        print("📋 PASO 2: Conectar a Google Sheets")
        print("-" * 88)
        
        handler = TablasHandler(id_empresa=ID_EMPRESA, db=session)
        
        # Obtener el worksheet de stock
        try:
            sheet = handler.client.open_by_key(handler.google_sheet_id)
            ws_stock = sheet.worksheet("stock")
            print(f"✅ Conectado a hoja 'stock'\n")
        except Exception as e:
            print(f"❌ Error al conectar: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        # ================================================================
        # PASO 3: Leer columnas disponibles
        # ================================================================
        print("📋 PASO 3: Leer estructura del Sheet")
        print("-" * 88)
        
        # Obtener encabezados (fila 1)
        headers = ws_stock.row_values(1)
        print(f"Columnas encontradas ({len(headers)}):")
        for i, header in enumerate(headers, 1):
            print(f"  {i:2}. {header}")
        print()
        
        # ================================================================
        # PASO 4: Identificar columnas de ID y Stock
        # ================================================================
        print("📋 PASO 4: Identificar columnas de ID y Stock")
        print("-" * 88)
        
        id_col = None
        stock_col = None
        
        for i, header in enumerate(headers, 1):
            if header and header.lower() in ['id', 'código', 'codigo']:
                id_col = i
                print(f"✅ Columna ID: #{id_col} ({header})")
            elif header and 'stock' in header.lower() or 'cantidad' in header.lower():
                stock_col = i
                print(f"✅ Columna Stock: #{stock_col} ({header})")
        
        if not id_col or not stock_col:
            print(f"\n⚠️  PROBLEMA DETECTADO:")
            print(f"   ID Column: {id_col}")
            print(f"   Stock Column: {stock_col}")
            print(f"   → Falta configurar las columnas correctamente\n")
        else:
            print()
        
        # ================================================================
        # PASO 5: Leer datos del Sheet
        # ================================================================
        print("📋 PASO 5: Leer datos del Sheet (primeras 15 filas)")
        print("-" * 88 + "\n")
        
        all_values = ws_stock.get_all_values()
        
        print("Datos del Google Sheets:")
        for row_idx in range(1, min(16, len(all_values))):  # Filas 1-15
            row = all_values[row_idx]
            
            if len(row) > max(id_col or 0, stock_col or 0):
                id_val = row[id_col - 1] if id_col else "?"
                stock_val = row[stock_col - 1] if stock_col else "?"
                print(f"  Fila {row_idx+1:2}: ID={id_val:20} │ Stock={stock_val:15}")
            else:
                print(f"  Fila {row_idx+1:2}: [datos incompletos]")
        
        print()
        
        # ================================================================
        # PASO 6: Comparar con BD
        # ================================================================
        print("📋 PASO 6: Comparar datos de Sheet vs Base de Datos")
        print("-" * 88 + "\n")
        
        articulos_bd = session.query(Articulo).filter(
            Articulo.id_empresa == ID_EMPRESA
        ).order_by(Articulo.id).all()
        
        print(f"Total artículos en BD: {len(articulos_bd)}\n")
        print("Comparación (Primeros 10):")
        
        discrepancias = 0
        for idx, art in enumerate(articulos_bd[:10], 1):
            try:
                # Buscar en sheet
                codigo_en_sheet = None
                stock_en_sheet = None
                
                for row_idx in range(1, len(all_values)):
                    row = all_values[row_idx]
                    if len(row) > (id_col or 1) - 1:
                        if row[id_col - 1] == art.codigo_interno:
                            codigo_en_sheet = row[id_col - 1]
                            if stock_col and len(row) > stock_col - 1:
                                try:
                                    stock_en_sheet = float(row[stock_col - 1])
                                except:
                                    stock_en_sheet = row[stock_col - 1]
                            break
                
                if codigo_en_sheet:
                    match = "✅" if stock_en_sheet == art.stock_actual else "❌"
                    print(f"  {match} {art.codigo_interno:15} │ BD={art.stock_actual:12.0f} │ Sheet={str(stock_en_sheet):12}")
                    if stock_en_sheet != art.stock_actual:
                        discrepancias += 1
                else:
                    print(f"  ❌ {art.codigo_interno:15} │ NO ENCONTRADO EN SHEET")
                    discrepancias += 1
                    
            except Exception as e:
                print(f"  ⚠️  {art.codigo_interno:15} │ Error: {str(e)}")
        
        print(f"\n📊 Discrepancias encontradas: {discrepancias}")
        
        # ================================================================
        # PASO 7: Verificar configuración de sincronización
        # ================================================================
        print("\n📋 PASO 8: Verificar configuración de sincronización")
        print("-" * 88)
        
        print("\nConfiguraciones guardadas en BD:")
        print(f"  • link_google_sheets: {config.link_google_sheets}")
        print(f"  • nombre_negocio: {config.nombre_negocio}")
        print(f"  • color_principal: {config.color_principal}")
        
        # ================================================================
        # PASO 8: Diagnóstico
        # ================================================================
        print("\n📋 PASO 9: DIAGNÓSTICO")
        print("-" * 88)
        
        if discrepancias > 0:
            print("\n⚠️  PROBLEMA IDENTIFICADO:")
            print(f"   • Hay {discrepancias} discrepancias entre Sheet y BD")
            print("   • Posibles causas:")
            print("     1. Stock en Sheet no se sincronizó correctamente")
            print("     2. Columnas mal configuradas en Sheet")
            print("     3. IDs de productos no coinciden")
        else:
            print("\n✅ Sheet sincronizado correctamente con BD")
        
        print()

except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
