#!/usr/bin/env python3
"""
Script de diagnóstico rápido para verificar la estructura de columnas
en todas las hojas de Google Sheets configuradas.
"""
import sys
from pathlib import Path

# Agregar el directorio back al path
sys.path.insert(0, str(Path(__file__).parent / "back"))

from back.database import get_db
from back.modelos import ConfiguracionEmpresa
from back.utils.tablas_handler import TablasHandler
from sqlmodel import select
import gspread


def diagnosticar_empresa(id_empresa: int, nombre_empresa: str, db):
    """
    Realiza un diagnóstico completo de la configuración de Google Sheets para una empresa
    """
    print(f"\n{'='*70}")
    print(f"🏢 EMPRESA: {nombre_empresa} (ID: {id_empresa})")
    print(f"{'='*70}")
    
    try:
        # Obtener configuración
        config = db.get(ConfiguracionEmpresa, id_empresa)
        if not config or not config.link_google_sheets:
            print("❌ No tiene Google Sheets configurado")
            return False
        
        print(f"📋 Google Sheet ID: {config.link_google_sheets}")
        
        # Crear handler
        handler = TablasHandler(id_empresa=id_empresa, db=db)
        
        if not handler.client:
            print("❌ No se pudo conectar al cliente de Google Sheets")
            return False
        
        # Abrir el documento
        try:
            sheet = handler.client.open_by_key(config.link_google_sheets)
            print(f"✅ Documento encontrado: '{sheet.title}'")
        except gspread.exceptions.SpreadsheetNotFound:
            print("❌ No se encontró el documento (verifica el ID)")
            return False
        except Exception as e:
            print(f"❌ Error al abrir documento: {e}")
            return False
        
        # Listar todas las hojas
        worksheets = sheet.worksheets()
        print(f"\n📄 Hojas disponibles ({len(worksheets)}):")
        for ws in worksheets:
            print(f"   - {ws.title}")
        
        # Verificar hoja 'stock'
        print(f"\n{'─'*70}")
        print("🔍 ANÁLISIS DE HOJA 'stock':")
        print(f"{'─'*70}")
        
        try:
            worksheet_stock = sheet.worksheet("stock")
            print(f"✅ Hoja 'stock' encontrada")
            
            # Obtener encabezados
            encabezados = worksheet_stock.row_values(1)
            print(f"\n📋 Columnas detectadas ({len(encabezados)}):")
            for i, col in enumerate(encabezados, 1):
                print(f"   {i:2d}. '{col}'")
            
            # Verificar qué columnas se detectarían
            print(f"\n🔍 MAPEO AUTOMÁTICO DE COLUMNAS:")
            
            columnas_necesarias = [
                ('Código/ID', ['codigo_interno', 'codigo', 'código', 'code', 'Código']),
                ('Stock', ['stock_actual', 'stock', 'cantidad', 'existencia', 'cantidad_disponible']),
                ('Descripción', ['descripcion', 'descripción', 'nombre', 'producto', 'name']),
                ('Precio Venta', ['precio_venta', 'precio', 'precio_unitario', 'pvp', 'costo 1', 'costo_1']),
                ('Precio Costo', ['precio_costo', 'costo', 'precio_compra', 'costo_unitario']),
                ('Ubicación', ['ubicacion', 'ubicación', 'location', 'estante']),
            ]
            
            columnas_criticas_ok = True
            
            for nombre, variantes in columnas_necesarias:
                columna_detectada = handler._encontrar_columna(encabezados, variantes)
                es_critica = nombre in ['Código/ID', 'Stock']
                
                if columna_detectada:
                    print(f"   ✅ {nombre:20s} → '{columna_detectada}'")
                else:
                    simbolo = "❌" if es_critica else "⚠️ "
                    print(f"   {simbolo} {nombre:20s} → NO DETECTADA")
                    if es_critica:
                        columnas_criticas_ok = False
                        print(f"      💡 Busqué: {', '.join(variantes)}")
            
            # Revisar algunos datos de ejemplo
            print(f"\n📊 MUESTRA DE DATOS (primeras 3 filas):")
            datos = worksheet_stock.get_all_records()
            
            if not datos:
                print("   ⚠️  La hoja está vacía (solo tiene encabezados)")
            else:
                for i, fila in enumerate(datos[:3], 1):
                    print(f"\n   Fila {i}:")
                    for key, value in list(fila.items())[:5]:  # Solo primeras 5 columnas
                        print(f"      {key}: {value}")
            
            # Resultado final
            print(f"\n{'─'*70}")
            if columnas_criticas_ok:
                print("✅ RESULTADO: Configuración CORRECTA - Stock se puede sincronizar")
            else:
                print("❌ RESULTADO: Faltan columnas CRÍTICAS - Sincronización FALLARÁ")
                print("\n💡 SOLUCIÓN: Asegúrate de que la hoja 'stock' tenga:")
                print("   - Una columna para el código (ej: 'Código', 'codigo', 'codigo_interno')")
                print("   - Una columna para el stock (ej: 'cantidad', 'stock', 'stock_actual')")
            
            return columnas_criticas_ok
            
        except gspread.exceptions.WorksheetNotFound:
            print("❌ No se encontró la hoja 'stock'")
            print("\n💡 SOLUCIÓN: Crea una hoja llamada 'stock' en el documento")
            return False
        
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """
    Función principal
    """
    print(f"\n{'#'*70}")
    print(f"# DIAGNÓSTICO DE CONFIGURACIÓN DE GOOGLE SHEETS")
    print(f"# Sistema de Gestión IMA")
    print(f"{'#'*70}")
    
    db = next(get_db())
    
    try:
        # Buscar todas las empresas con Google Sheets configurado
        empresas = db.exec(
            select(ConfiguracionEmpresa)
            .where(ConfiguracionEmpresa.link_google_sheets.isnot(None))
            .where(ConfiguracionEmpresa.link_google_sheets != "")
        ).all()
        
        if not empresas:
            print("\n❌ No se encontraron empresas con Google Sheets configurado")
            print("\n💡 Configura el link_google_sheets en la tabla configuracion_empresas")
            return
        
        print(f"\n✅ Se encontraron {len(empresas)} empresa(s) con Google Sheets configurado\n")
        
        # Diagnosticar cada empresa
        resultados = {}
        for config in empresas:
            nombre_display = config.nombre_negocio or f"Empresa {config.id_empresa}"
            resultado = diagnosticar_empresa(
                config.id_empresa,
                nombre_display,
                db
            )
            resultados[config.id_empresa] = resultado
        
        # Resumen final
        print(f"\n\n{'#'*70}")
        print(f"# RESUMEN GENERAL")
        print(f"{'#'*70}\n")
        
        empresas_ok = sum(1 for r in resultados.values() if r)
        empresas_fail = len(resultados) - empresas_ok
        
        print(f"📊 Total de empresas analizadas: {len(resultados)}")
        print(f"   ✅ Configuradas correctamente: {empresas_ok}")
        print(f"   ❌ Con problemas: {empresas_fail}")
        
        if empresas_fail > 0:
            print(f"\n⚠️  Empresas que requieren atención:")
            for config in empresas:
                if not resultados[config.id_empresa]:
                    nombre = config.nombre_negocio or f"Empresa {config.id_empresa}"
                    print(f"   - {nombre} (ID: {config.id_empresa})")
        
        print()
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
