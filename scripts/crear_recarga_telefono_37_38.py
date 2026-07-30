#!/usr/bin/env python3
"""
Crea (o repara) el artículo especial RECARGA DE TELEFONO con precio_manual
en de-campo (37) y La Esquina 2 (38).

El cajero ingresa el monto al vender; no descuenta stock.

Uso:
  python scripts/crear_recarga_telefono_37_38.py --dry-run
  python scripts/crear_recarga_telefono_37_38.py --apply
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlmodel import Session, select

from back.database import engine
from back.gestion import modo_especial_manager
from back.modelos import Articulo, ConfiguracionEmpresa
from back.schemas.modo_especial_schemas import ProductoModoEspecialCreate, UnidadMedidaEnum

EMPRESAS = (37, 38)
CODIGO = "RECARGA"
DESCRIPCION = "RECARGA DE TELEFONO"
PRECIO_PLACEHOLDER = 1.0
STOCK_ILIMITADO = 999999.0


def _asegurar(db: Session, id_empresa: int, *, dry: bool) -> str:
    existente = db.exec(
        select(Articulo).where(
            Articulo.id_empresa == id_empresa,
            Articulo.codigo_interno == CODIGO,
        )
    ).first()

    if existente:
        accion = "update"
        print(
            f"  [{id_empresa}] existe id={existente.id} "
            f"pm={existente.precio_manual} activo={existente.activo} desc={existente.descripcion!r}"
        )
        if dry:
            return accion
        existente.descripcion = DESCRIPCION
        existente.precio_venta = PRECIO_PLACEHOLDER
        existente.venta_negocio = PRECIO_PLACEHOLDER
        existente.precio_costo = 0.0
        existente.precio_manual = True
        existente.auto_actualizar_precio = False
        existente.stock_actual = STOCK_ILIMITADO
        existente.activo = True
        db.add(existente)
        db.commit()
    else:
        accion = "create"
        print(f"  [{id_empresa}] crear {CODIGO} / {DESCRIPCION}")
        if dry:
            return accion
        modo_especial_manager.crear_producto(
            db,
            id_empresa,
            ProductoModoEspecialCreate(
                codigo_interno=CODIGO,
                descripcion=DESCRIPCION,
                precio_venta=PRECIO_PLACEHOLDER,
                precio_costo=0.0,
                categorias=["Especiales"],
                stock=STOCK_ILIMITADO,
                barcodes=[CODIGO],
                unidad=UnidadMedidaEnum.unidad,
                tasa_iva=0.21,
            ),
            omitir_conflictos_barcode=True,
            commit=True,
        )
        art = modo_especial_manager._obtener_articulo_por_codigo(db, id_empresa, CODIGO)
        if art is None:
            raise RuntimeError(f"No se pudo crear {CODIGO} en empresa {id_empresa}")
        art.precio_manual = True
        art.auto_actualizar_precio = False
        art.stock_actual = STOCK_ILIMITADO
        art.descripcion = DESCRIPCION
        db.add(art)
        db.commit()

    cfg = db.get(ConfiguracionEmpresa, id_empresa)
    if cfg is not None and not dry:
        cfg.catalogo_version = int(cfg.catalogo_version or 0) + 1
        db.add(cfg)
        db.commit()

    art = db.exec(
        select(Articulo).where(
            Articulo.id_empresa == id_empresa,
            Articulo.codigo_interno == CODIGO,
        )
    ).first()
    if art:
        print(
            f"  [{id_empresa}] OK id={art.id} pm={art.precio_manual} "
            f"pv={art.precio_venta} stock={art.stock_actual} activo={art.activo}"
        )
    return accion


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    dry = bool(args.dry_run)

    print(f"=== RECARGA DE TELEFONO 37/38 ({'DRY-RUN' if dry else 'APPLY'}) ===")
    with Session(engine) as db:
        for eid in EMPRESAS:
            _asegurar(db, eid, dry=dry)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
