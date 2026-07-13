#!/usr/bin/env python3
"""Busca un código de barras en articulos.xls y muestra PrecioVenta si existe."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.cargar_precios_articulos_xls import (  # noqa: E402
    DEFAULT_XLS,
    _barcodes_fila,
    _codigo,
    _descripcion,
    _iter_excel,
    _norm_barcode,
    _precio_venta_fila,
    _resolver_archivo,
)


def buscar(archivo: Path, codigo: str) -> int:
    codigo = _norm_barcode(codigo)
    print(f"Archivo: {archivo}")
    print(f"Buscando: {codigo}\n")

    coincidencias = []
    for i, row in enumerate(_iter_excel(archivo), start=2):
        barras = _barcodes_fila(row)
        id_art = _codigo(row)
        if codigo not in barras and codigo != id_art:
            continue
        precio = _precio_venta_fila(row)
        coincidencias.append(
            {
                "fila": i,
                "desc": _descripcion(row) or row.get("Articulo", ""),
                "precio": precio,
                "barras": barras,
                "id_art": id_art,
            }
        )

    if not coincidencias:
        print("NO ENCONTRADO en este Excel.")
        print(
            "El producto está en stock.csv pero no en articulos.xls del servidor.\n"
            "Copiá tu archivo real de OneDrive a:\n"
            f"  {DEFAULT_XLS}"
        )
        return 1

    for hit in coincidencias:
        print(f"Fila {hit['fila']}: {hit['desc']}")
        print(f"  Barras: {hit['barras']}")
        print(f"  IDArt: {hit['id_art']}")
        print(f"  PrecioVenta: {hit['precio']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("codigo", help="Código de barras o IDArt")
    parser.add_argument("--archivo", type=Path, default=None)
    args = parser.parse_args()
    archivo = _resolver_archivo(args.archivo)
    return buscar(archivo, args.codigo)


if __name__ == "__main__":
    raise SystemExit(main())
