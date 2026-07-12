#!/usr/bin/env python3
"""
Sincroniza precios de venta en empresas demo 37/38 desde articulos.xls y catálogos POS.

Fuentes (en orden de prioridad):
  1. articulos.xls / 02_articulos_artsxls_elixia.csv  (columna PVMay = precio venta)
  2. 03_productos_pos.xlsx                              (columna Precio)
  3. productos_listos_para_importar.csv               (columna Precio)

- Empresa 37: solo precios
- Empresa 38: precios + stock_actual = 1000
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlmodel import Session, select

from back.database import engine
from back.gestion.modo_especial_manager import _incrementar_catalogo_version
from back.modelos import Articulo, ConfiguracionEmpresa

DEFAULT_ARTICULOS = ROOT / "02_articulos_artsxls_elixia.csv"
POS_XLSX = ROOT / "03_productos_pos.xlsx"
PRODUCTOS_LISTOS = ROOT / "productos_listos_para_importar.csv"
ID_DE_CAMPO = 37
ID_LA_ESQUINA_2 = 38
STOCK_ESQUINA_2 = 1000.0
FALLBACK_MARGEN = 1.75

PrecioRegistro = Tuple[float, Optional[float]]


@dataclass
class CatalogoPrecios:
    by_barcode: Dict[str, PrecioRegistro] = field(default_factory=dict)
    by_codigo: Dict[str, PrecioRegistro] = field(default_factory=dict)
    by_desc: Dict[str, PrecioRegistro] = field(default_factory=dict)
    token_index: list[tuple[set[str], PrecioRegistro]] = field(default_factory=list)


def _norm_texto(valor: Optional[str]) -> str:
    texto = (valor or "").upper().strip()
    texto = re.sub(r"\s+", " ", texto)
    texto = re.sub(r"[^A-Z0-9 ]", "", texto)
    return texto


def _tokens(valor: Optional[str]) -> set[str]:
    return {t for t in _norm_texto(valor).split() if len(t) >= 4}


def _parse_float(valor: Optional[str]) -> Optional[float]:
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto or texto.lower() == "nan":
        return None
    try:
        return float(texto.replace(",", "."))
    except ValueError:
        return None


def _precio_venta_desde_fila(row: dict[str, str]) -> float:
    for col in ("PVMay", "PVMin", "PVInt", "PrecioVenta", "precio_venta", "Precio"):
        precio = _parse_float(row.get(col))
        if precio and precio > 0:
            return precio
    return 0.0


def _costo_desde_fila(row: dict[str, str]) -> Optional[float]:
    for col in ("PrecioCosto", "Costo", "precio_costo"):
        costo = _parse_float(row.get(col))
        if costo is not None and costo >= 0:
            return costo
    return None


def _barcode_desde_fila(row: dict[str, str]) -> str:
    for col in ("CodBarra", "CodigoBarras", "codigo_barras", "Código de Barras", "Codigo de Barras"):
        valor = (row.get(col) or "").strip()
        if valor and valor.lower() != "nan":
            return valor
    return ""


def _codigo_desde_fila(row: dict[str, str]) -> str:
    for col in ("IDArt", "CodProveedor", "Codigo", "Código"):
        valor = (row.get(col) or "").strip()
        if valor and valor.lower() != "nan":
            return valor
    return ""


def _desc_desde_fila(row: dict[str, str]) -> str:
    for col in ("Articulo", "Producto", "Descripcion", "Descripción"):
        valor = (row.get(col) or "").strip()
        if valor and valor.lower() != "nan":
            return _norm_texto(valor)
    return ""


def _merge_registro(
    catalogo: CatalogoPrecios,
    *,
    barcode: str,
    codigo: str,
    desc: str,
    registro: PrecioRegistro,
    desc_raw: str,
) -> None:
    precio, _ = registro
    if precio <= 0:
        return
    if barcode and barcode not in catalogo.by_barcode:
        catalogo.by_barcode[barcode] = registro
    if codigo and codigo not in catalogo.by_codigo:
        catalogo.by_codigo[codigo] = registro
        if codigo.isdigit():
            z = codigo.zfill(6)
            if z not in catalogo.by_codigo:
                catalogo.by_codigo[z] = registro
    if desc and desc not in catalogo.by_desc:
        catalogo.by_desc[desc] = registro
        catalogo.token_index.append((_tokens(desc_raw or desc), registro))


def _iter_filas_csv(ruta: Path) -> Iterable[dict[str, str]]:
    contenido = ruta.read_bytes()
    for encoding in ("utf-8-sig", "latin-1", "cp1252"):
        try:
            text = contenido.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = contenido.decode("latin-1", errors="replace")

    delimitador = ";" if text.count(";") > text.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimitador)
    for raw in reader:
        yield {(k or "").strip(): ("" if v is None else str(v).strip()) for k, v in raw.items()}


def _iter_filas_excel(ruta: Path) -> Iterable[dict[str, str]]:
    import pandas as pd

    df = pd.read_excel(ruta, dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    for _, series in df.iterrows():
        yield {
            str(k): ("" if pd.isna(v) else str(v).strip())
            for k, v in series.items()
        }


def _cargar_archivo(ruta: Path, catalogo: CatalogoPrecios) -> int:
    if not ruta.exists():
        return 0
    filas = _iter_filas_excel(ruta) if ruta.suffix.lower() in {".xls", ".xlsx", ".xlsm"} else _iter_filas_csv(ruta)
    count = 0
    for row in filas:
        precio = _precio_venta_desde_fila(row)
        costo = _costo_desde_fila(row)
        if precio <= 0 and costo is None:
            continue
        registro: PrecioRegistro = (precio, costo)
        barcode = _barcode_desde_fila(row)
        codigo = _codigo_desde_fila(row)
        desc_raw = (row.get("Articulo") or row.get("Producto") or row.get("Descripcion") or row.get("Descripción") or "")
        desc = _norm_texto(desc_raw)
        _merge_registro(
            catalogo,
            barcode=barcode,
            codigo=codigo,
            desc=desc,
            registro=registro,
            desc_raw=desc_raw,
        )
        count += 1
    return count


def cargar_catalogo_completo(archivo_principal: Path) -> CatalogoPrecios:
    catalogo = CatalogoPrecios()
    fuentes = [
        ("articulos", archivo_principal),
        ("pos", POS_XLSX),
        ("productos_listos", PRODUCTOS_LISTOS),
    ]
    print("Fuentes de precio de venta:")
    for nombre, ruta in fuentes:
        n = _cargar_archivo(ruta, catalogo)
        print(f"  {nombre}: {n} filas ({ruta.name})")
    print(f"  Índice barras: {len(catalogo.by_barcode)}")
    print(f"  Índice códigos: {len(catalogo.by_codigo)}")
    print(f"  Índice descripciones: {len(catalogo.by_desc)}")
    return catalogo


def _match_por_tokens(desc: str, catalogo: CatalogoPrecios) -> Optional[PrecioRegistro]:
    tokens = _tokens(desc)
    if len(tokens) < 2:
        return None
    mejor: Optional[PrecioRegistro] = None
    mejor_score = 0.0
    for token_set, registro in catalogo.token_index:
        inter = len(tokens & token_set)
        if inter < 2:
            continue
        score = inter / max(len(tokens), 1)
        if score >= 0.6 and score > mejor_score:
            mejor_score = score
            mejor = registro
    return mejor


def _resolver_precio(
    articulo: Articulo,
    catalogo: CatalogoPrecios,
    margen_fallback: float,
) -> Tuple[float, Optional[float], str]:
    codigo = (articulo.codigo_interno or "").strip()
    desc = _norm_texto(articulo.descripcion)

    registro = (
        catalogo.by_barcode.get(codigo)
        or catalogo.by_codigo.get(codigo)
        or catalogo.by_codigo.get(codigo.zfill(6) if codigo.isdigit() else "")
        or catalogo.by_desc.get(desc)
        or _match_por_tokens(articulo.descripcion or "", catalogo)
    )

    if registro:
        precio, costo = registro
        if precio > 0:
            costo_final = costo if costo is not None else articulo.precio_costo
            return precio, costo_final, "precio_venta_catalogo"

    costo_actual = articulo.precio_costo or 0.0
    if costo_actual > 0:
        return round(costo_actual * margen_fallback, 2), costo_actual, "sin_precio_en_catalogo"

    return articulo.precio_venta or 0.0, articulo.precio_costo, "sin_datos"


def _calcular_margen_fallback(articulos: list[Articulo], catalogo: CatalogoPrecios) -> float:
    ratios: list[float] = []
    for articulo in articulos:
        _, _, origen = _resolver_precio(articulo, catalogo, FALLBACK_MARGEN)
        if origen != "precio_venta_catalogo":
            continue
        codigo = (articulo.codigo_interno or "").strip()
        desc = _norm_texto(articulo.descripcion)
        registro = (
            catalogo.by_barcode.get(codigo)
            or catalogo.by_codigo.get(codigo)
            or catalogo.by_desc.get(desc)
        )
        if not registro:
            continue
        precio, costo = registro
        if precio > 0 and costo and costo > 0:
            ratio = precio / costo
            if 1.0 <= ratio <= 5.0:
                ratios.append(ratio)
    return statistics.median(ratios) if ratios else FALLBACK_MARGEN


def actualizar_empresa(
    db: Session,
    id_empresa: int,
    nombre: str,
    *,
    fijar_stock: Optional[float],
    catalogo: CatalogoPrecios,
    margen_fallback: float,
) -> dict[str, int]:
    articulos = db.exec(
        select(Articulo).where(Articulo.id_empresa == id_empresa, Articulo.activo == True)
    ).all()

    stats = {"total": len(articulos), "precio_venta_catalogo": 0, "sin_precio_en_catalogo": 0, "sin_datos": 0}

    for articulo in articulos:
        precio, costo, origen = _resolver_precio(articulo, catalogo, margen_fallback)
        articulo.precio_venta = precio
        articulo.venta_negocio = precio
        articulo.auto_actualizar_precio = False
        if costo is not None:
            articulo.precio_costo = costo
        stats[origen] = stats.get(origen, 0) + 1

        if fijar_stock is not None:
            articulo.stock_actual = fijar_stock

        db.add(articulo)

    if db.get(ConfiguracionEmpresa, id_empresa):
        _incrementar_catalogo_version(db, id_empresa)
    db.commit()

    print(f"\n=== {nombre} (id={id_empresa}) ===")
    print(f"  Artículos: {stats['total']}")
    print(f"  Con precio de venta del catálogo: {stats['precio_venta_catalogo']}")
    print(f"  Sin precio en catálogo (estimado x margen): {stats['sin_precio_en_catalogo']}")
    print(f"  Sin datos: {stats['sin_datos']}")
    if fijar_stock is not None:
        print(f"  Stock fijado a {fijar_stock:g}")
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Sincronizar precios demo 37/38")
    parser.add_argument("--archivo", type=Path, default=DEFAULT_ARTICULOS)
    args = parser.parse_args()

    catalogo = cargar_catalogo_completo(args.archivo)

    with Session(engine) as db:
        ref = db.exec(
            select(Articulo).where(Articulo.id_empresa == ID_DE_CAMPO, Articulo.activo == True)
        ).all()
        margen = _calcular_margen_fallback(ref, catalogo)
        print(f"  Margen estimado (solo faltantes): {margen:.2f}")

        actualizar_empresa(db, ID_DE_CAMPO, "de-campo", fijar_stock=None, catalogo=catalogo, margen_fallback=margen)
        actualizar_empresa(
            db,
            ID_LA_ESQUINA_2,
            "La Esquina 2",
            fijar_stock=STOCK_ESQUINA_2,
            catalogo=catalogo,
            margen_fallback=margen,
        )

    print("\nSincronización finalizada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
