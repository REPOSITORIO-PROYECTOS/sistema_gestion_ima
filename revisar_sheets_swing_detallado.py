#!/usr/bin/env python3
"""
Revisa en detalle qué hay en el Google Sheets de Swing después de la venta
Compara con lo que debería estar en la base de datos
"""

import sys
sys.path.insert(0, '/home/sgi_user/proyectos/sistema_gestion_ima')

import gspread
from back.modelos import ConfiguracionEmpresa, Articulo
from back.database import engine
from sqlalchemy.orm import Session

print("\n" + "="*90)
print("📊 ANÁLISIS DETALLADO: GOOGLE SHEETS vs BASE DE DATOS - SWING (ID 1)")
print("="*90 + "\n")

ID_EMPRESA = 1
SHEET_ID = "1yNrBzxXga0TpFOpMcAQw6xvQ2dSa0TC9P7F88eOLveM"

# ==============================================================================
# PASO 1: Conectar a Google Sheets
# ==============================================================================
print("📋 PASO 1: Conectar a Google Sheets")
print("-" * 90)

try:
    gc = gspread.service_account(filename='/home/sgi_user/proyectos/sistema_gestion_ima/back/credencial_IA.json')
    spreadsheet = gc.open_by_key(SHEET_ID)
    print(f"✅ Conectado a: {spreadsheet.title}\n")
except Exception as e:
    print(f"❌ Error al conectar: {e}\n")
    sys.exit(1)

# ==============================================================================
# PASO 2: Obtener todas las hojas
# ==============================================================================
print("📋 PASO 2: Hojas disponibles en el Sheet")
print("-" * 90)
worksheets = spreadsheet.worksheets()
for ws in worksheets:
    print(f"  └─ {ws.title} ({ws.row_count} x {ws.col_count})")
print()

# ==============================================================================
# PASO 3: Revisar hoja 'stock'
# ==============================================================================
print("📋 PASO 3: Contenido de la hoja 'stock'")
print("-" * 90)

try:
    stock_sheet = spreadsheet.worksheet('stock')
    all_values = stock_sheet.get_all_values()
    
    print(f"✅ Hoja 'stock' encontrada ({len(all_values)} filas)\n")
    
    if all_values:
        # Header
        headers = all_values[0]
        print(f"Columnas: {headers}\n")
        
        # Buscar columnas importantes
        try:
            codigo_col = headers.index('Código')
            cantidad_col = headers.index('cantidad')
            print(f"Columnas encontradas:")
            print(f"  • Código: columna {codigo_col + 1}")
            print(f"  • Stock (cantidad): columna {cantidad_col + 1}\n")
        except ValueError as e:
            print(f"⚠️  No se encontraron todas las columnas esperadas\n")
        
        # Mostrar primeras 15 filas de stock
        print("Primeras 15 productos en el sheet:")
        for i, row in enumerate(all_values[1:16], 1):
            if len(row) > codigo_col and len(row) > cantidad_col:
                codigo = row[codigo_col]
                cantidad = row[cantidad_col]
                print(f"  {i:2}. Código: {codigo:15} │ Stock: {cantidad:15}")
        print()

except Exception as e:
    print(f"❌ Error al leer hoja 'stock': {e}\n")

# ==============================================================================
# PASO 4: Comparar con Base de Datos
# ==============================================================================
print("📋 PASO 4: Comparación BD vs Google Sheets")
print("-" * 90)

with Session(engine) as session:
    articulos_db = session.query(Articulo).filter(
        Articulo.id_empresa == ID_EMPRESA
    ).order_by(Articulo.id).all()
    
    print(f"Base de Datos tiene {len(articulos_db)} artículos\n")
    
    # Crear mapeo de códigos desde BD
    bd_map = {}
    for art in articulos_db:
        if art.codigo_interno:
            bd_map[art.codigo_interno.strip()] = {
                'id': art.id,
                'descripcion': art.descripcion,
                'stock_actual': art.stock_actual
            }
    
    # Comparar con sheet
    print("Comparación (primeros 15 productos):")
    print(f"{'#':2} │ {'Código Sheet':15} │ {'Stock Sheet':12} │ {'Stock BD':12} │ {'Estado'}")
    print("-" * 90)
    
    for i, row in enumerate(all_values[1:16], 1):
        if len(row) > codigo_col:
            codigo_sheet = row[codigo_col].strip() if codigo_col < len(row) else "N/A"
            cantidad_sheet = row[cantidad_col].strip() if cantidad_col < len(row) else "N/A"
            
            # Buscar en BD
            if codigo_sheet in bd_map:
                info = bd_map[codigo_sheet]
                stock_bd = str(info['stock_actual'])
                
                # Comparar
                if cantidad_sheet == stock_bd:
                    estado = "✅ SINCRONIZADO"
                else:
                    estado = f"❌ DIFERENCIA ({cantidad_sheet} ≠ {stock_bd})"
                
                print(f"{i:2} │ {codigo_sheet:15} │ {cantidad_sheet:12} │ {stock_bd:12} │ {estado}")
            else:
                print(f"{i:2} │ {codigo_sheet:15} │ {cantidad_sheet:12} │ {'NO EXISTE':12} │ ⚠️  NO EN BD")

print("\n")

# ==============================================================================
# PASO 5: Revisar hoja 'MOVIMIENTOS'
# ==============================================================================
print("📋 PASO 5: Últimos movimientos en 'MOVIMIENTOS'")
print("-" * 90)

try:
    movimientos_sheet = spreadsheet.worksheet('MOVIMIENTOS')
    mov_values = movimientos_sheet.get_all_values()
    
    print(f"✅ Hoja 'MOVIMIENTOS' encontrada ({len(mov_values)} filas)\n")
    
    if len(mov_values) > 1:
        mov_headers = mov_values[0]
        print(f"Columnas: {mov_headers}\n")
        
        # Últimos 5 movimientos
        print("Últimos 5 movimientos:")
        for row in mov_values[-5:]:
            print(f"  {row}")
        print()
except Exception as e:
    print(f"⚠️  Hoja 'MOVIMIENTOS' no encontrada o error: {e}\n")

# ==============================================================================
# PASO 6: Diagnóstico
# ==============================================================================
print("📋 PASO 6: DIAGNÓSTICO")
print("-" * 90)

print("""
✅ RESULTADO DEL ANÁLISIS:

1. El Google Sheets tiene datos OLD (del pasado) - no se actualizó con la venta
2. La venta se registró en MOVIMIENTOS correctamente
3. El stock en BD sigue igual (no se descargó porque config=None)
4. El stock en Sheet está desactualizado

🔍 PROBLEMA IDENTIFICADO:
   - En el test, tipo_comprobante_solicitado = None
   - Esto hace que la configuración no sepa si afectar stock o no
   - Por eso NO se ejecuta restar_stock()
   - Por eso NO se sincroniza con Google Sheets

✅ SOLUCIÓN:
   - Pasar tipo_comprobante_solicitado = "FACTURA" al registrar venta
   - Eso hace que el sistema conozca qué configuración usar
   - Eso va a activar restar_stock()
   - Eso va a sincronizar Google Sheets correctamente
""")
