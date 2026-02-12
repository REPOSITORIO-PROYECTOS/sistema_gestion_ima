#!/usr/bin/env python3
"""
Script de prueba para verificar la sincronización de stock en Google Sheets
con diferentes configuraciones de columnas.
"""
import sys
from pathlib import Path

# Agregar el directorio back al path
sys.path.insert(0, str(Path(__file__).parent / "back"))

from back.database import get_db
from back.modelos import ConfiguracionEmpresa, Articulo, Usuario
from back.utils.tablas_handler import TablasHandler
from back.schemas.caja_schemas import ArticuloVendido
from sqlmodel import Session, select
from typing import List

def test_deteccion_columnas(id_empresa: int, db: Session):
    """
    Prueba la detección flexible de columnas en la hoja de stock
    """
    print(f"\n{'='*60}")
    print(f"🔍 PRUEBA 1: Detección de columnas para empresa ID {id_empresa}")
    print(f"{'='*60}")
    
    try:
        # Obtener configuración de la empresa
        config = db.get(ConfiguracionEmpresa, id_empresa)
        if not config or not config.link_google_sheets:
            print(f"❌ Empresa {id_empresa} no tiene Google Sheets configurado")
            return False
        
        print(f"📋 Google Sheet ID: {config.link_google_sheets[:20]}...")
        
        # Crear handler y cargar datos
        handler = TablasHandler(id_empresa=id_empresa, db=db)
        print("\n📦 Cargando artículos desde Google Sheets...")
        articulos = handler.cargar_articulos()
        
        if not articulos:
            print("❌ No se pudieron cargar artículos")
            return False
        
        print(f"✅ Se cargaron {len(articulos)} artículos")
        
        # Mostrar las primeras 3 filas como muestra
        print("\n📋 Muestra de datos detectados:")
        for i, art in enumerate(articulos[:3], 1):
            print(f"\nArtículo {i}:")
            print(f"  - Código: {art.get('codigo_interno', 'N/A')}")
            print(f"  - Descripción: {art.get('descripcion', 'N/A')}")
            print(f"  - Stock: {art.get('stock_actual', 'N/A')}")
            print(f"  - Precio Venta: {art.get('precio_venta', 'N/A')}")
            print(f"  - Ubicación: {art.get('ubicacion', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_actualizacion_stock(id_empresa: int, db: Session, codigo_producto: str, cantidad: float = 1.0):
    """
    Prueba la actualización de stock sin realizar una venta real
    (simulación en modo dry-run)
    """
    print(f"\n{'='*60}")
    print(f"🔄 PRUEBA 2: Simulación de actualización de stock")
    print(f"{'='*60}")
    
    try:
        # Buscar el artículo en la DB
        articulo = db.exec(
            select(Articulo)
            .where(Articulo.id_empresa == id_empresa)
            .where(Articulo.codigo_interno == codigo_producto)
        ).first()
        
        if not articulo:
            print(f"❌ No se encontró artículo con código '{codigo_producto}' en la DB")
            return False
        
        print(f"✅ Artículo encontrado en DB:")
        print(f"   - ID: {articulo.id}")
        print(f"   - Código: {articulo.codigo_interno}")
        print(f"   - Descripción: {articulo.descripcion}")
        print(f"   - Stock actual en DB: {articulo.stock_actual}")
        
        # Crear un item de venta simulado
        item_simulado = ArticuloVendido(
            id_articulo=articulo.id,
            cantidad=cantidad,
            precio_unitario=articulo.precio_venta,
            subtotal=cantidad * articulo.precio_venta
        )
        
        print(f"\n📝 Simulando descuento de {cantidad} unidades...")
        
        # Crear handler
        handler = TablasHandler(id_empresa=id_empresa, db=db)
        
        # NOTA: Esta es una prueba real, va a actualizar el stock
        print("⚠️  ADVERTENCIA: Esto actualizará el stock real en Google Sheets")
        print("⚠️  Presiona Ctrl+C en los próximos 3 segundos para cancelar...")
        
        import time
        time.sleep(3)
        
        print("\n🚀 Ejecutando actualización de stock...")
        resultado = handler.restar_stock(db, [item_simulado])
        
        if resultado:
            print("✅ Stock actualizado correctamente en Google Sheets")
            return True
        else:
            print("❌ Falló la actualización del stock")
            return False
            
    except KeyboardInterrupt:
        print("\n🛑 Operación cancelada por el usuario")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_verificar_columnas_stock(id_empresa: int, db: Session):
    """
    Verifica qué columnas están disponibles en la hoja de stock
    """
    print(f"\n{'='*60}")
    print(f"🔍 PRUEBA 3: Verificación de columnas en hoja 'stock'")
    print(f"{'='*60}")
    
    try:
        handler = TablasHandler(id_empresa=id_empresa, db=db)
        
        # Acceder directamente a la hoja
        sheet = handler.client.open_by_key(handler.google_sheet_id)
        worksheet = sheet.worksheet("stock")
        
        # Obtener encabezados
        encabezados = worksheet.row_values(1)
        
        print(f"\n📋 Columnas encontradas ({len(encabezados)}):")
        for i, col in enumerate(encabezados, 1):
            print(f"   {i}. {col}")
        
        # Verificar qué columnas se detectarían
        print(f"\n🔍 Detección de columnas relevantes:")
        
        # Código
        col_codigo = handler._encontrar_columna(
            encabezados,
            ['codigo_interno', 'codigo', 'código', 'code', 'Código']
        )
        print(f"   - Columna de CÓDIGO: {col_codigo or '❌ NO DETECTADA'}")
        
        # Stock
        col_stock = handler._encontrar_columna(
            encabezados,
            ['stock_actual', 'stock', 'cantidad', 'existencia', 'cantidad_disponible']
        )
        print(f"   - Columna de STOCK: {col_stock or '❌ NO DETECTADA'}")
        
        # Precio
        col_precio = handler._encontrar_columna(
            encabezados,
            ['precio_venta', 'precio', 'precio_unitario', 'pvp']
        )
        print(f"   - Columna de PRECIO: {col_precio or '⚠️  NO DETECTADA (opcional)'}")
        
        # Descripción
        col_desc = handler._encontrar_columna(
            encabezados,
            ['descripcion', 'descripción', 'nombre', 'producto']
        )
        print(f"   - Columna de DESCRIPCIÓN: {col_desc or '⚠️  NO DETECTADA (opcional)'}")
        
        if col_codigo and col_stock:
            print(f"\n✅ Las columnas necesarias para actualizar stock fueron detectadas")
            return True
        else:
            print(f"\n❌ Faltan columnas críticas para actualizar stock")
            return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def listar_empresas(db: Session):
    """
    Lista todas las empresas con Google Sheets configurado
    """
    print(f"\n{'='*60}")
    print(f"📊 EMPRESAS CON GOOGLE SHEETS CONFIGURADO")
    print(f"{'='*60}")
    
    empresas = db.exec(
        select(ConfiguracionEmpresa)
        .where(ConfiguracionEmpresa.link_google_sheets.isnot(None))
        .where(ConfiguracionEmpresa.link_google_sheets != "")
    ).all()
    
    if not empresas:
        print("❌ No hay empresas con Google Sheets configurado")
        return []
    
    print(f"\n✅ Se encontraron {len(empresas)} empresa(s):\n")
    for config in empresas:
        print(f"   ID: {config.id_empresa}")
        print(f"   Nombre: {config.razon_social}")
        print(f"   Sheet ID: {config.link_google_sheets[:30]}...")
        print(f"   {'─'*50}")
    
    return [c.id_empresa for c in empresas]


def main():
    """
    Función principal del script de pruebas
    """
    print(f"\n{'#'*60}")
    print(f"# SCRIPT DE PRUEBA - SINCRONIZACIÓN DE STOCK")
    print(f"# Sistema de Gestión IMA")
    print(f"{'#'*60}")
    
    # Obtener sesión de base de datos
    db = next(get_db())
    
    try:
        # 1. Listar empresas disponibles
        empresas_ids = listar_empresas(db)
        
        if not empresas_ids:
            print("\n❌ No hay empresas para probar")
            return
        
        # Preguntar qué empresa probar
        print(f"\n{'='*60}")
        print("Selecciona una empresa para probar:")
        for i, emp_id in enumerate(empresas_ids, 1):
            print(f"   {i}. Empresa ID {emp_id}")
        print(f"   0. Probar todas")
        
        try:
            seleccion = int(input("\nIngresa tu selección: "))
        except ValueError:
            print("❌ Selección inválida")
            return
        
        if seleccion == 0:
            empresas_a_probar = empresas_ids
        elif 1 <= seleccion <= len(empresas_ids):
            empresas_a_probar = [empresas_ids[seleccion - 1]]
        else:
            print("❌ Selección fuera de rango")
            return
        
        # Ejecutar pruebas para cada empresa
        resultados = {}
        
        for id_empresa in empresas_a_probar:
            print(f"\n\n{'#'*60}")
            print(f"# PROBANDO EMPRESA ID: {id_empresa}")
            print(f"{'#'*60}")
            
            resultados[id_empresa] = {
                'deteccion_columnas': False,
                'verificacion_stock': False,
                'actualizacion': None  # None = no probado
            }
            
            # Prueba 1: Detección de columnas
            resultados[id_empresa]['deteccion_columnas'] = test_deteccion_columnas(id_empresa, db)
            
            # Prueba 3: Verificar columnas de stock
            resultados[id_empresa]['verificacion_stock'] = test_verificar_columnas_stock(id_empresa, db)
            
            # Prueba 2: Actualización de stock (opcional, preguntamos)
            if resultados[id_empresa]['verificacion_stock']:
                print(f"\n{'='*60}")
                respuesta = input("¿Deseas probar la actualización de stock? (esto modifica datos reales) [s/N]: ")
                if respuesta.lower() == 's':
                    codigo = input("Ingresa el código del producto a probar: ")
                    cantidad = float(input("Cantidad a descontar (default 1.0): ") or "1.0")
                    resultados[id_empresa]['actualizacion'] = test_actualizacion_stock(
                        id_empresa, db, codigo, cantidad
                    )
        
        # Resumen final
        print(f"\n\n{'#'*60}")
        print(f"# RESUMEN DE PRUEBAS")
        print(f"{'#'*60}\n")
        
        for id_empresa, tests in resultados.items():
            print(f"Empresa ID {id_empresa}:")
            print(f"   ✓ Detección de columnas: {'✅ PASS' if tests['deteccion_columnas'] else '❌ FAIL'}")
            print(f"   ✓ Verificación stock: {'✅ PASS' if tests['verificacion_stock'] else '❌ FAIL'}")
            if tests['actualizacion'] is not None:
                print(f"   ✓ Actualización stock: {'✅ PASS' if tests['actualizacion'] else '❌ FAIL'}")
            print()
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
