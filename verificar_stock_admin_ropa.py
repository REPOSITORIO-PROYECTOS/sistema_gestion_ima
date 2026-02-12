#!/usr/bin/env python3
"""
VERIFICACIÓN URGENTE de sincronización de stock para admin_ropa
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "back"))

from back.database import get_db
from back.modelos import Usuario, Articulo, ConfiguracionEmpresa
from back.utils.tablas_handler import TablasHandler
from sqlmodel import select

def main():
    print("\n" + "="*80)
    print("🚨 VERIFICACIÓN URGENTE DE STOCK - admin_ropa")
    print("="*80 + "\n")
    
    db = next(get_db())
    
    try:
        # 1. Buscar usuario admin_ropa
        print("🔍 Buscando usuario 'admin_ropa'...")
        usuario = db.exec(
            select(Usuario).where(Usuario.nombre_usuario == "admin_ropa")
        ).first()
        
        if not usuario:
            print("❌ ERROR: No se encontró el usuario 'admin_ropa'")
            return
        
        print(f"✅ Usuario encontrado:")
        print(f"   - ID: {usuario.id}")
        print(f"   - Nombre: {usuario.nombre_usuario}")
        print(f"   - ID Empresa: {usuario.id_empresa}")
        
        # 2. Obtener configuración de la empresa
        config = db.get(ConfiguracionEmpresa, usuario.id_empresa)
        if not config or not config.link_google_sheets:
            print(f"❌ ERROR: La empresa no tiene Google Sheets configurado")
            return
        
        print(f"\n📋 Configuración de empresa:")
        print(f"   - Nombre: {config.nombre_negocio or f'Empresa {usuario.id_empresa}'}")
        print(f"   - Sheet ID: {config.link_google_sheets[:40]}...")
        
        # 3. Obtener artículos de la DB
        print(f"\n📦 Obteniendo artículos de la BASE DE DATOS...")
        articulos_db = db.exec(
            select(Articulo)
            .where(Articulo.id_empresa == usuario.id_empresa)
        ).all()
        
        print(f"✅ Se encontraron {len(articulos_db)} artículos en la DB")
        
        # 4. Obtener artículos de Google Sheets
        print(f"\n☁️  Obteniendo artículos de GOOGLE SHEETS...")
        handler = TablasHandler(id_empresa=usuario.id_empresa, db=db)
        
        try:
            articulos_sheet = handler.cargar_articulos()
            print(f"✅ Se encontraron {len(articulos_sheet)} artículos en Sheets")
        except Exception as e:
            print(f"❌ ERROR al cargar desde Sheets: {e}")
            return
        
        # 5. Crear diccionarios para comparar
        print(f"\n🔄 Comparando datos...")
        
        db_dict = {art.codigo_interno: art for art in articulos_db}
        sheet_dict = {art.get('codigo_interno'): art for art in articulos_sheet if art.get('codigo_interno')}
        
        # 6. Análisis de sincronización
        solo_en_db = set(db_dict.keys()) - set(sheet_dict.keys())
        solo_en_sheet = set(sheet_dict.keys()) - set(db_dict.keys())
        en_ambos = set(db_dict.keys()) & set(sheet_dict.keys())
        
        print(f"\n📊 RESULTADOS DE COMPARACIÓN:")
        print(f"   - Artículos SOLO en BD: {len(solo_en_db)}")
        print(f"   - Artículos SOLO en Sheets: {len(solo_en_sheet)}")
        print(f"   - Artículos en AMBOS: {len(en_ambos)}")
        
        # 7. Verificar diferencias de stock
        print(f"\n🔍 VERIFICANDO DIFERENCIAS DE STOCK:")
        diferencias = []
        
        for codigo in en_ambos:
            art_db = db_dict[codigo]
            art_sheet = sheet_dict[codigo]
            
            stock_db = art_db.stock_actual
            stock_sheet = art_sheet.get('stock_actual', 0)
            
            if stock_db != stock_sheet:
                diferencias.append({
                    'codigo': codigo,
                    'descripcion': art_db.descripcion,
                    'stock_db': stock_db,
                    'stock_sheet': stock_sheet,
                    'diferencia': stock_db - stock_sheet
                })
        
        if diferencias:
            print(f"\n⚠️  SE ENCONTRARON {len(diferencias)} DIFERENCIAS DE STOCK:\n")
            
            # Mostrar primeras 20 diferencias
            for i, diff in enumerate(diferencias[:20], 1):
                print(f"{i}. {diff['codigo']} - {diff['descripcion'][:40]}")
                print(f"   DB: {diff['stock_db']} | Sheet: {diff['stock_sheet']} | Diferencia: {diff['diferencia']}")
            
            if len(diferencias) > 20:
                print(f"\n   ... y {len(diferencias) - 20} diferencias más")
            
            # Estadísticas
            print(f"\n📈 ESTADÍSTICAS DE DIFERENCIAS:")
            print(f"   - Promedio de diferencia: {sum(d['diferencia'] for d in diferencias) / len(diferencias):.2f}")
            print(f"   - Mayor diferencia: {max(diferencias, key=lambda x: abs(x['diferencia']))['diferencia']}")
            print(f"   - Total de items con diferencias: {len(diferencias)}")
            print(f"   - % de items con diferencias: {(len(diferencias)/len(en_ambos)*100):.1f}%")
        else:
            print(f"✅ ¡STOCK PERFECTAMENTE SINCRONIZADO!")
        
        # 8. Mostrar items solo en uno u otro
        if solo_en_db:
            print(f"\n⚠️  ARTÍCULOS SOLO EN BD (no en Sheets): {len(solo_en_db)}")
            for codigo in list(solo_en_db)[:10]:
                art = db_dict[codigo]
                print(f"   - {codigo}: {art.descripcion[:50]} (Stock: {art.stock_actual})")
            if len(solo_en_db) > 10:
                print(f"   ... y {len(solo_en_db) - 10} más")
        
        if solo_en_sheet:
            print(f"\n⚠️  ARTÍCULOS SOLO EN SHEETS (no en BD): {len(solo_en_sheet)}")
            for codigo in list(solo_en_sheet)[:10]:
                art = sheet_dict[codigo]
                print(f"   - {codigo}: {art.get('descripcion', 'Sin descripción')[:50]}")
            if len(solo_en_sheet) > 10:
                print(f"   ... y {len(solo_en_sheet) - 10} más")
        
        # 9. Recomendación
        print(f"\n{'='*80}")
        print(f"💡 RECOMENDACIONES:")
        print(f"{'='*80}")
        
        if diferencias or solo_en_db or solo_en_sheet:
            print("\n⚠️  EL STOCK NO ESTÁ SINCRONIZADO. Acciones sugeridas:")
            print("\n1. Sincronizar desde Google Sheets a la BD:")
            print("   cd /home/sgi_user/proyectos/sistema_gestion_ima")
            print(f"   ./venv/bin/python3 -c \"")
            print(f"from back.database import get_db")
            print(f"from back.gestion.sincronizacion_manager import sincronizar_articulos_desde_sheet")
            print(f"db = next(get_db())")
            print(f"resultado = sincronizar_articulos_desde_sheet(db, {usuario.id_empresa})")
            print(f"print(resultado)")
            print(f"   \"")
            
            print("\n2. O usar el endpoint de la API:")
            print(f"   POST /api/sincronizacion/articulos")
            print(f"   (requiere autenticación del usuario admin_ropa)")
        else:
            print("\n✅ EL STOCK ESTÁ PERFECTAMENTE SINCRONIZADO")
            print("   No se requiere ninguna acción.")
        
        print()
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
