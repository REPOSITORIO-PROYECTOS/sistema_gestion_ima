#!/usr/bin/env python3
"""
Script para analizar dónde se guardan y sincronizan los datos de stock de la empresa Swing (ID 1).
Muestra el flujo completo de datos desde una venta hasta Google Sheets.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'back'))

from sqlmodel import Session, select
from back.database import engine
from back.modelos import Articulo, Venta, VentaDetalle, CajaMovimiento, ConfiguracionEmpresa
from datetime import datetime, timedelta

def analizar_flujo_stock_swing():
    """Analiza el flujo de stock de Swing."""
    
    ID_EMPRESA_SWING = 1
    
    with Session(engine) as session:
        print("\n" + "="*90)
        print("📊 ANÁLISIS DEZ FLUJO DE STOCK DE SWING (EMPRESA ID 1)")
        print("="*90)
        
        # 1. VERIFICAR CONFIGURACIÓN DE GOOGLE SHEETS
        print("\n1️⃣  CONFIGURACIÓN DE GOOGLE SHEETS")
        print("─" * 90)
        config = session.get(ConfiguracionEmpresa, ID_EMPRESA_SWING)
        if config:
            print(f"✅ Google Sheets Link: {config.link_google_sheets[:50]}...")
        else:
            print("❌ NO TIENE CONFIGURACIÓN")
        
        # 2. VERIFICAR ARTÍCULOS DE SWING
        print("\n2️⃣  ARTÍCULOS EN STOCK DE SWING")
        print("─" * 90)
        articulos = session.exec(
            select(Articulo).where(Articulo.id_empresa == ID_EMPRESA_SWING)
        ).all()
        
        print(f"Total de artículos: {len(articulos)}")
        if articulos:
            print("\nPrimeros 5 artículos:")
            for art in articulos[:5]:
                print(f"  └─ ID: {art.id}, Código: {art.codigo_interno}, "
                      f"Descripción: {art.descripcion}, Stock actual: {art.stock_actual}")
        
        # 3. VERIFICAR VENTAS RECIENTES DE SWING
        print("\n3️⃣  VENTAS REGISTRADAS EN BASE DE DATOS (Últimas 5)")
        print("─" * 90)
        hace_7_dias = datetime.utcnow() - timedelta(days=7)
        
        ventas = session.exec(
            select(Venta)
            .where(Venta.id_empresa == ID_EMPRESA_SWING)
            .where(Venta.timestamp >= hace_7_dias)
            .order_by(Venta.timestamp.desc())
            .limit(5)
        ).all()
        
        print(f"Ventas en últimos 7 días: {len(ventas)}")
        if ventas:
            for venta in ventas:
                print(f"\n  Venta ID: {venta.id}")
                print(f"  ├─ Total: ${venta.total:.2f}")
                print(f"  ├─ Cliente: {venta.id_cliente or 'Cliente Final'}")
                print(f"  ├─ Fecha: {venta.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"  ├─ Tipo: {venta.tipo_comprobante_solicitado}")
                
                # Obtener detalles de la venta
                detalles = session.exec(
                    select(VentaDetalle).where(VentaDetalle.id_venta == venta.id)
                ).all()
                
                print(f"  └─ Artículos: {len(detalles)}")
                for detalle in detalles:
                    art = session.get(Articulo, detalle.id_articulo)
                    if art:
                        print(f"     └─ {art.descripcion}: {detalle.cantidad} unid @ ${detalle.precio_unitario:.2f}")
        else:
            print("❌ No hay ventas registradas en los últimos 7 días")
        
        # 4. VERIFICAR MOVIMIENTOS DE CAJA
        print("\n4️⃣  MOVIMIENTOS DE CAJA REGISTRADOS (Últimos 5)")
        print("─" * 90)
        
        movimientos = session.exec(
            select(CajaMovimiento)
            .where(CajaMovimiento.id_usuario.in_(
                session.exec(select(lambda: None)).all()  # Placeholder
            ))
            .limit(5)
        ).all()
        
        print(f"Total de movimientos en el sistema: {session.query(CajaMovimiento).count()}")
        
        # 5. TABLAS INVOLUCRADAS
        print("\n5️⃣  ANATOMÍA DE LAS TABLAS DE STOCK")
        print("─" * 90)
        
        print("""
┌─────────────────────────────────────────────────────────────┐
│ TABLA: articulos                                             │
├─────────────────────────────────────────────────────────────┤
│ ├─ id                                 (PK)                  │
│ ├─ id_empresa                         (FK → empresas)      │
│ ├─ codigo_interno                     (Código único)        │
│ ├─ descripcion                        (Nombre del producto)│
│ ├─ stock_actual            ⬅️ AQUÍ SE DESCUENTA EN VENTA   │
│ ├─ precio_venta                       (Precio de lista)    │
│ ├─ precio_costo                       (Costo)              │
│ └─ ... (otros campos)                                      │
└─────────────────────────────────────────────────────────────┘

         CUANDO SE CREA UNA VENTA:
                    ↓
         ┌──────────────────────────┐
         │ Se crea registro en BD:  │
         │   - venta (cabecera)     │
         │   - venta_detalle (items)│
         │   - stock se descuenta   │
         └────────────┬─────────────┘
                      ↓
         ┌──────────────────────────────────┐
         │ INTENTA SINCRONIZAR:             │
         │ Registra en Google Sheets:       │
         │   - MOVIMIENTOS (tab)            │
         │   - stock (tab) ⬅️ AQUÍ FALLA    │
         └──────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ TABLA: venta                                                 │
├─────────────────────────────────────────────────────────────┤
│ ├─ id                                 (PK)                  │
│ ├─ id_empresa                         (FK → empresas)      │
│ ├─ id_usuario                         (FK → usuarios)      │
│ ├─ id_cliente                         (FK → terceros) OPT  │
│ ├─ total                                                   │
│ ├─ descuento_total                    (Descuento aplicado)│
│ ├─ tipo_comprobante_solicitado         (Factura/Recibo)   │
│ ├─ fecha_creacion                      (Cuándo se registró)│
│ └─ ... (otros campos)                                      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ TABLA: venta_detalle                                         │
├─────────────────────────────────────────────────────────────┤
│ ├─ id                                 (PK)                  │
│ ├─ id_venta                           (FK → venta)         │
│ ├─ id_articulo                        (FK → articulos)     │
│ ├─ cantidad                           (Cuántas unidades)   │
│ ├─ precio_unitario                     (Precio final)       │
│ ├─ descuento_aplicado                  (Descuento item)    │
│ └─ ... (otros campos)                                      │
└─────────────────────────────────────────────────────────────┘
        """)
        
        # 6. FLUJO DETALLADO
        print("\n6️⃣  FLUJO DETALLADO DE UNA VENTA EN SWING")
        print("─" * 90)
        
        print("""
PASO 1: USUARIO REGISTRA VENTA EN SISTEMA
├─ Se valida que el stock sea suficiente
├─ Se crea registro en tabla 'venta' (BD local)
├─ Se crea registros en tabla 'venta_detalle' (BD local)
└─ Se descuenta stock en tabla 'articulos' ✅ (BD local)

PASO 2: INTENTAR SINCRONIZAR CON GOOGLE SHEETS
├─ Se obtiene link_google_sheets de ConfiguracionEmpresa
├─ Se conecta a Google Sheets usando gspread
├─ Se registra movimiento en pestaña "MOVIMIENTOS"
├─ Se descuenta stock en pestaña "stock"
└─ ❌ SI FALLA AQUÍ → El stock NO se sincroniza pero la BD LOCAL sí está actualizada

PASO 3: PROBLEMAS IDENTIFICADOS (YA ARREGLADOS)
└─ ❌ El código NO lanzaba excepción al fallar la sincronización
   └─ Simplemente imprimía una advertencia y continuaba
   └─ Resultado: Stock desincronizado entre BD y Google Sheets
        """)
        
        # 7. VERIFICAR ESTADO ACTUAL
        print("\n7️⃣  ESTADO SUMARIO DE SWING")
        print("─" * 90)
        
        total_articulos = len(articulos)
        total_stock = sum(a.stock_actual for a in articulos) if articulos else 0
        total_ventas = len(ventas)
        valor_stock = sum(a.stock_actual * a.precio_venta for a in articulos) if articulos else 0
        
        print(f"✅ Total de artículos: {total_articulos}")
        print(f"✅ Stock total en unidades: {total_stock}")
        print(f"✅ Valor aproximado del stock: ${valor_stock:,.2f}")
        print(f"✅ Ventas registradas (7 días): {total_ventas}")
        print(f"✅ Google Sheets configurado: {'SÍ' if config and config.link_google_sheets else 'NO'}")
        
        print("\n" + "="*90 + "\n")

if __name__ == "__main__":
    analizar_flujo_stock_swing()
