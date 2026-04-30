#!/usr/bin/env python3
"""
Revisión manual Sheets ↔ DB: mismos códigos y mismos campos que usa la sync
(`TablasHandler._mapear_fila` / modelo `Articulo`).
"""
import sys
from pathlib import Path
from typing import Any, Dict, List

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sqlmodel import Session, select
from back.database import engine
from back.modelos import Articulo, ConfiguracionEmpresa
from back.utils.tablas_handler import TablasHandler

# Misma tolerancia que en operación manual: evita ruido por decimales
EPS_PRECIO = 0.02
EPS_STOCK = 0.02


def _a_float(v: Any) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("$", "").replace(" ", "")
    if not s:
        return 0.0
    s = "".join(ch for ch in s if ch.isdigit() or ch in ".,-")
    if not s:
        return 0.0
    try:
        if "." in s and "," in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        return float(s)
    except ValueError:
        return 0.0


def _norm_txt(s: Any) -> str:
    return str(s or "").strip().lower()


def comparar_db_vs_sheets(id_empresa: int):
    """
    Compara la DB con Google Sheets para detectar desincronizaciones
    """
    print(f"\n{'='*80}")
    print(f"COMPARACIÓN DB VS GOOGLE SHEETS - Empresa ID: {id_empresa}")
    print(f"{'='*80}\n")
    
    with Session(engine) as db:
        try:
            # 1. VERIFICAR QUE LA EMPRESA TENGA SHEET CONFIGURADO
            config_empresa = db.get(ConfiguracionEmpresa, id_empresa)
            if not config_empresa or not config_empresa.link_google_sheets:
                print(f"❌ La empresa {id_empresa} NO tiene Google Sheet configurado")
                return
            
            print(f"✓ Empresa {id_empresa}: {config_empresa.nombre_negocio}")
            print(f"✓ Google Sheet: {config_empresa.link_google_sheets}\n")
            
            # 2. LEER DATOS DEL GOOGLE SHEET
            print("📥 Leyendo Google Sheets...")
            handler = TablasHandler(id_empresa=id_empresa, db=db)
            articulos_sheet = handler.cargar_articulos()
            
            if not articulos_sheet:
                print("⚠️  No se encontraron artículos en Google Sheets")
                return
            
            print(f"✓ Total artículos en Sheet: {len(articulos_sheet)}\n")
            
            # 3. LEER DATOS DE LA BD
            print("📥 Leyendo Base de Datos...")
            articulos_db = db.exec(
                select(Articulo).where(Articulo.id_empresa == id_empresa)
            ).all()
            
            print(f"✓ Total artículos en DB: {len(articulos_db)}\n")
            
            # 4. CREAR DICCIONARIOS PARA COMPARACIÓN
            # Formato: {codigo: datos_completos}
            codigos_sheet = {}
            codigos_db = {}
            
            # Procesar Sheet
            for fila in articulos_sheet:
                codigo = fila.get('codigo_interno')
                if codigo:
                    codigo = str(codigo).strip()
                    # Campos alineados con TablasHandler + Articulo (precio_venta / stock_actual)
                    codigos_sheet[codigo] = {
                        'descripcion': fila.get('descripcion', ''),
                        'precio_venta': _a_float(
                            fila.get('precio_venta', fila.get('precio_final', fila.get('precio', 0)))
                        ),
                        'stock_actual': _a_float(
                            fila.get('stock_actual', fila.get('stock', 0))
                        ),
                        'categoria': fila.get('categoria', ''),
                        'marca': fila.get('marca', ''),
                        'fila_sheet': fila,
                    }
            
            # Procesar DB
            for articulo in articulos_db:
                codigo = str(articulo.codigo_interno).strip() if articulo.codigo_interno else None
                if codigo:
                    codigos_db[codigo] = {
                        'descripcion': articulo.descripcion,
                        'precio_venta': float(articulo.precio_venta),
                        'stock_actual': float(articulo.stock_actual),
                        'categoria': articulo.categoria.nombre if articulo.categoria else '',
                        'marca': articulo.marca.nombre if articulo.marca else '',
                        'objeto_db': articulo,
                    }
            
            # 5. ANÁLISIS COMPARATIVO
            print(f"{'='*80}")
            print("ANÁLISIS DE DIFERENCIAS")
            print(f"{'='*80}\n")
            
            # Códigos SOLO en Sheet (no están en DB)
            codigos_solo_sheet = set(codigos_sheet.keys()) - set(codigos_db.keys())
            if codigos_solo_sheet:
                print(f"🔴 CÓDIGOS EN SHEETS PERO NO EN DB: {len(codigos_solo_sheet)}")
                print(f"{'─'*80}")
                for codigo in sorted(codigos_solo_sheet)[:20]:  # Mostrar primeros 20
                    info = codigos_sheet[codigo]
                    print(f"  Código: {codigo}")
                    print(f"    Descripción: {info['descripcion']}")
                    print(f"    Stock: {info['stock_actual']}")
                    print(f"    Precio venta: ${info['precio_venta']}")
                    print()
                
                if len(codigos_solo_sheet) > 20:
                    print(f"  ... y {len(codigos_solo_sheet) - 20} códigos más\n")
            else:
                print("✅ Todos los códigos de Sheets están en la DB\n")
            
            # Códigos SOLO en DB (no están en Sheet)
            codigos_solo_db = set(codigos_db.keys()) - set(codigos_sheet.keys())
            if codigos_solo_db:
                print(f"🟠 CÓDIGOS EN DB PERO NO EN SHEETS: {len(codigos_solo_db)}")
                print(f"{'─'*80}")
                for codigo in sorted(codigos_solo_db)[:20]:  # Mostrar primeros 20
                    info = codigos_db[codigo]
                    print(f"  Código: {codigo}")
                    print(f"    Descripción: {info['descripcion']}")
                    print(f"    Categoría: {info['categoria']}")
                    print()
                
                if len(codigos_solo_db) > 20:
                    print(f"  ... y {len(codigos_solo_db) - 20} códigos más\n")
            else:
                print("✅ Todos los códigos de la DB están en Sheets\n")
            
            # Códigos que existen en ambos pero con datos diferentes
            codigos_ambos = set(codigos_sheet.keys()) & set(codigos_db.keys())
            diferencias: List[Dict[str, Any]] = []

            for codigo in codigos_ambos:
                sheet = codigos_sheet[codigo]
                db_data = codigos_db[codigo]

                if _norm_txt(sheet['descripcion']) != _norm_txt(db_data['descripcion']):
                    diferencias.append(
                        {
                            'codigo': codigo,
                            'tipo': 'Descripción',
                            'sheet': sheet['descripcion'],
                            'db': db_data['descripcion'],
                        }
                    )
                if abs(sheet['precio_venta'] - db_data['precio_venta']) > EPS_PRECIO:
                    diferencias.append(
                        {
                            'codigo': codigo,
                            'tipo': 'Precio venta',
                            'sheet': sheet['precio_venta'],
                            'db': db_data['precio_venta'],
                        }
                    )
                if abs(sheet['stock_actual'] - db_data['stock_actual']) > EPS_STOCK:
                    diferencias.append(
                        {
                            'codigo': codigo,
                            'tipo': 'Stock',
                            'sheet': sheet['stock_actual'],
                            'db': db_data['stock_actual'],
                        }
                    )
                if _norm_txt(sheet['categoria']) != _norm_txt(db_data['categoria']):
                    diferencias.append(
                        {
                            'codigo': codigo,
                            'tipo': 'Categoría',
                            'sheet': sheet['categoria'],
                            'db': db_data['categoria'],
                        }
                    )
                if _norm_txt(sheet['marca']) != _norm_txt(db_data['marca']):
                    diferencias.append(
                        {
                            'codigo': codigo,
                            'tipo': 'Marca',
                            'sheet': sheet['marca'],
                            'db': db_data['marca'],
                        }
                    )

            codigos_con_diff = {d['codigo'] for d in diferencias}

            if diferencias:
                print(
                    f"🟡 DIFERENCIAS DE CAMPO (mismo código en Sheet y DB): {len(diferencias)} filas, "
                    f"{len(codigos_con_diff)} códigos afectados"
                )
                print(f"{'─'*80}")
                for diff in diferencias[:25]:
                    print(f"  Código: {diff['codigo']}")
                    print(f"    {diff['tipo']}:")
                    print(f"      Sheet: {diff['sheet']}")
                    print(f"      DB:    {diff['db']}")
                    print()

                if len(diferencias) > 25:
                    print(f"  ... y {len(diferencias) - 25} diferencias más\n")
            else:
                print("✅ Mismos campos revisados coinciden entre Sheet y DB (descripción, precio venta, stock, categoría, marca)\n")
            
            # 6. RESUMEN FINAL
            print(f"{'='*80}")
            print("RESUMEN")
            print(f"{'='*80}")
            print(f"Total en Sheets:           {len(codigos_sheet)}")
            print(f"Total en DB:               {len(codigos_db)}")
            print(f"Sincronizados (en ambos):  {len(codigos_ambos)}")
            print(f"Solo en Sheets (FALTA):    {len(codigos_solo_sheet)}")
            print(f"Solo en DB (EXTRA):        {len(codigos_solo_db)}")
            print(f"Diferencias de campo:     {len(diferencias)} ({len(codigos_con_diff)} códigos)")
            
            sincronizacion_pct = (len(codigos_ambos) / len(codigos_sheet) * 100) if codigos_sheet else 0
            print(f"\n📊 Nivel de sincronización: {sincronizacion_pct:.1f}%")
            print(f"{'='*80}\n")
            
            return {
                'total_sheet': len(codigos_sheet),
                'total_db': len(codigos_db),
                'sincronizados': len(codigos_ambos),
                'solo_sheet': len(codigos_solo_sheet),
                'solo_db': len(codigos_solo_db),
                'desincronizados': len(diferencias),
                'codigos_con_diferencias_campo': len(codigos_con_diff),
                'codigos_solo_sheet': sorted(list(codigos_solo_sheet))[:50],
                'codigos_solo_db': sorted(list(codigos_solo_db))[:50],
            }
            
        except Exception as e:
            print(f"\n❌ ERROR CAPTURADO:")
            print(f"   Tipo: {type(e).__name__}")
            print(f"   Mensaje: {str(e)}")
            import traceback
            print(f"\n   Traceback completo:")
            traceback.print_exc()
            return None


if __name__ == "__main__":
    # ID por CLI o default 33 (Distribuidora El Negro), alineado con test_sincronizacion_manual.py
    id_empresa = int(sys.argv[1]) if len(sys.argv) > 1 else 33

    resultado = comparar_db_vs_sheets(id_empresa)

    if resultado and (
        resultado['solo_sheet'] > 0
        or resultado['solo_db'] > 0
        or resultado.get('desincronizados', 0) > 0
    ):
        print("\n⚠️  RECOMENDACIÓN: Tras revisar, ejecutá la sync de artículos, por ejemplo:")
        print(f"     python3 testing/test_sincronizacion_manual.py")
        print("     (o el endpoint de actualización masiva que usen en producción)")
