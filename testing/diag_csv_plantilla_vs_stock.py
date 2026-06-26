#!/usr/bin/env python3
"""
Diagnóstico CSV plantilla (modo especial) ↔ stock en DB.

Compara un archivo de importación (ej. productos_listos_para_importar.csv) contra
el catálogo/stock de una empresa y explica qué pasa y qué hay que hacer.

Uso:
  python testing/diag_csv_plantilla_vs_stock.py
  python testing/diag_csv_plantilla_vs_stock.py --csv productos_listos_para_importar.csv --id-empresa 35
  python testing/diag_csv_plantilla_vs_stock.py --buscar esquina
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sqlmodel import Session, select

from back.database import engine
from back.gestion import modo_especial_manager
from back.modelos import Articulo, ConfiguracionEmpresa, Empresa
from back.schemas.modo_especial_schemas import ProductoModoEspecialCreate

EPS_PRECIO = 0.02
EPS_STOCK = 0.02
DEFAULT_CSV = _ROOT / "productos_listos_para_importar.csv"
_RE_NOTACION_CIENTIFICA = re.compile(r"^\d+\.?\d*[eE][+-]?\d+$")


@dataclass
class FilaCsvValidada:
    codigo: str
    descripcion: str
    precio_venta: float
    precio_costo: Optional[float]
    stock_csv: Optional[float]
    stock_efectivo: float
    categorias: List[str]
    barcodes: Optional[List[str]]
    unidad: str
    advertencias: List[str] = field(default_factory=list)


@dataclass
class ResultadoDiagnostico:
    id_empresa: int
    nombre_empresa: str
    modo_especial: bool
    ruta_csv: Path
    total_filas_csv: int
    filas_omitidas: int
    filas_con_error_parse: int
    productos_validos: int
    solo_csv: List[str]
    solo_db: List[str]
    diff_stock: List[Dict[str, Any]]
    diff_precio: List[Dict[str, Any]]
    diff_descripcion: List[Dict[str, Any]]
    sim_creados: int
    sim_actualizados: int
    sim_errores: int
    errores_parse: List[str]
    advertencias_globales: List[str]
    stock_negativo_csv: int
    barcodes_duplicados_csv: int
    codigos_notacion_cientifica: List[str]


def _es_notacion_cientifica(codigo: str) -> bool:
    return bool(_RE_NOTACION_CIENTIFICA.match(codigo.strip()))
def _norm_codigo(codigo: str) -> str:
    return str(codigo or "").strip()


def _norm_txt(valor: Any) -> str:
    return str(valor or "").strip().lower()


def _resolver_id_empresa(db: Session, id_empresa: Optional[int], buscar: Optional[str]) -> Tuple[int, str, bool]:
    if id_empresa is not None:
        empresa = db.get(Empresa, id_empresa)
        if not empresa:
            raise SystemExit(f"No existe empresa con id={id_empresa}")
        config = db.get(ConfiguracionEmpresa, id_empresa)
        modo = bool(config and config.modo_especial_habilitado)
        nombre = empresa.nombre_fantasia or empresa.nombre_legal or f"Empresa {id_empresa}"
        return id_empresa, nombre, modo

    if buscar:
        termino = buscar.lower()
        empresas = db.exec(select(Empresa)).all()
        candidatos: List[Tuple[int, str, bool]] = []
        for emp in empresas:
            texto = f"{emp.nombre_fantasia or ''} {emp.nombre_legal or ''}".lower()
            if termino in texto:
                config = db.get(ConfiguracionEmpresa, emp.id)
                modo = bool(config and config.modo_especial_habilitado)
                nombre = emp.nombre_fantasia or emp.nombre_legal or f"Empresa {emp.id}"
                candidatos.append((emp.id, nombre, modo))
        if not candidatos:
            raise SystemExit(f"No se encontró empresa que contenga '{buscar}'")
        if len(candidatos) > 1:
            print("Varias empresas coinciden:")
            for cid, cnom, cmodo in candidatos:
                print(f"  id={cid}  {cnom}  modo_especial={cmodo}")
            raise SystemExit("Especifique --id-empresa")
        return candidatos[0]

    raise SystemExit("Indique --id-empresa o --buscar <texto>")


def _leer_y_validar_csv(contenido: str) -> Tuple[List[FilaCsvValidada], List[str], int, int, List[str]]:
    filas = modo_especial_manager._leer_filas_csv(contenido)
    validadas: List[FilaCsvValidada] = []
    errores_parse: List[str] = []
    omitidas = 0
    stock_negativo = 0
    advertencias_globales: List[str] = []
    barcode_por_codigo: Dict[str, str] = {}
    barcodes_duplicados = 0
    codigos_cientificos: List[str] = []

    for fila in filas:
        codigo = _norm_codigo(fila.get("codigo"))
        nombre = (fila.get("producto") or "").strip()
        if not codigo or not nombre:
            omitidas += 1
            if len(errores_parse) < 5:
                errores_parse.append(f"Fila omitida: falta código o nombre ({fila})")
            continue

        if _es_notacion_cientifica(codigo):
            codigos_cientificos.append(codigo)

        advertencias: List[str] = []
        try:
            precio = modo_especial_manager._parse_numero_csv(fila.get("precio"), 0.0) or 0.0
            costo = modo_especial_manager._parse_numero_csv(fila.get("costo"))
            stock_raw = modo_especial_manager._parse_numero_csv(fila.get("stock"))
            stock_efectivo = stock_raw if stock_raw is not None else 0.0
            if stock_raw is not None and stock_raw < 0:
                stock_negativo += 1
                advertencias.append(f"stock negativo en CSV ({stock_raw}) → se importaría como 0")
                stock_efectivo = 0.0

            unidad = modo_especial_manager._normalizar_unidad(fila.get("unidad") or "unidad")
            categorias = modo_especial_manager._parse_categorias_csv(fila.get("categorias") or "")
            barcodes = modo_especial_manager._parse_barcodes_csv(fila.get("codigo_barras") or "")

            ProductoModoEspecialCreate(
                codigo_interno=codigo,
                descripcion=nombre,
                precio_venta=precio,
                precio_costo=costo,
                categorias=categorias,
                stock=stock_efectivo,
                stock_minimo=modo_especial_manager._parse_numero_csv(fila.get("stock_minimo")),
                barcodes=barcodes,
                unidad=unidad,
                cantidad_envase=modo_especial_manager._parse_numero_csv(fila.get("cantidad_envase")),
                ubicacion=(fila.get("ubicacion") or "").strip() or None,
            )

            if barcodes:
                for bc in barcodes:
                    prev = barcode_por_codigo.get(bc)
                    if prev and prev != codigo:
                        barcodes_duplicados += 1
                    barcode_por_codigo[bc] = codigo

            validadas.append(
                FilaCsvValidada(
                    codigo=codigo,
                    descripcion=nombre,
                    precio_venta=precio,
                    precio_costo=costo,
                    stock_csv=stock_raw,
                    stock_efectivo=stock_efectivo,
                    categorias=categorias,
                    barcodes=barcodes,
                    unidad=unidad,
                    advertencias=advertencias,
                )
            )
        except Exception as exc:
            errores_parse.append(f"{codigo}: {exc}")

    if stock_negativo:
        advertencias_globales.append(
            f"{stock_negativo} filas tienen stock negativo en el CSV; el importador los guarda como 0."
        )
    if barcodes_duplicados:
        advertencias_globales.append(
            f"{barcodes_duplicados} códigos de barras repetidos entre productos distintos; "
            "el importador omite el barcode en conflicto pero carga el producto."
        )
    if codigos_cientificos:
        advertencias_globales.append(
            f"{len(codigos_cientificos)} códigos en notación científica (error típico de Excel): "
            f"{', '.join(codigos_cientificos[:5])}"
        )

    return validadas, errores_parse, omitidas, stock_negativo, advertencias_globales


def _cargar_db(db: Session, id_empresa: int) -> Dict[str, Articulo]:
    articulos = db.exec(
        select(Articulo).where(Articulo.id_empresa == id_empresa)
    ).all()
    return {_norm_codigo(a.codigo_interno): a for a in articulos if a.codigo_interno}


def _simular_importacion(
    csv_map: Dict[str, FilaCsvValidada],
    db_map: Dict[str, Articulo],
) -> Tuple[int, int, int]:
    creados = sum(1 for c in csv_map if c not in db_map)
    actualizados = sum(1 for c in csv_map if c in db_map)
    return creados, actualizados, 0


def diagnosticar(
    ruta_csv: Path,
    id_empresa: Optional[int] = None,
    buscar: Optional[str] = None,
) -> ResultadoDiagnostico:
    if not ruta_csv.is_file():
        raise SystemExit(f"No existe el CSV: {ruta_csv}")

    contenido = ruta_csv.read_text(encoding="utf-8-sig")
    validadas, errores_parse, omitidas, stock_negativo, advertencias = _leer_y_validar_csv(contenido)

    with Session(engine) as db:
        id_emp, nombre, modo = _resolver_id_empresa(db, id_empresa, buscar)
        if not modo:
            advertencias.append(
                "Modo especial NO está habilitado para esta empresa. "
                "El usuario no verá Stock → importación CSV hasta activarlo en configuración (super-admin)."
            )
        db_map = _cargar_db(db, id_emp)

    csv_map = {v.codigo: v for v in validadas}
    solo_csv = sorted(set(csv_map) - set(db_map))
    solo_db = sorted(set(db_map) - set(csv_map))
    ambos = set(csv_map) & set(db_map)

    diff_stock: List[Dict[str, Any]] = []
    diff_precio: List[Dict[str, Any]] = []
    diff_descripcion: List[Dict[str, Any]] = []

    for codigo in sorted(ambos):
        fila = csv_map[codigo]
        art = db_map[codigo]
        stock_db = float(art.stock_actual or 0)
        if abs(fila.stock_efectivo - stock_db) > EPS_STOCK:
            diff_stock.append(
                {
                    "codigo": codigo,
                    "descripcion": fila.descripcion,
                    "csv": fila.stock_efectivo,
                    "db": stock_db,
                    "csv_raw": fila.stock_csv,
                }
            )
        precio_db = float(art.precio_venta or 0)
        if abs(fila.precio_venta - precio_db) > EPS_PRECIO:
            diff_precio.append(
                {
                    "codigo": codigo,
                    "descripcion": fila.descripcion,
                    "csv": fila.precio_venta,
                    "db": precio_db,
                }
            )
        if _norm_txt(fila.descripcion) != _norm_txt(art.descripcion):
            diff_descripcion.append(
                {
                    "codigo": codigo,
                    "csv": fila.descripcion,
                    "db": art.descripcion or "",
                }
            )

    sim_creados, sim_actualizados, sim_errores = _simular_importacion(csv_map, db_map)
    codigos_cientificos = [v.codigo for v in validadas if _es_notacion_cientifica(v.codigo)]

    return ResultadoDiagnostico(
        id_empresa=id_emp,
        nombre_empresa=nombre,
        modo_especial=modo,
        ruta_csv=ruta_csv,
        total_filas_csv=len(modo_especial_manager._leer_filas_csv(contenido)),
        filas_omitidas=omitidas,
        filas_con_error_parse=len(errores_parse),
        productos_validos=len(validadas),
        solo_csv=solo_csv,
        solo_db=solo_db,
        diff_stock=diff_stock,
        diff_precio=diff_precio,
        diff_descripcion=diff_descripcion,
        sim_creados=sim_creados,
        sim_actualizados=sim_actualizados,
        sim_errores=sim_errores + len(errores_parse),
        errores_parse=errores_parse,
        advertencias_globales=advertencias,
        stock_negativo_csv=stock_negativo,
        barcodes_duplicados_csv=0,
        codigos_notacion_cientifica=codigos_cientificos,
    )


def _imprimir_bloque(titulo: str, lineas: List[str]) -> None:
    print(f"\n{'─' * 80}")
    print(titulo)
    print(f"{'─' * 80}")
    if lineas:
        for linea in lineas:
            print(linea)
    else:
        print("  (nada)")


def _recomendaciones(res: ResultadoDiagnostico) -> List[str]:
    recs: List[str] = []

    if not res.modo_especial:
        recs.append("Activar modo especial en Configuración → Empresa (solo super-admin).")

    if res.filas_con_error_parse:
        recs.append(
            f"Corregir {res.filas_con_error_parse} filas con error de parseo antes de importar "
            "(unidad inválida, número mal formateado, categoría vacía, etc.)."
        )

    if res.solo_csv:
        recs.append(
            f"Importar el CSV: faltan {len(res.solo_csv)} productos en la DB. "
            "Stock → Modo especial → Importar CSV (puede tardar ~90 s con 5000+ filas)."
        )
    elif res.productos_validos and not res.solo_csv and not res.diff_stock and not res.diff_precio:
        recs.append("El CSV ya está alineado con la DB. No hace falta reimportar salvo cambios puntuales.")

    if res.sim_actualizados and (res.diff_stock or res.diff_precio):
        recs.append(
            "Reimportar el CSV actualizaría precios/stock de productos existentes "
            f"({len(res.diff_stock)} stocks distintos, {len(res.diff_precio)} precios distintos)."
        )

    if res.solo_db:
        recs.append(
            f"Hay {len(res.solo_db)} productos en la DB que NO están en el CSV. "
            "Revisar si son extras del sistema o si faltan en la planilla origen."
        )

    if res.codigos_notacion_cientifica:
        recs.append(
            "Corregir códigos en notación científica en Excel (formato texto) antes de la próxima exportación."
        )

    if res.stock_negativo_csv:
        recs.append(
            f"Revisar {res.stock_negativo_csv} filas con stock negativo en el CSV; "
            "al importar quedan en 0, no en el valor negativo."
        )

    if not recs:
        recs.append("Sin acciones urgentes detectadas.")

    return recs


def imprimir_reporte(res: ResultadoDiagnostico) -> None:
    print(f"\n{'=' * 80}")
    print("DIAGNÓSTICO: CSV PLANTILLA ↔ STOCK EN DB")
    print(f"{'=' * 80}")
    print(f"Empresa:        {res.nombre_empresa} (id={res.id_empresa})")
    print(f"Modo especial:  {'SÍ' if res.modo_especial else 'NO'}")
    print(f"CSV:            {res.ruta_csv}")
    print(f"Filas en CSV:   {res.total_filas_csv}")
    print(f"Válidas:        {res.productos_validos}")
    print(f"Omitidas:       {res.filas_omitidas}")
    print(f"Errores parse:  {res.filas_con_error_parse}")

    if res.advertencias_globales:
        _imprimir_bloque("ADVERTENCIAS DEL CSV", [f"  • {a}" for a in res.advertencias_globales])

    if res.errores_parse:
        muestra = [f"  • {e}" for e in res.errores_parse[:15]]
        if len(res.errores_parse) > 15:
            muestra.append(f"  ... y {len(res.errores_parse) - 15} más")
        _imprimir_bloque("ERRORES DE PARSEO (bloquean filas)", muestra)

    print(f"\n{'─' * 80}")
    print("SIMULACIÓN DE IMPORTACIÓN (sin escribir en DB)")
    print(f"{'─' * 80}")
    print(f"  Crearía:      {res.sim_creados}")
    print(f"  Actualizaría: {res.sim_actualizados}")
    print(f"  Errores:      {res.sim_errores}")

    _imprimir_bloque(
        f"SOLO EN CSV — faltan en DB ({len(res.solo_csv)})",
        [f"  {c}" for c in res.solo_csv[:20]]
        + ([f"  ... y {len(res.solo_csv) - 20} más"] if len(res.solo_csv) > 20 else []),
    )

    _imprimir_bloque(
        f"SOLO EN DB — no están en CSV ({len(res.solo_db)})",
        [f"  {c}" for c in res.solo_db[:20]]
        + ([f"  ... y {len(res.solo_db) - 20} más"] if len(res.solo_db) > 20 else []),
    )

    diff_stock_lines = [
        f"  {d['codigo']}: CSV={d['csv']} (raw={d['csv_raw']})  DB={d['db']}  — {d['descripcion'][:50]}"
        for d in res.diff_stock[:20]
    ]
    if len(res.diff_stock) > 20:
        diff_stock_lines.append(f"  ... y {len(res.diff_stock) - 20} más")
    _imprimir_bloque(f"DIFERENCIAS DE STOCK ({len(res.diff_stock)})", diff_stock_lines)

    diff_precio_lines = [
        f"  {d['codigo']}: CSV=${d['csv']:.2f}  DB=${d['db']:.2f}  — {d['descripcion'][:50]}"
        for d in res.diff_precio[:20]
    ]
    if len(res.diff_precio) > 20:
        diff_precio_lines.append(f"  ... y {len(res.diff_precio) - 20} más")
    _imprimir_bloque(f"DIFERENCIAS DE PRECIO ({len(res.diff_precio)})", diff_precio_lines)

    if res.diff_descripcion:
        diff_desc_lines = [
            f"  {d['codigo']}:\n      CSV: {d['csv'][:60]}\n      DB:  {d['db'][:60]}"
            for d in res.diff_descripcion[:10]
        ]
        if len(res.diff_descripcion) > 10:
            diff_desc_lines.append(f"  ... y {len(res.diff_descripcion) - 10} más")
        _imprimir_bloque(f"DIFERENCIAS DE DESCRIPCIÓN ({len(res.diff_descripcion)})", diff_desc_lines)

    print(f"\n{'=' * 80}")
    print("RESUMEN")
    print(f"{'=' * 80}")
    en_ambos = res.productos_validos - len(res.solo_csv)
    pct = (en_ambos / res.productos_validos * 100) if res.productos_validos else 0
    print(f"Productos válidos en CSV:     {res.productos_validos}")
    print(f"Ya en DB (mismo código):      {en_ambos}")
    print(f"Faltan importar:              {len(res.solo_csv)}")
    print(f"Extras en DB:                 {len(res.solo_db)}")
    print(f"Stock distinto CSV vs DB:     {len(res.diff_stock)}")
    print(f"Precio distinto CSV vs DB:    {len(res.diff_precio)}")
    print(f"Alineación código CSV↔DB:     {pct:.1f}%")

    print(f"\n{'=' * 80}")
    print("QUÉ HAY QUE HACER")
    print(f"{'=' * 80}")
    for i, rec in enumerate(_recomendaciones(res), 1):
        print(f"  {i}. {rec}")
    print(f"{'=' * 80}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compara CSV plantilla de importación vs stock en DB")
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV,
        help=f"Ruta al CSV (default: {DEFAULT_CSV.name})",
    )
    parser.add_argument("--id-empresa", type=int, default=None, help="ID de empresa (ej. 35 = La Esquina)")
    parser.add_argument("--buscar", type=str, default=None, help="Buscar empresa por nombre (ej. esquina)")
    args = parser.parse_args()

    id_empresa = args.id_empresa
    buscar = args.buscar
    if id_empresa is None and buscar is None:
        buscar = "esquina"

    resultado = diagnosticar(args.csv, id_empresa=id_empresa, buscar=buscar)
    imprimir_reporte(resultado)


if __name__ == "__main__":
    main()
