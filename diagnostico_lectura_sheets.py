#!/usr/bin/env python3
"""
DIAGNÓSTICO: ¿Por qué el artículo nuevo de Sheets NO se sincroniza a la DB?
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "back"))

from back.database import get_db
from back.modelos import Usuario, Articulo
from back.utils.tablas_handler import TablasHandler
from sqlmodel import select

def main():
    print("\n" + "="*80)
    print("🔍 DIAGNÓSTICO: ¿Por qué el artículo nuevo NO se lee de Sheets?")
    print("="*80 + "\n")
    
    db = next(get_db())
    
    try:
        usuario = db.exec(
            select(Usuario).where(Usuario.nombre_usuario == "admin_ropa")
        ).first()
        
        if not usuario:
            print("❌ ERROR: No se encontró el usuario 'admin_ropa'")
            return
        
        id_empresa = usuario.id_empresa
        print(f"✅ Usuario: admin_ropa (Empresa ID: {id_empresa})")
        
        # Cargar artículos CRUDOS desde Google Sheets
        print(f"\n🔍 PASO 1: Leyendo TODOS los datos crudos de Google Sheets...")
        handler = TablasHandler(id_empresa=id_empresa, db=db)
        
        # Acceder directamente a la hoja
        sheet = handler.client.open_by_key(handler.google_sheet_id)
        worksheet = sheet.worksheet("stock")
        
        # Leer TODOS los registros crudos
        datos_crudos = worksheet.get_all_records()
        
        print(f"✅ Total de filas en Google Sheets: {len(datos_crudos)}")
        
        # Mostrar últimas 5 filas (probablemente ahí está el nuevo)
        print(f"\n📋 ÚLTIMAS 5 FILAS EN GOOGLE SHEETS:")
        for i, fila in enumerate(datos_crudos[-5:], len(datos_crudos)-4):
            codigo = fila.get('Código') or fila.get('codigo') or fila.get('codigo_interno')
            nombre = fila.get('nombre') or fila.get('Descripción') or fila.get('descripcion')
            cantidad = fila.get('cantidad') or fila.get('stock') or fila.get('stock_actual')
            print(f"\n   Fila {i}:")
            print(f"      Código: {codigo}")
            print(f"      Nombre: {nombre}")
            print(f"      Cantidad: {cantidad}")
        
        # Cargar usando el método normal (mapeado)
        print(f"\n🔍 PASO 2: Cargando usando cargar_articulos() (con mapeo)...")
        articulos_mapeados = handler.cargar_articulos()
        
        print(f"✅ Total de artículos mapeados: {len(articulos_mapeados)}")
        
        # Comparar
        diferencia = len(datos_crudos) - len(articulos_mapeados)
        
        if diferencia > 0:
            print(f"\n⚠️  PROBLEMA ENCONTRADO:")
            print(f"   Google Sheets tiene: {len(datos_crudos)} filas")
            print(f"   Sistema mapea: {len(articulos_mapeados)} filas")
            print(f"   DIFERENCIA: {diferencia} filas NO se mapean")
            
            # Identificar cuáles no se mapean
            print(f"\n🔍 BUSCANDO FILAS QUE NO SE MAPEAN...")
            
            codigos_mapeados = set()
            for art in articulos_mapeados:
                if art.get('codigo_interno'):
                    codigos_mapeados.add(str(art['codigo_interno']).strip())
            
            filas_no_mapeadas = []
            for i, fila_cruda in enumerate(datos_crudos, 1):
                codigo_crudo = fila_cruda.get('Código') or fila_cruda.get('codigo') or fila_cruda.get('codigo_interno')
                if codigo_crudo:
                    codigo_normalizado = str(codigo_crudo).strip()
                    if codigo_normalizado not in codigos_mapeados:
                        filas_no_mapeadas.append((i, fila_cruda))
            
            if filas_no_mapeadas:
                print(f"\n❌ FILAS QUE NO SE MAPEARON ({len(filas_no_mapeadas)}):")
                for num_fila, fila in filas_no_mapeadas[:10]:
                    codigo = fila.get('Código') or fila.get('codigo')
                    nombre = fila.get('nombre') or fila.get('Descripción')
                    activo = fila.get('Activo')
                    print(f"\n   Fila {num_fila}:")
                    print(f"      Código: {codigo}")
                    print(f"      Nombre: {nombre}")
                    print(f"      Activo: {activo}")
                    print(f"      Todas las columnas: {list(fila.keys())[:10]}")
                    
                    # Verificar si tiene campos vacíos críticos
                    if not codigo:
                        print(f"      ❌ PROBLEMA: Código vacío o None")
                    if not nombre:
                        print(f"      ❌ PROBLEMA: Nombre vacío o None")
        
        # Verificar artículos en DB
        print(f"\n🔍 PASO 3: Verificando artículos en la Base de Datos...")
        articulos_db = db.exec(
            select(Articulo).where(Articulo.id_empresa == id_empresa)
        ).all()
        
        print(f"✅ Total de artículos en DB: {len(articulos_db)}")
        
        # Comparar códigos
        codigos_db = {art.codigo_interno for art in articulos_db}
        codigos_sheet = {art.get('codigo_interno') for art in articulos_mapeados if art.get('codigo_interno')}
        
        solo_en_sheet = codigos_sheet - codigos_db
        
        if solo_en_sheet:
            print(f"\n✅ Artículos en Sheet que NO están en DB ({len(solo_en_sheet)}):")
            for codigo in list(solo_en_sheet)[:5]:
                art = next((a for a in articulos_mapeados if a.get('codigo_interno') == codigo), None)
                if art:
                    print(f"   - {codigo}: {art.get('descripcion', 'Sin descripción')[:50]}")
            
            print(f"\n💡 Estos DEBERÍAN crearse al sincronizar")
        else:
            print(f"\n⚠️  No hay artículos nuevos en Sheet que no estén en DB")
        
        print(f"\n{'='*80}")
        print(f"💡 DIAGNÓSTICO FINAL:")
        print(f"{'='*80}")
        
        if diferencia > 0:
            print(f"\n❌ PROBLEMA IDENTIFICADO:")
            print(f"   {diferencia} filas de Google Sheets NO se están mapeando")
            print(f"\n   POSIBLES CAUSAS:")
            print(f"   1. Filas con campos críticos vacíos (código o nombre)")
            print(f"   2. Filas con valor 'Activo' = False o vacío")
            print(f"   3. Error en el mapeo de columnas")
            print(f"   4. Filas filtradas por alguna validación")
        elif not solo_en_sheet:
            print(f"\n⚠️  TODOS los artículos de Sheet YA están en la DB")
            print(f"   El artículo nuevo que buscas puede estar:")
            print(f"   1. En ambos (Sheet y DB) pero necesitas verificar el código")
            print(f"   2. No haberse guardado correctamente en Sheet")
            print(f"   3. Tener un código que ya existe")
        else:
            print(f"\n✅ EL SISTEMA ESTÁ FUNCIONANDO CORRECTAMENTE")
            print(f"   Hay {len(solo_en_sheet)} artículos nuevos listos para sincronizar")
        
        print()
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
