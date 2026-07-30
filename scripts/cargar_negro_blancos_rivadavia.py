#!/usr/bin/env python3
"""
Agrega a Rivadavia (39) productos de El Negro (33) que NO estaban en el match
de El Refugio: precio/costo en blanco (0), con códigos de barra reales.

Solo importa artículos de El Negro que tengan al menos un barcode y cuyo
barcode/código no exista ya en Rivadavia.

Uso:
  back/venv/bin/python scripts/cargar_negro_blancos_rivadavia.py --dry-run
  back/venv/bin/python scripts/cargar_negro_blancos_rivadavia.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from back.database import engine
from back.gestion import modo_especial_manager
from back.modelos import Articulo, Categoria
from back.schemas.modo_especial_schemas import ProductoModoEspecialCreate, UnidadMedidaEnum

ID_NEGRO = 33
ID_DESTINO = 39


def _categorias(articulo: Articulo) -> list[str]:
    raw = getattr(articulo, "categorias", None)
    if isinstance(raw, list) and raw:
        return [str(c).strip() for c in raw if str(c).strip()]
    if articulo.categoria and articulo.categoria.nombre:
        return [articulo.categoria.nombre]
    return ["El Negro"]


def _unidad(articulo: Articulo) -> str:
    u = (articulo.unidad_venta or "unidad").strip().lower()
    valid = {e.value for e in UnidadMedidaEnum}
    return u if u in valid else "unidad"


def main() -> int:
    dry = "--dry-run" in sys.argv
    with Session(engine) as db:
        destinos = db.exec(
            select(Articulo)
            .where(Articulo.id_empresa == ID_DESTINO, Articulo.activo == True)
            .options(selectinload(Articulo.codigos))
        ).all()
        codigos_dest = {(a.codigo_interno or "").strip() for a in destinos if a.codigo_interno}
        barras_dest: set[str] = set()
        for a in destinos:
            for c in a.codigos or []:
                if c.codigo:
                    barras_dest.add(c.codigo.strip())

        negros = db.exec(
            select(Articulo)
            .where(Articulo.id_empresa == ID_NEGRO, Articulo.activo == True)
            .options(selectinload(Articulo.codigos), selectinload(Articulo.categoria))
        ).all()

        candidatos = []
        omit_sin_barra = 0
        omit_ya = 0
        for a in negros:
            bars = [c.codigo.strip() for c in (a.codigos or []) if c.codigo and c.codigo.strip()]
            if not bars:
                omit_sin_barra += 1
                continue
            codigo = (a.codigo_interno or "").strip()
            if not codigo:
                omit_sin_barra += 1
                continue
            if codigo in codigos_dest or any(b in barras_dest for b in bars):
                omit_ya += 1
                continue
            candidatos.append((a, bars))

        print(
            f"El Negro activos={len(negros)} | sin_barra={omit_sin_barra} | "
            f"ya_en_rivadavia={omit_ya} | a_crear={len(candidatos)}"
        )
        for a, bars in candidatos[:8]:
            print(f"  {codigo if (codigo:=a.codigo_interno) else '?'} | {(a.descripcion or '')[:50]} | {bars[:2]}")

        if dry:
            print("[dry-run] sin escribir")
            return 0

        creados = 0
        errores = 0
        usados = set(codigos_dest)
        for a, bars in candidatos:
            codigo = a.codigo_interno.strip()
            if codigo in usados:
                codigo = f"{codigo}-N"
            usados.add(codigo)
            try:
                modo_especial_manager.crear_producto(
                    db,
                    ID_DESTINO,
                    ProductoModoEspecialCreate(
                        codigo_interno=codigo,
                        descripcion=(a.descripcion or codigo).strip(),
                        precio_venta=0.0,
                        precio_costo=0.0,
                        categorias=_categorias(a),
                        stock=0.0,
                        barcodes=bars,
                        unidad=UnidadMedidaEnum(_unidad(a)),
                        tasa_iva=0.21,
                    ),
                    omitir_conflictos_barcode=True,
                    commit=True,
                )
                creados += 1
            except Exception as exc:
                errores += 1
                print(f"ERROR {codigo}: {exc}")

        print(f"\n=== Resultado: creados={creados} errores={errores}")
    return 0 if errores == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
