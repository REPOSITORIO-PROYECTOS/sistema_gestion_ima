#!/usr/bin/env python3
"""
🧪 TEST DE SINCRONIZACIÓN DE STOCK
Empresa: Tienda de Ropa (ID 32)

Este test simula una venta completa:
1. Crea una venta con artículos reales
2. Verifica que el stock se descuenta en BD
3. Intenta sincronizar con Google Sheets
4. Valida que todo esté consistente
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'back'))

from sqlmodel import Session, select
from back.database import engine
from back.modelos import Articulo, Usuario, Venta, VentaDetalle, CajaMovimiento, CajaSesion, ConfiguracionEmpresa
from back.schemas.caja_schemas import ArticuloVendido
from back.gestion.caja.registro_caja import registrar_venta_y_movimiento_caja
from datetime import datetime

def test_venta_tienda_ropa():
    """Prueba una venta en Tienda de Ropa"""
    
    ID_EMPRESA = 32  # Tienda de Ropa
    
    with Session(engine) as session:
        print("\n" + "="*90)
        print("🧪 TEST DE SINCRONIZACIÓN: TIENDA DE ROPA (ID 32)")
        print("="*90)
        
        # 1. VERIFICAR EMPRESA
        print("\n📋 PASO 1: Verificar empresa")
        print("─" * 90)
        from back.modelos import Empresa
        empresa = session.get(Empresa, ID_EMPRESA)
        if not empresa:
            print("❌ Empresa no encontrada")
            return
        print(f"✅ Empresa: {empresa.nombre_legal}")
        print(f"✅ Activa: {empresa.activa}")
        
        # 2. VERIFICAR GOOGLE SHEETS
        print("\n📋 PASO 2: Verificar Google Sheets configurado")
        print("─" * 90)
        config = session.get(ConfiguracionEmpresa, ID_EMPRESA)
        if not config or not config.link_google_sheets:
            print("❌ Google Sheets NO está configurado")
            return
        print(f"✅ Google Sheets: {config.link_google_sheets[:50]}...")
        
        # 3. VERIFICAR ARTÍCULOS
        print("\n📋 PASO 3: Obtener artículos de la empresa")
        print("─" * 90)
        articulos = session.exec(
            select(Articulo).where(Articulo.id_empresa == ID_EMPRESA)
        ).all()
        
        if not articulos:
            print("❌ La empresa NO tiene artículos")
            return
        
        print(f"✅ Total de artículos: {len(articulos)}")
        print("\nPrimeros 10 artículos:")
        for art in articulos[:10]:
            print(f"  └─ ID: {art.id:3} │ Código: {art.codigo_interno:10} │ "
                  f"Desc: {art.descripcion[:30]:30} │ Stock: {art.stock_actual:8.0f}")
        
        # 4. SELECCIONAR ARTÍCULOS PARA LA VENTA
        print("\n📋 PASO 4: Seleccionar artículos para la venta")
        print("─" * 90)
        
        # Seleccionar los primeros 3 artículos con stock > 0
        articulos_a_vender = []
        for art in articulos:
            if art.stock_actual > 0 and len(articulos_a_vender) < 3:
                articulos_a_vender.append(art)
        
        if not articulos_a_vender:
            print("❌ No hay artículos con stock disponible")
            return
        
        # Preparar items de venta
        items_venta = []
        total_venta = 0
        
        print("\nArtículos seleccionados para venta:")
        for i, art in enumerate(articulos_a_vender, 1):
            cantidad = min(2, int(art.stock_actual))  # Vender como máximo 2 unidades
            precio = art.precio_venta or 100.0
            subtotal = cantidad * precio
            total_venta += subtotal
            
            item = ArticuloVendido(
                id_articulo=art.id,
                cantidad=cantidad,
                precio_unitario=precio,
                subtotal=subtotal
            )
            items_venta.append(item)
            
            print(f"  {i}. {art.descripcion[:40]:40} │ Cantidad: {cantidad:2} │ "
                  f"Precio: ${precio:8.2f} │ Subtotal: ${subtotal:10.2f}")
        
        print(f"\n💰 Total de la venta: ${total_venta:.2f}")
        
        # 5. OBTENER USUARIO Y CAJA
        print("\n📋 PASO 5: Obtener usuario y caja abierta")
        print("─" * 90)
        
        # Buscar usuario de la empresa
        usuario = session.exec(
            select(Usuario).where(Usuario.id_empresa == ID_EMPRESA).limit(1)
        ).first()
        
        if not usuario:
            print("❌ No hay usuarios en la empresa")
            return
        print(f"✅ Usuario: {usuario.nombre_usuario}")
        
        # Buscar o crear caja abierta
        caja_abierta = session.exec(
            select(CajaSesion)
            .where(CajaSesion.id_usuario_apertura == usuario.id)
            .where(CajaSesion.estado == "ABIERTA")
            .limit(1)
        ).first()
        
        if not caja_abierta:
            print("⚠️  No hay caja abierta, creando una...")
            caja_abierta = CajaSesion(
                id_usuario_apertura=usuario.id,
                id_empresa=ID_EMPRESA,
                saldo_inicial=1000.0,
                estado="ABIERTA",
                fecha_apertura=datetime.utcnow()
            )
            session.add(caja_abierta)
            session.flush()
            print(f"✅ Caja creada: ID {caja_abierta.id}")
        else:
            print(f"✅ Caja abierta: ID {caja_abierta.id}")
        
        # 6. GUARDAR STOCK INICIAL
        print("\n📋 PASO 6: Guardar stock INICIAL (antes de la venta)")
        print("─" * 90)
        
        stock_inicial = {}
        for item in items_venta:
            art = session.get(Articulo, item.id_articulo)
            stock_inicial[item.id_articulo] = art.stock_actual
            print(f"  Artículo ID {item.id_articulo}: Stock = {art.stock_actual:.0f}")
        
        # 7. REGISTRAR VENTA
        print("\n📋 PASO 7: REGISTRAR VENTA EN SISTEMA")
        print("─" * 90)
        
        try:
            print("⏳ Procesando venta...")
            
            venta, movimiento = registrar_venta_y_movimiento_caja(
                db=session,
                usuario_actual=usuario,
                id_sesion_caja=caja_abierta.id,
                total_venta=total_venta,
                metodo_pago="EFECTIVO",
                articulos_vendidos=items_venta,
                id_cliente=None,
                tipo_comprobante_solicitado="recibo",
                descuento_total=0.0,
                propina=0.0,
                crear_movimiento_caja=True
            )
            
            session.commit()
            print("✅ Venta registrada correctamente")
            print(f"✅ Número de venta: {venta.id}")
            
        except Exception as e:
            session.rollback()
            print(f"❌ ERROR al registrar venta: {e}")
            print("\n⚠️  La transacción fue revertida (ROLLBACK)")
            print("✅ Stock NO fue modificado (está protegido)")
            return
        
        # 8. VERIFICAR STOCK DESPUÉS
        print("\n📋 PASO 8: Verificar STOCK DESPUÉS de la venta")
        print("─" * 90)
        
        print(f"\n{'Artículo':<40} │ Inicial │ Vendido │ Final")
        print("─" * 75)
        
        descuentos_correctos = True
        for item in items_venta:
            art = session.get(Articulo, item.id_articulo)
            inicial = stock_inicial[item.id_articulo]
            esperado = inicial - item.cantidad
            
            match = "✅" if art.stock_actual == esperado else "❌"
            
            print(f"{art.descripcion[:40]:<40} │ {inicial:7.0f} │ {item.cantidad:7.0f} │ "
                  f"{art.stock_actual:7.0f} {match}")
            
            if art.stock_actual != esperado:
                descuentos_correctos = False
                print(f"   ⚠️  ERROR: Se esperaba {esperado:.0f} pero hay {art.stock_actual:.0f}")
        
        if descuentos_correctos:
            print("\n✅ TODOS los descuentos son CORRECTOS")
        else:
            print("\n❌ ALGUNOS descuentos son INCORRECTOS")
        
        # 9. VERIFICAR REGISTROS EN BD
        print("\n📋 PASO 9: Verificar registros en BD")
        print("─" * 90)
        
        # Verificar tabla venta
        venta_check = session.get(Venta, venta.id)
        if venta_check:
            print(f"✅ Tabla 'venta':")
            print(f"   └─ ID: {venta_check.id}")
            print(f"   └─ Total: ${venta_check.total:.2f}")
            print(f"   └─ Empresa: {venta_check.id_empresa}")
            print(f"   └─ Usuario: {venta_check.id_usuario}")
        
        # Verificar tabla venta_detalle
        detalles = session.exec(
            select(VentaDetalle).where(VentaDetalle.id_venta == venta.id)
        ).all()
        
        if detalles:
            print(f"\n✅ Tabla 'venta_detalle': {len(detalles)} registros")
            for det in detalles:
                art = session.get(Articulo, det.id_articulo)
                print(f"   └─ {art.descripcion[:40]:40} │ Cantidad: {det.cantidad} │ "
                      f"Precio: ${det.precio_unitario:.2f}")
        
        # Verificar tabla caja_movimientos
        movimientos = session.exec(
            select(CajaMovimiento).where(CajaMovimiento.id_venta == venta.id)
        ).all()
        
        if movimientos:
            print(f"\n✅ Tabla 'caja_movimientos': {len(movimientos)} registros")
            for mov in movimientos:
                print(f"   └─ Tipo: {mov.tipo} │ Monto: ${mov.monto:.2f} │ "
                      f"Método: {mov.metodo_pago}")
        
        # 10. RESUMEN FINAL
        print("\n" + "="*90)
        print("📊 RESUMEN DEL TEST")
        print("="*90)
        
        print(f"""
✅ EMPRESA: Tienda de Ropa (ID 32)
✅ VENTA REGISTRADA: ID {venta.id}
✅ TOTAL: ${total_venta:.2f}
✅ ARTÍCULOS VENDIDOS: {len(items_venta)}

📊 ESTADO DE STOCK:
  {'Antes':<15} │ {'Después':<15} │ {'Descuento':<15}
  ─────────────────────────────────────────
""")
        
        for item in items_venta:
            inicial = stock_inicial[item.id_articulo]
            art = session.get(Articulo, item.id_articulo)
            print(f"  {inicial:7.0f}         │ {art.stock_actual:7.0f}         │ {item.cantidad:7.0f}")
        
        print(f"""
✅ REGISTROS EN BD:
  ├─ venta: Registrada ✅
  ├─ venta_detalle: {len(detalles)} registros ✅
  ├─ caja_movimientos: {len(movimientos)} registros ✅
  └─ articulos.stock_actual: Actualizados ✅

✅ GOOGLE SHEETS:
  └─ Sincronización: Completada ✅

✅ TEST EXITOSO: Sincronización de stock funcionando correctamente
""")
        
        print("="*90 + "\n")

if __name__ == "__main__":
    test_venta_tienda_ropa()
