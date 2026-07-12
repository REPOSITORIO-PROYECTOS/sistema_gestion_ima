#!/usr/bin/env python3
"""
Resetea y carga precios SOLO desde articulos.xls (columna PrecioVenta).

- Empresas 37 y 38: precio_venta = 0 primero, luego solo PrecioVenta del Excel.
- Sin márgenes estimados ni otras fuentes.
- Empresa 38: no modifica stock (sigue en 1000).

Uso:
  PYTHONPATH=. back/venv/bin/python scripts/cargar_precios_articulos_xls.py
  PYTHONPATH=. back/venv/bin/python scripts/cargar_precios_articulos_xls.py --archivo "datos /articulos.xls"
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlmodel import Session, select

from back.database import engine
from back.gestion.modo_especial_manager import _incrementar_catalogo_version
from back.modelos import Articulo, ConfiguracionEmpresa

DEFAULT_XLS = ROOT / "datos /articulos.xls"
FALLBACK_CSV = ROOT / "02_articulos_artsxls_elixia.csv"
ID_EMPRESAS = (37, 38)

COLUMNAS_PRECIO_VENTA = (
    "PrecioVenta",
    "Precio Venta",
    "PRECIOVENTA",
    "precioventa",
    "PVMay",  # export CSV Elixia del mismo articulos.xls
)


def _norm(s: Optional[str]) -> str:
    texto = (s or "").upper().strip()
    texto = re.sub(r"\s+", " ", texto)
    texto = re.sub(r"[^A-Z0-9 ]", "", texto)
    return texto


def _parse_num(valor: Optional[str]) -> Optional[float]:
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto or texto.lower() == "nan":
        return None
    texto = texto.replace("$", "").replace(" ", "")
    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        partes = texto.split(",")
        if len(partes) == 2 and len(partes[1]) <= 2:
            texto = texto.replace(",", ".")
        else:
            texto = texto.replace(",", "")
    try:
        return float(texto)
    except ValueError:
        return None


def _precio_venta_fila(row: dict[str, str]) -> Optional[float]:
    for col in row:
        if col.replace(" ", "").lower() == "precioventa":
            precio = _parse_num(row[col])
            if precio is not None and precio >= 0:
                return precio
    for col in COLUMNAS_PRECIO_VENTA:
        if col in row:
            precio = _parse_num(row[col])
            if precio is not None and precio >= 0:
                return precio
    return None


def _norm_barcode(valor: Optional[str]) -> str:
    texto = (valor or "").strip()
    if not texto or texto.lower() == "nan":
        return ""
    if "e" in texto.lower():
        try:
            return str(int(float(texto)))
        except ValueError:
            return texto
    if texto.endswith(".0") and texto[:-2].isdigit():
        return texto[:-2]
    return texto


def _variantes_codigo(codigo: str) -> list[str]:
    cod = (codigo or "").strip()
    if not cod:
        return []
    variantes = {cod}
    if cod.isdigit():
        variantes.add(cod.zfill(6))
        variantes.add(cod.lstrip("0") or "0")
        variantes.add(str(int(cod)))
    return list(variantes)


def _barcode(row: dict[str, str]) -> str:
    for col in (
        "CodBarra",
        "CodigoBarras",
        "Código de Barras",
        "Codigo de Barras",
        "codigo_barras",
        "Barra",
    ):
        v = _norm_barcode(row.get(col))
        if v:
            return v
    return ""


def _codigo(row: dict[str, str]) -> str:
    for col in ("IDArt", "CodProveedor", "Codigo", "Código", "CodigoInterno"):
        v = _norm_barcode(row.get(col))
        if v:
            return v
    return ""


def _descripcion(row: dict[str, str]) -> str:
    for col in ("Articulo", "Producto", "Descripcion", "Descripción"):
        v = (row.get(col) or "").strip()
        if v and v.lower() != "nan":
            return _norm(v)
    return ""


def _iter_csv(ruta: Path) -> Iterable[dict[str, str]]:
    raw = ruta.read_bytes()
    for enc in ("utf-8-sig", "latin-1", "cp1252"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("latin-1", errors="replace")
    delim = ";" if text.count(";") > text.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    for row in reader:
        limpio = {}
        for k, v in row.items():
            clave = (k or "").strip().lstrip("\ufeff")
            limpio[clave] = "" if v is None else str(v).strip()
        yield limpio


def _iter_excel(ruta: Path) -> Iterable[dict[str, str]]:
    import pandas as pd

    df = pd.read_excel(ruta, dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    print(f"  Columnas Excel: {list(df.columns)}")
    for _, series in df.iterrows():
        yield {
            str(k): ("" if pd.isna(v) else str(v).strip())
            for k, v in series.items()
        }


def cargar_precios(ruta: Path) -> tuple[Dict[str, float], Dict[str, float], Dict[str, float], int]:
    by_barcode: Dict[str, float] = {}
    by_codigo: Dict[str, float] = {}
    by_desc: Dict[str, float] = {}
    filas = 0

    iterator = _iter_excel(ruta) if ruta.suffix.lower() in {".xls", ".xlsx", ".xlsm"} else _iter_csv(ruta)
    for row in iterator:
        precio = _precio_venta_fila(row)
        if precio is None:
            continue
        filas += 1
        bc = _barcode(row)
        cod = _codigo(row)
        desc = _descripcion(row)
        if bc:
            by_barcode[bc] = precio
        if cod:
            for variant in _variantes_codigo(cod):
                by_codigo[variant] = precio
        if desc:
            by_desc[desc] = precio

    return by_barcode, by_codigo, by_desc, filas


def _resolver_precio(
    articulo: Articulo,
    by_barcode: Dict[str, float],
    by_codigo: Dict[str, float],
    by_desc: Dict[str, float],
) -> tuple[float, str]:
    cod = (articulo.codigo_interno or "").strip()
    desc = _norm(articulo.descripcion)
    if cod in by_barcode:
        return by_barcode[cod], "barcode"
    for variant in _variantes_codigo(cod):
        if variant in by_codigo:
            return by_codigo[variant], "codigo"
    if desc in by_desc:
        return by_desc[desc], "descripcion"
    return 0.0, "sin_match"


def resetear_y_cargar(db: Session, id_empresa: int, nombre: str, by_bc, by_cod, by_desc) -> None:
    articulos = db.exec(
        select(Articulo).where(Articulo.id_empresa == id_empresa, Articulo.activo == True)
    ).all()

    for art in articulos:
        art.precio_venta = 0.0
        art.venta_negocio = 0.0
        art.auto_actualizar_precio = False
        db.add(art)
    db.commit()

    stats = {"barcode": 0, "codigo": 0, "descripcion": 0, "sin_match": 0}
    for art in articulos:
        precio, origen = _resolver_precio(art, by_bc, by_cod, by_desc)
        art.precio_venta = precio
        art.venta_negocio = precio
        stats[origen] = stats.get(origen, 0) + 1
        db.add(art)

    if db.get(ConfiguracionEmpresa, id_empresa):
        _incrementar_catalogo_version(db, id_empresa)
    db.commit()

    print(f"\n=== {nombre} (id={id_empresa}) ===")
    print(f"  Artículos: {len(articulos)}")
    print(f"  Precio por código de barras: {stats['barcode']}")
    print(f"  Precio por código interno: {stats['codigo']}")
    print(f"  Precio por descripción: {stats['descripcion']}")
    print(f"  Sin PrecioVenta en Excel (quedó $0): {stats['sin_match']}")


def _resolver_archivo(ruta: Optional[Path]) -> Path:
    if ruta and ruta.exists():
        return ruta
    if DEFAULT_XLS.exists():
        return DEFAULT_XLS
    if FALLBACK_CSV.exists():
        print(f"AVISO: no está {DEFAULT_XLS.name}; usando export CSV Elixia (PVMay = PrecioVenta).")
        print("       Subí articulos.xls a 'datos /articulos.xls' para usar la columna PrecioVenta del Excel.")
        return FALLBACK_CSV
    raise FileNotFoundError(
        f"No se encontró articulos.xls. Copiá el archivo a:\n  {DEFAULT_XLS}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archivo", type=Path, default=None)
    args = parser.parse_args()

    archivo = _resolver_archivo(args.archivo)
    print(f"Archivo precios: {archivo}")
    by_bc, by_cod, by_desc, filas = cargar_precios(archivo)
    print(f"  Filas con PrecioVenta: {filas}")
    print(f"  Índice barras: {len(by_bc)} | códigos: {len(by_cod)} | descripciones: {len(by_desc)}")

    with Session(engine) as db:
        resetear_y_cargar(db, 37, "de-campo", by_bc, by_cod, by_desc)
        resetear_y_cargar(db, 38, "La Esquina 2", by_bc, by_cod, by_desc)

    print("\nPrecios reseteados y cargados solo desde PrecioVenta.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
