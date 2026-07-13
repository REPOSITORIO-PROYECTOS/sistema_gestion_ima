#!/usr/bin/env python3
"""
Resetea y carga precios SOLO desde TU articulos.xls (columna PrecioVenta).

- Empresas 37 y 38: precio_venta = 0 primero, luego solo PrecioVenta del Excel.
- NO usa Elixia, CSV ni otros catálogos.
- Empresa 38: no modifica stock (sigue en 1000).

Copiá tu archivo de OneDrive/Descargas a: datos /articulos.xls

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
ID_EMPRESAS = (37, 38)

COLUMNAS_PRECIO_VENTA = (
    "PrecioVenta",
    "Precio Venta",
    "PRECIOVENTA",
    "precioventa",
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


def _parece_barcode(valor: str) -> bool:
    cod = _norm_barcode(valor)
    if not cod or not cod.isdigit():
        return False
    return 6 <= len(cod) <= 14


def _barcodes_fila(row: dict[str, str]) -> list[str]:
    """Todas las claves posibles de la fila (Elixia usa columnas distintas)."""
    encontrados: list[str] = []
    vistos: set[str] = set()
    preferidas = (
        "Codigo",
        "Código",
        "CodBarra",
        "CodigoBarras",
        "Código de Barras",
        "Codigo de Barras",
        "codigo_barras",
        "Barra",
        "EAN",
        "GTIN",
    )
    for col in preferidas:
        v = _norm_barcode(row.get(col))
        if v and v not in vistos:
            vistos.add(v)
            encontrados.append(v)
    for valor in row.values():
        v = _norm_barcode(valor)
        if v and _parece_barcode(v) and v not in vistos:
            vistos.add(v)
            encontrados.append(v)
    return encontrados


def _barcode(row: dict[str, str]) -> str:
    barras = _barcodes_fila(row)
    return barras[0] if barras else ""


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


def _excel_engine(ruta: Path) -> str | None:
    """xlrd para .xls legacy (export POS); openpyxl para .xlsx."""
    suf = ruta.suffix.lower()
    if suf == ".xls":
        return "xlrd"
    if suf in {".xlsx", ".xlsm"}:
        return "openpyxl"
    return None


def _read_excel(ruta: Path, **kwargs):
    import pandas as pd

    if "engine" not in kwargs:
        engine = _excel_engine(ruta)
        if engine:
            kwargs["engine"] = engine
    return pd.read_excel(ruta, **kwargs)


def _open_excel(ruta: Path):
    import pandas as pd

    engine = _excel_engine(ruta)
    if engine:
        return pd.ExcelFile(ruta, engine=engine)
    return pd.ExcelFile(ruta)


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

    libro = _open_excel(ruta)
    print(f"  Hojas Excel: {libro.sheet_names}")
    engine = _excel_engine(ruta)
    for hoja in libro.sheet_names:
        kwargs: dict = {"sheet_name": hoja, "dtype": str}
        if engine:
            kwargs["engine"] = engine
        df = _read_excel(ruta, **kwargs)
        df.columns = [str(c).strip() for c in df.columns]
        print(f"  Hoja '{hoja}' ({len(df)} filas) columnas: {list(df.columns)}")
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
        cod = _codigo(row)
        desc = _descripcion(row)
        for bc in _barcodes_fila(row):
            by_barcode[bc] = precio
            for variant in _variantes_codigo(bc):
                by_barcode[variant] = precio
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


def _validar_excel_usuario(ruta: Path) -> None:
    """Rechaza el xls parcial generado en servidor; exige columna PrecioVenta."""
    libro = _open_excel(ruta)
    engine = _excel_engine(ruta)
    kwargs: dict = {"sheet_name": libro.sheet_names[0], "nrows": 5, "dtype": str}
    if engine:
        kwargs["engine"] = engine
    df = _read_excel(ruta, **kwargs)
    columnas = {str(c).strip() for c in df.columns}
    if "PrecioVenta" not in columnas:
        raise ValueError(
            f"El Excel no tiene columna PrecioVenta. Columnas: {sorted(columnas)}"
        )
    if columnas == {"IDArt", "Articulo", "CodBarra", "PrecioCosto", "PrecioVenta"}:
        total_kwargs: dict = {"sheet_name": libro.sheet_names[0], "dtype": str}
        if engine:
            total_kwargs["engine"] = engine
        total = len(_read_excel(ruta, **total_kwargs))
        if total <= 3100:
            raise FileNotFoundError(
                f"El archivo {ruta} parece un export parcial del servidor ({total} filas).\n"
                f"Subí tu articulos.xls real a:\n  {DEFAULT_XLS}"
            )


def _resolver_archivo(ruta: Optional[Path]) -> Path:
    if ruta and ruta.exists():
        archivo = ruta
    elif DEFAULT_XLS.exists():
        archivo = DEFAULT_XLS
    else:
        raise FileNotFoundError(
            "No está tu articulos.xls en el servidor.\n"
            "Desde tu PC copiá el archivo a:\n"
            f"  {DEFAULT_XLS}\n"
            "En Cursor: arrastralo a la carpeta 'datos ' del proyecto."
        )
    if archivo.suffix.lower() not in {".xls", ".xlsx", ".xlsm"}:
        raise ValueError(f"Se espera un Excel (.xls/.xlsx), no: {archivo}")
    _validar_excel_usuario(archivo)
    return archivo


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
