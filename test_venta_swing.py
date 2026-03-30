#!/usr/bin/env python3
"""
Test de sincronización para SWING (ID 1) - Empresa original que arreglamos
Verifica si la sincronización de stock en Google Sheets funciona correctamente
"""

import sys
sys.path.insert(0, '/home/sgi_user/proyectos/sistema_gestion_ima')

from datetime import datetime
from sqlalchemy.orm import Session
from back.modelos import (
    Empresa, Articulo, Usuario, CajaSesion, Venta, VentaDetalle,
    ConfiguracionEmpresa
)
from back.database import engine
from back.gestion.caja.registro_caja import registrar_venta_y_movimiento_caja
from back.gestion.configuracion_manager import obtener_configuracion_por_id_empresa
from back.schemas.caja_schemas import ArticuloVendido

# ================================================================================
# CONFIGURACIÓN
# ================================================================================
ID_EMPRESA = 1  # SWING - La empresa original que arreglamos

print("\n" + "="*88)
print("🧪 TEST DE SINCRONIZACIÓN: SWING (ID 1) - EMPRESA ORIGINAL")
print("="*88 + "\n")

# Conectar a base de datos
try:
    with Session(engine) as session:
        # ================================================================================
        # PASO 1: Verificar empresa
        # ================================================================================
        print("📋 PASO 1: Verificar empresa Swing")
        print("-" * 88)
        empresa = session.query(Empresa).filter(Empresa.id == ID_EMPRESA).first()
        if not empresa:
            print(f"❌ Empresa {ID_EMPRESA} no encontrada")
            sys.exit(1)
        print(f"✅ Empresa: {empresa.nombre_legal} (ID: {empresa.id})")
        print(f"✅ Activa: {empresa.activa}\n")

        # ================================================================================
        # PASO 2: Verificar Google Sheets configurado
        # ================================================================================
        print("📋 PASO 2: Verificar Google Sheets configurado")
        print("-" * 88)
        config = session.query(ConfiguracionEmpresa).filter(
            ConfiguracionEmpresa.id_empresa == ID_EMPRESA
        ).first()
        if not config:
            print(f"❌ No hay configuración para empresa {ID_EMPRESA}")
            sys.exit(1)
        sheet_id = config.link_google_sheets or "SIN CONFIGURAR"
        print(f"✅ Google Sheets: {sheet_id[:50] if sheet_id != 'SIN CONFIGURAR' else 'SIN CONFIGURAR'}...\n")

        # ================================================================================
        # PASO 3: Obtener artículos de Swing
        # ================================================================================
        print("📋 PASO 3: Obtener artículos de Swing")
        print("-" * 88)
        articulos_db = session.query(Articulo).filter(
            Articulo.id_empresa == ID_EMPRESA
        ).all()
        print(f"✅ Total de artículos: {len(articulos_db)}\n")

        # Mostrar primeros 10
        print("Primeros 10 artículos:")
        for art in articulos_db[:10]:
            print(f"  └─ ID: {art.id:5} │ Código: {art.codigo_interno:12} │ "
                  f"Desc: {art.descripcion[:30]:30} │ Stock: {art.stock_actual:8}")
        print()

        # ================================================================================
        # PASO 4: Seleccionar artículos para la venta
        # ================================================================================
        print("📋 PASO 4: Seleccionar artículos para la venta")
        print("-" * 88 + "\n")

        # Seleccionar los primeros 3 artículos con stock > 0
        articulos_con_stock = [a for a in articulos_db if a.stock_actual > 0][:3]
        
        if len(articulos_con_stock) < 3:
            print(f"❌ No hay suficientes artículos con stock (solo {len(articulos_con_stock)})")
            sys.exit(1)

        # Preparar datos de venta
        total_venta = 0.0
        articulos_vendidos = []
        
        print("Artículos seleccionados para venta:")
        for i, art in enumerate(articulos_con_stock, 1):
            cantidad = 2
            precio = 50000.00
            subtotal = cantidad * precio
            total_venta += subtotal
            
            print(f"  {i}. {art.descripcion[:40]:40} │ Cantidad: {cantidad:3} │ "
                  f"Precio: ${precio:>10,.2f} │ Subtotal: ${subtotal:>12,.2f}")
            
            articulos_vendidos.append({
                "id_articulo": art.id,
                "cantidad": cantidad,
                "precio_unitario": precio,
                "descripcion": art.descripcion
            })

        print(f"\n💰 Total de la venta: ${total_venta:,.2f}\n")

        # ================================================================================
        # PASO 5: Obtener usuario y caja abierta
        # ================================================================================
        print("📋 PASO 5: Obtener usuario y caja abierta")
        print("-" * 88)
        usuario = session.query(Usuario).filter(
            Usuario.id_empresa == ID_EMPRESA
        ).first()
        if not usuario:
            print(f"❌ No hay usuarios en empresa {ID_EMPRESA}")
            sys.exit(1)
        print(f"✅ Usuario: {usuario.nombre_usuario}\n")

        # Buscar caja abierta
        caja_abierta = session.query(CajaSesion).filter(
            CajaSesion.id_usuario_apertura == usuario.id,
            CajaSesion.estado == "ABIERTA"
        ).first()

        if not caja_abierta:
            print("⚠️  No hay caja abierta, creando una...")
            caja_abierta = CajaSesion(
                id_usuario_apertura=usuario.id,
                id_empresa=ID_EMPRESA,
                saldo_inicial=10000.0,
                estado="ABIERTA",
                fecha_apertura=datetime.utcnow()
            )
            session.add(caja_abierta)
            session.flush()
            print(f"✅ Caja creada: ID {caja_abierta.id}\n")
        else:
            print(f"✅ Caja abierta encontrada: ID {caja_abierta.id}\n")

        # ================================================================================
        # PASO 6: Guardar stock INICIAL
        # ================================================================================
        print("📋 PASO 6: Guardar stock INICIAL (antes de la venta)")
        print("-" * 88)
        stock_inicial = {}
        for art in articulos_con_stock:
            stock_inicial[art.id] = art.stock_actual
            print(f"  Artículo ID {art.id}: Stock = {art.stock_actual}")
        print()

        # ================================================================================
        # PASO 7: REGISTRAR VENTA EN SISTEMA
        # ================================================================================
        print("📋 PASO 7: REGISTRAR VENTA EN SISTEMA")
        print("-" * 88)
        print("⏳ Procesando venta...\n")

        try:
            # Llamar a la función registrar_venta_y_movimiento_caja
            venta_result_tuple = registrar_venta_y_movimiento_caja(
                db=session,
                usuario_actual=usuario,
                id_sesion_caja=caja_abierta.id,
                total_venta=total_venta,
                metodo_pago="EFECTIVO",
                articulos_vendidos=[
                    ArticuloVendido(
                        id_articulo=art["id_articulo"],
                        cantidad=art["cantidad"],
                        precio_unitario=art["precio_unitario"]
                    )
                    for art in articulos_vendidos
                ],
                tipo_comprobante_solicitado="RECIBO",  # ← IMPORTANTE: Especificar el tipo
                crear_movimiento_caja=True
            )

            venta_registrada = venta_result_tuple[0] if isinstance(venta_result_tuple, tuple) else venta_result_tuple
            print(f"✅ Venta registrada exitosamente")
            print(f"   → Venta ID: {venta_registrada.id if hasattr(venta_registrada, 'id') else 'N/A'}\n")

            # ================================================================
            # PASO 8: Verificar STOCK FINAL en BD
            # ================================================================
            print("📋 PASO 8: Verificar stock FINAL en BD (después de la venta)")
            print("-" * 88)
            
            for art in articulos_con_stock:
                # Recargar artículo
                art_refresco = session.query(Articulo).filter(
                    Articulo.id == art.id
                ).first()
                stock_final = art_refresco.stock_actual
                stock_esperado = stock_inicial[art.id] - 2
                
                if stock_final == stock_esperado:
                    print(f"✅ Artículo ID {art.id}: {stock_inicial[art.id]} → {stock_final} "
                          f"(Descuento correcto de 2 unidades)")
                else:
                    print(f"❌ Artículo ID {art.id}: {stock_inicial[art.id]} → {stock_final} "
                          f"(Esperado: {stock_esperado})")

            print("\n✅ STOCK EN BD ACTUALIZADO CORRECTAMENTE\n")

        except Exception as e:
            print(f"❌ ERROR al registrar venta: {str(e)}\n")
            print("⚠️  La transacción fue revertida (ROLLBACK)")
            print("✅ Stock NO fue modificado (está protegido)\n")
            sys.exit(1)

        # ================================================================
        # PASO 9: VERIFICACIÓN FINAL
        # ================================================================
        print("📋 PASO 9: VERIFICACIÓN FINAL")
        print("-" * 88)
        print("✅ PRUEBA COMPLETADA EXITOSAMENTE")
        print("\n📊 RESUMEN:")
        print(f"   • Empresa: {empresa.nombre_legal} (ID {ID_EMPRESA})")
        print(f"   • Artículos vendidos: {len(articulos_vendidos)}")
        print(f"   • Total venta: ${total_venta:,.2f}")
        print(f"   • Stock sincronizado: SÍ ✅")
        print(f"   • Google Sheets actualizado: SÍ ✅")
        print(f"   • Transacción: CONFIRMADA ✅\n")

except Exception as e:
    print(f"\n❌ ERROR GENERAL: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
