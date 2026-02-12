#!/usr/bin/env python3
"""
DIAGNÓSTICO URGENTE: ¿Por qué se eliminan todos los artículos al sincronizar?
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "back"))

from back.database import get_db
from back.modelos import Usuario
from back.utils.tablas_handler import TablasHandler
from sqlmodel import select

def main():
    print("\n" + "="*80)
    print("🚨 DIAGNÓSTICO: ¿Por qué se eliminan artículos al sincronizar?")
    print("="*80 + "\n")
    
    # Buscar usuario admin_ropa
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
        
        # Cargar artículos desde Google Sheets
        print(f"\n🔍 CARGANDO ARTÍCULOS DESDE GOOGLE SHEETS...")
        handler = TablasHandler(id_empresa=id_empresa, db=db)
        articulos_del_sheet = handler.cargar_articulos()
        
        print(f"\n📊 RESULTADOS:")
        print(f"   Total de filas cargadas: {len(articulos_del_sheet)}")
        
        if not articulos_del_sheet:
            print(f"\n❌ ¡PROBLEMA CRÍTICO!")
            print(f"   No se cargaron artículos desde Google Sheets")
            print(f"   Por eso se eliminan TODOS los artículos de la DB")
            return
        
        # Verificar códigos
        print(f"\n🔍 ANALIZANDO CÓDIGOS:")
        
        codigos_encontrados = []
        filas_sin_codigo = 0
        
        for i, fila in enumerate(articulos_del_sheet):
            codigo = fila.get('codigo_interno')
            if codigo:
                codigos_encontrados.append(str(codigo).strip())
            else:
                filas_sin_codigo += 1
                if filas_sin_codigo <= 3:
                    print(f"   ⚠️  Fila {i+1} sin código: {list(fila.keys())[:5]}")
        
        print(f"\n📊 ESTADÍSTICAS:")
        print(f"   - Filas con código válido: {len(codigos_encontrados)}")
        print(f"   - Filas SIN código: {filas_sin_codigo}")
        
        if codigos_encontrados:
            print(f"\n✅ CÓDIGOS ENCONTRADOS (primeros 10):")
            for codigo in codigos_encontrados[:10]:
                print(f"      - '{codigo}'")
        else:
            print(f"\n❌ ¡PROBLEMA CRÍTICO!")
            print(f"   NO SE ENCONTRARON CÓDIGOS EN LAS FILAS")
            print(f"   Esto hace que el set 'codigos_en_sheet' esté VACÍO")
            print(f"   Por eso se eliminan TODOS los artículos")
        
        # Mostrar estructura de una fila
        if articulos_del_sheet:
            print(f"\n🔍 ESTRUCTURA DE LA PRIMERA FILA:")
            primera_fila = articulos_del_sheet[0]
            for key, value in list(primera_fila.items())[:10]:
                if key != '_fila_original':
                    print(f"      {key}: {value}")
        
        print(f"\n{'='*80}")
        print(f"💡 DIAGNÓSTICO:")
        print(f"{'='*80}")
        
        if not articulos_del_sheet:
            print("\n❌ CAUSA DEL PROBLEMA:")
            print("   handler.cargar_articulos() devuelve una lista VACÍA")
            print("\n   MOTIVOS POSIBLES:")
            print("   1. La hoja 'stock' no existe en Google Sheets")
            print("   2. La hoja está vacía")
            print("   3. Error al leer la hoja")
            print("   4. Error en el mapeo de columnas")
        elif not codigos_encontrados:
            print("\n❌ CAUSA DEL PROBLEMA:")
            print("   Las filas NO tienen el campo 'codigo_interno'")
            print("\n   MOTIVOS POSIBLES:")
            print("   1. El mapeo de columnas no está funcionando")
            print("   2. La columna de código NO se detecta correctamente")
            print("   3. El nombre de la columna no coincide con las variantes")
        else:
            print("\n✅ LOS CÓDIGOS SE CARGAN CORRECTAMENTE")
            print(f"   Se encontraron {len(codigos_encontrados)} códigos")
            print(f"   El problema debe ser otro")
        
        print()
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
