#!/usr/bin/env python3
"""
Script de Diagnóstico: Verifica artículos sin ID válido en la base de datos
Detalla problemas de integridad en la tabla de artículos
"""

import sys
from typing import Optional
from sqlmodel import Session, select, create_engine
from sqlalchemy import text
from datetime import datetime

# Agregar directorio del proyecto al path
sys.path.insert(0, '/home/sgi_user/proyectos/sistema_gestion_ima')

try:
    from back.modelos import Articulo, Empresa
    from back.database import SessionLocal, engine
    print("✅ Módulos importados exitosamente")
except ImportError as e:
    print(f"❌ Error al importar módulos: {e}")
    sys.exit(1)

def diagnosticar_articulos():
    """Diagnóstico completo de artículos sin ID y problemas de integridad"""
    
    print("\n" + "="*80)
    print("🔍 DIAGNÓSTICO DE ARTÍCULOS SIN ID VÁLIDO")
    print("="*80 + "\n")
    
    # Crear sesión
    db = SessionLocal()
    
    try:
        # === PRUEBA 1: Verificar artículos con ID NULL ===
        print("1️⃣  BUSCANDO ARTÍCULOS CON ID NULL:")
        print("-" * 80)
        
        try:
            # Query SQL directa para más control
            result = db.exec(text("""
                SELECT COUNT(*) as cantidad, 
                       COUNT(DISTINCT id) as ids_unicos,
                       COUNT(CASE WHEN id IS NULL THEN 1 END) as ids_null,
                       COUNT(CASE WHEN id <= 0 THEN 1 END) as ids_invalidos
                FROM articulos;
            """)).first()
            
            if result:
                total, ids_unicos, ids_null, ids_invalidos = result
                print(f"   Total de artículos: {total}")
                print(f"   IDs únicos: {ids_unicos}")
                print(f"   IDs NULL: {ids_null}")
                print(f"   IDs <= 0: {ids_invalidos}")
                
                if ids_null > 0 or ids_invalidos > 0:
                    print("   ⚠️  PROBLEMA DETECTADO: Hay artículos con ID inválido\n")
                else:
                    print("   ✅ Todos los artículos tienen ID válido\n")
        except Exception as e:
            print(f"   ❌ Error en query: {e}\n")
        
        # === PRUEBA 2: Listar algunos artículos problemáticos ===
        print("2️⃣  ARTÍCULOS SIN ID O CON ID INVÁLIDO:")
        print("-" * 80)
        
        try:
            problematicos = db.exec(text("""
                SELECT id, descripcion, codigo_interno, activo, id_empresa
                FROM articulos
                WHERE id IS NULL OR id <= 0
                LIMIT 20;
            """)).all()
            
            if problematicos:
                print(f"   Encontrados {len(problematicos)} artículos problemáticos:")
                for row in problematicos:
                    print(f"   - ID: {row[0]}, Descripción: {row[1]}, Código: {row[2]}, Empresa: {row[4]}")
                print()
            else:
                print("   ✅ No hay artículos con ID inválido\n")
        except Exception as e:
            print(f"   ❌ Error en query: {e}\n")
        
        # === PRUEBA 3: Artículos por empresa ===
        print("3️⃣  DISTRIBUCIÓN DE ARTÍCULOS POR EMPRESA:")
        print("-" * 80)
        
        try:
            empresas = db.exec(text("""
                SELECT e.id, e.nombre_comercial, COUNT(a.id) as cantidad
                FROM empresas e
                LEFT JOIN articulos a ON e.id = a.id_empresa
                GROUP BY e.id, e.nombre_comercial
                ORDER BY cantidad DESC;
            """)).all()
            
            for empresa in empresas:
                emp_id, nombre, cantidad = empresa
                print(f"   Empresa {emp_id} ({nombre}): {cantidad} artículos")
            print()
        except Exception as e:
            print(f"   ❌ Error en query: {e}\n")
        
        # === PRUEBA 4: Verificar inconsistencias en descripciones ===
        print("4️⃣  VERIFICANDO DUPLICADOS EN DESCRIPCIONES:")
        print("-" * 80)
        
        try:
            duplicados = db.exec(text("""
                SELECT descripcion, COUNT(*) as cantidad
                FROM articulos
                WHERE activo = true
                GROUP BY descripcion
                HAVING COUNT(*) > 1
                ORDER BY cantidad DESC
                LIMIT 10;
            """)).all()
            
            if duplicados:
                print(f"   Encontrados {len(duplicados)} productos con descripciones duplicadas:")
                for row in duplicados:
                    desc, cant = row
                    print(f"   - '{desc}': {cant} veces")
                print()
            else:
                print("   ✅ No hay duplicados en descripciones\n")
        except Exception as e:
            print(f"   ❌ Error en query: {e}\n")
        
        # === PRUEBA 5: Verificar productos específicos del video ===
        print("5️⃣  BUSCANDO PRODUCTOS ESPECÍFICOS DEL REPORTE:")
        print("-" * 80)
        
        productos_problema = [
            "Shorts de jeans (nuevo)",
            "Shorts Frunce negro",
            "shorts de jeans",
            "shorts frunce"
        ]
        
        for producto_nombre in productos_problema:
            try:
                articulos = db.exec(text(f"""
                    SELECT id, descripcion, codigo_interno, precio_venta, activo, id_empresa
                    FROM articulos
                    WHERE LOWER(descripcion) LIKE LOWER('%{producto_nombre}%')
                    LIMIT 5;
                """)).all()
                
                if articulos:
                    print(f"   '{producto_nombre}':")
                    for art in articulos:
                        art_id, desc, cod, precio, activo, emp = art
                        estado_id = "✅" if art_id and art_id > 0 else "❌"
                        print(f"      {estado_id} ID: {art_id}, Desc: {desc}, Código: {cod}, Precio: {precio}, Empresa: {emp}")
                else:
                    print(f"   ⚠️  '{producto_nombre}': NO ENCONTRADO\n")
            except Exception as e:
                print(f"   ❌ Error buscando '{producto_nombre}': {e}")
        
        print()
        
        # === PRUEBA 6: Verificar estructura de tabla ===
        print("6️⃣  ESTRUCTURA DE LA TABLA ARTICULOS:")
        print("-" * 80)
        
        try:
            columnas = db.exec(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'articulos'
                ORDER BY ordinal_position;
            """)).all()
            
            if columnas:
                for col in columnas[:5]:  # Mostrar primeras 5 columnas
                    col_name, data_type, nullable, default = col
                    print(f"   {col_name}: {data_type} (nullable: {nullable}, default: {default})")
                print(f"   ... (y {len(columnas) - 5} columnas más)")
            print()
        except Exception as e:
            print(f"   ❌ Error verificando estructura: {e}\n")
    
    finally:
        db.close()

def generar_reporte():
    """Genera un reporte de diagnóstico en archivo"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo_salida = f"/home/sgi_user/proyectos/sistema_gestion_ima/diagnostico_articulos_{timestamp}.txt"
    
    # Redirigir stdout a archivo
    import io
    old_stdout = sys.stdout
    
    with open(archivo_salida, 'w') as f:
        sys.stdout = f
        diagnosticar_articulos()
    
    sys.stdout = old_stdout
    return archivo_salida

if __name__ == "__main__":
    diagnosticar_articulos()
    
    print("\n" + "="*80)
    print("📋 RECOMENDACIONES:")
    print("="*80)
    print("""
1. Si hay artículos sin ID:
   - Ejecutar: python /home/sgi_user/proyectos/sistema_gestion_ima/fix_articulos_id.py
   
2. Si hay duplicados en descripciones:
   - Revisar en admin qué productos están duplicados
   - Consolidar y eliminar referencias antiguas
   
3. Si los productos específicos no tienen ID:
   - Verificar que fueron importados correctamente
   - Re-sincronizar desde la fuente original
   
4. En el frontend, mejorar validación:
   - Filtrar artículos con ID NULL o <= 0 ANTES de mostrar en selector
   - Validar que cada producto seleccionado tiene ID válido
""")
    print("="*80 + "\n")
