#!/usr/bin/env python3
"""
Importa `datos /stock.csv` (Stock Valorizado) a empresas DEMO separadas.

- de-campo: stock real del CSV
- La Esquina 2: mismo catálogo con stock = 0

NO toca La Esquina prod (35) ni FULL24 (36).
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlmodel import Session, func, select

from back.database import engine
from back.gestion import modo_especial_manager
from back.modelos import Articulo, ConfiguracionEmpresa, Empresa
from back.schemas.modo_especial_schemas import (
    BulkProductosRequest,
    ImportExportResumen,
    ProductoModoEspecialCreate,
    UnidadMedidaEnum,
)

DEFAULT_CSV = ROOT / "datos /stock.csv"
NOMBRE_LA_ESQUINA_2 = "La Esquina 2"
NOMBRE_DE_CAMPO = "de-campo"
ID_LA_ESQUINA_PROD = 35
ID_F24_PROD = 36
MARKUP_PRECIO = 1.5


@dataclass
class FilaStockValorizado:
    codigo_interno: str
    descripcion: str
    marca: str
    costo: float
    stock: float


def _parse_numero(valor: Optional[str]) -> Optional[float]:
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    return modo_especial_manager._parse_numero_csv(texto)


def _precio_desde_costo(costo: float) -> float:
    if costo <= 0:
        return 0.0
    return round(costo * MARKUP_PRECIO, 2)


def leer_stock_valorizado(ruta: Path) -> List[FilaStockValorizado]:
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {ruta}")

    contenido = ruta.read_bytes().decode("latin-1")
    filas: List[FilaStockValorizado] = []

    for linea in contenido.splitlines():
        if not linea.strip():
            continue
        if linea.startswith(";Stock Valorizado"):
            continue
        if "Código" in linea and "Descripción" in linea:
            continue
        if "Pág." in linea or "TOTAL" in linea.upper():
            continue

        partes = linea.split(";")
        if len(partes) < 10:
            continue

        codigo = partes[1].strip()
        descripcion = partes[2].strip()
        marca = partes[6].strip() if len(partes) > 6 else ""
        costo = _parse_numero(partes[8] if len(partes) > 8 else "") or 0.0
        stock = _parse_numero(partes[9] if len(partes) > 9 else "") or 0.0

        if not codigo or not descripcion:
            continue

        filas.append(
            FilaStockValorizado(
                codigo_interno=codigo,
                descripcion=descripcion,
                marca=marca,
                costo=costo,
                stock=max(stock, 0.0),
            )
        )

    return filas


def _a_productos(
    filas: List[FilaStockValorizado],
    *,
    stock_override: Optional[float],
) -> List[ProductoModoEspecialCreate]:
    productos: List[ProductoModoEspecialCreate] = []
    for fila in filas:
        stock = stock_override if stock_override is not None else fila.stock
        categorias = [fila.marca] if fila.marca else ["General"]
        productos.append(
            ProductoModoEspecialCreate(
                codigo_interno=fila.codigo_interno,
                descripcion=fila.descripcion,
                precio_venta=_precio_desde_costo(fila.costo),
                precio_costo=fila.costo,
                categorias=categorias,
                stock=stock,
                barcodes=[fila.codigo_interno],
                unidad=UnidadMedidaEnum.unidad,
            )
        )
    return productos


def _resolver_id_demo(db: Session, nombre_fantasia: str) -> int:
    empresa = db.exec(
        select(Empresa).where(Empresa.nombre_fantasia == nombre_fantasia)
    ).first()
    if not empresa:
        raise RuntimeError(
            f"No existe empresa demo '{nombre_fantasia}'. "
            "Ejecute scripts/revertir_y_crear_demo_esquina2.py primero."
        )
    if empresa.id in (ID_LA_ESQUINA_PROD, ID_F24_PROD):
        raise RuntimeError(
            f"'{nombre_fantasia}' apunta a empresa prod id={empresa.id}. Abortando."
        )
    return empresa.id


def _verificar_modo_especial(db: Session, id_empresa: int, nombre: str) -> None:
    config = db.get(ConfiguracionEmpresa, id_empresa)
    if not config or not config.modo_especial_habilitado:
        raise RuntimeError(f"{nombre} (id={id_empresa}) no tiene modo especial habilitado.")


def _importar_lote(
    db: Session,
    id_empresa: int,
    productos: List[ProductoModoEspecialCreate],
) -> ImportExportResumen:
    return modo_especial_manager.bulk_upsert(
        db,
        id_empresa,
        BulkProductosRequest(productos=productos),
        omitir_conflictos_barcode=True,
        commit_por_producto=False,
    )


def _resumen_stock(db: Session, id_empresa: int) -> tuple[int, float]:
    total_articulos = db.exec(
        select(func.count())
        .select_from(Articulo)
        .where(Articulo.id_empresa == id_empresa, Articulo.activo == True)
    ).one()
    total_stock = db.exec(
        select(func.coalesce(func.sum(Articulo.stock_actual), 0.0))
        .where(Articulo.id_empresa == id_empresa, Articulo.activo == True)
    ).one()
    return int(total_articulos), float(total_stock or 0.0)


def main() -> int:
    parser = argparse.ArgumentParser(description="Importar stock valorizado a la-esquina y de-campo")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Ruta al CSV Stock Valorizado")
    args = parser.parse_args()

    filas = leer_stock_valorizado(args.csv)
    if not filas:
        print("No se encontraron productos en el CSV.")
        return 1

    print(f"CSV: {args.csv}")
    print(f"Productos leídos: {len(filas)}")
    print(f"Stock total en CSV: {sum(f.stock for f in filas):,.0f}")

    cargas = (
        (NOMBRE_DE_CAMPO, None),
        (NOMBRE_LA_ESQUINA_2, 0.0),
    )

    with Session(engine) as db:
        for nombre, stock_override in cargas:
            id_empresa = _resolver_id_demo(db, nombre)
            _verificar_modo_especial(db, id_empresa, nombre)
            productos = _a_productos(filas, stock_override=stock_override)
            print(f"\nImportando en {nombre} (id={id_empresa})...")
            resumen = _importar_lote(db, id_empresa, productos)
            articulos, stock_total = _resumen_stock(db, id_empresa)
            print(
                f"  Creados: {resumen.creados} | Actualizados: {resumen.actualizados} | "
                f"Errores: {resumen.errores}"
            )
            print(f"  Artículos activos: {articulos} | Stock total: {stock_total:,.0f}")
            if resumen.detalle_errores:
                print("  Primeros errores:")
                for err in resumen.detalle_errores[:5]:
                    print(f"    - {err}")

    print("\nImportación finalizada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
