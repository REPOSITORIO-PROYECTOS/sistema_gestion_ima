#!/usr/bin/env python3
"""Debug script para diagnosticar búsqueda de artículos"""

import sys
sys.path.insert(0, '/home/sgi_user/proyectos/sistema_gestion_ima')

from back.database import SessionLocal
from back.modelos import Articulo, Usuario
import back.gestion.stock.articulos as articulos_manager

db = SessionLocal()

try:
    # 1. Encontrar usuario admin
    print("=" * 60)
    print("PASO 1: Buscando usuarios ADMIN")
    print("=" * 60)
    
    usuarios = db.query(Usuario).filter(Usuario.email.like('%admin%')).all()
    print(f"Encontrados {len(usuarios)} usuarios admin:")
    
    admin_user = None
    for u in usuarios:
        print(f"  ✓ Email: {u.email}, ID: {u.id}, Empresa: {u.id_empresa}")
        if u.email == 'admin':
            admin_user = u
    
    if not admin_user:
        print("⚠️  No encontré usuario 'admin' exacto. Usando el primero...")
        admin_user = usuarios[0] if usuarios else None
    
    if not admin_user:
        print("❌ No hay usuarios admin. Abortando.")
        sys.exit(1)
    
    print(f"\n✅ Usando usuario: {admin_user.email} (Empresa: {admin_user.id_empresa})")
    
    # 2. Contar artículos en la BD por empresa
    print("\n" + "=" * 60)
    print("PASO 2: Contando artículos en BD por empresa")
    print("=" * 60)
    
    todas_empresas = db.query(Articulo.id_empresa).distinct().all()
    for (emp_id,) in todas_empresas:
        count = db.query(Articulo).filter(Articulo.id_empresa == emp_id).count()
        print(f"  Empresa {emp_id}: {count} artículos")
    
    # 3. Mostrar artículos de la empresa del admin
    print("\n" + "=" * 60)
    print(f"PASO 3: Artículos de empresa {admin_user.id_empresa}")
    print("=" * 60)
    
    articulos = db.query(Articulo).filter(Articulo.id_empresa == admin_user.id_empresa).limit(10).all()
    print(f"Total: {len(articulos)} artículos (mostrando max 10)")
    
    if articulos:
        for a in articulos:
            print(f"  ID: {a.id:4} | {a.descripcion:40} | ${a.precio_venta:8.2f} | Stock: {a.stock_actual:6.1f}")
    else:
        print("  ❌ SIN ARTÍCULOS EN ESTA EMPRESA")
    
    # 4. Probar búsqueda directa con la función de manager
    print("\n" + "=" * 60)
    print("PASO 4: Probando función buscar_articulos_por_termino")
    print("=" * 60)
    
    # Búsqueda vacía (debería retornar todos)
    print("\n  Búsqueda con termino='': ")
    resultados = articulos_manager.buscar_articulos_por_termino(
        db=db,
        id_empresa_actual=admin_user.id_empresa,
        termino="",
        skip=0,
        limit=10
    )
    print(f"    → Encontrados: {len(resultados)} artículos")
    
    # Búsqueda con término que debería coincidir
    if articulos:
        primer_termino = articulos[0].descripcion[:5]
        print(f"\n  Búsqueda con termino='{primer_termino}': ")
        resultados = articulos_manager.buscar_articulos_por_termino(
            db=db,
            id_empresa_actual=admin_user.id_empresa,
            termino=primer_termino,
            skip=0,
            limit=10
        )
        print(f"    → Encontrados: {len(resultados)} artículos")
        for r in resultados[:3]:
            print(f"      • {r.descripcion}")
    
    # Búsqueda con término que NO debería coincidir
    print(f"\n  Búsqueda con termino='dadwdwawdad': ")
    resultados = articulos_manager.buscar_articulos_por_termino(
        db=db,
        id_empresa_actual=admin_user.id_empresa,
        termino="dadwdwawdad",
        skip=0,
        limit=10
    )
    print(f"    → Encontrados: {len(resultados)} artículos (esperado: 0)")

finally:
    db.close()
    print("\n✅ Debug completado")
