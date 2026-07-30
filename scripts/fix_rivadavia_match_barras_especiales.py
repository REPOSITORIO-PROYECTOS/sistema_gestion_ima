#!/usr/bin/env python3
"""
Corrige Rivadavia (39):
1) Borra los productos en blanco (costo=0, venta=0) mal importados de El Negro.
2) Rematchea productos con precio (El Refugio) vs El Negro CON barcode, por coincidencia
   de nombre (normalización + tokens + marcas), y asigna EAN reales.
3) Crea PANIFICACION y CARAMELO: precio_manual=True (stock ilimitado al vender), precio=1.

Uso:
  back/venv/bin/python scripts/fix_rivadavia_match_barras_especiales.py --dry-run
  back/venv/bin/python scripts/fix_rivadavia_match_barras_especiales.py
"""
from __future__ import annotations

import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from back.database import engine
from back.gestion import modo_especial_manager
from back.modelos import Articulo, ArticuloCodigo
from back.schemas.modo_especial_schemas import (
    ProductoModoEspecialCreate,
    ProductoModoEspecialUpdate,
    UnidadMedidaEnum,
)

ID_NEGRO = 33
ID_DESTINO = 39
FUZZY_MIN = 0.78
PRECIO_ESPECIAL = 1.0

# Marcas / abreviaturas frecuentes en listas vs catálogo El Negro
SINONIMOS = {
    "BOB": "BONOBON",
    "BONOBON": "BONOBON",
    "BON": "BONOBON",
    "ALF": "ALFAJOR",
    "ALFA": "ALFAJOR",
    "BCO": "BLANCO",
    "BLCO": "BLANCO",
    "LEC": "LECHE",
    "LECH": "LECHE",
    "DDL": "DULCEDELECHE",
    "VAI": "VAINILLA",
    "CHO": "CHOCOLATE",
    "CHOC": "CHOCOLATE",
    "FRU": "FRUTILLA",
    "FRUT": "FRUTILLA",
    "FRAMB": "FRAMBUESA",
    "RELL": "RELLENO",
    "GRS": "",
    "GR": "",
    "UNI": "",
    "UNID": "",
    "UNIDAD": "",
    "TACC": "SINTACC",
    "LYPTUS": "EUCA",
}


def _strip_accents(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _norm(texto: str) -> str:
    t = _strip_accents(texto).upper()
    t = t.replace("Ñ", "N")
    t = re.sub(r"\d+[.,]?\d*\s*(G|GR|GRS|KG|ML|CC|L|LT|LTS|U|UN|UNI|UNID|UNIDAD|%)S?\b", " ", t)
    t = re.sub(r"\b\d+\s*X\s*\d+(\s*X\s*\d+)?\b", " ", t)
    t = re.sub(r"[^A-Z0-9]+", " ", t)
    parts = []
    for tok in t.split():
        tok = SINONIMOS.get(tok, tok)
        if tok:
            parts.append(tok)
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def _tokens(texto: str) -> set[str]:
    stop = {"DE", "DEL", "LA", "LAS", "LOS", "EL", "Y", "CON", "SIN", "X", "PARA", "GALLETAS", "TODOS", "LOS", "SABORES"}
    return {tok for tok in _norm(texto).split() if len(tok) > 1 and tok not in stop}


def _similitud(a: str, b: str) -> float:
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    inter = ta & tb
    if not inter:
        return 0.0
    # evitar cruces de marca (CLUB SOCIAL vs CHOCOLINAS)
    fuertes = {t for t in inter if len(t) >= 5}
    if not fuertes and len(inter) < 2:
        return 0.0
    # contención con token fuerte compartido
    if (na in nb or nb in na) and fuertes:
        return max(0.86, SequenceMatcher(None, na, nb).ratio())
    seq = SequenceMatcher(None, na, nb).ratio()
    jacc = len(inter) / len(ta | tb)
    recall = len(inter) / len(ta)
    score = max(seq, 0.30 * seq + 0.35 * jacc + 0.35 * recall)
    if not fuertes and score < 0.9:
        return score * 0.85
    return score


def _borrar_blancos(db: Session, dry: bool) -> int:
    arts = db.exec(
        select(Articulo)
        .where(Articulo.id_empresa == ID_DESTINO, Articulo.activo == True)
        .options(selectinload(Articulo.codigos))
    ).all()
    blancos = [
        a
        for a in arts
        if float(a.precio_venta or 0) == 0.0 and float(a.precio_costo or 0) == 0.0
        and (a.descripcion or "").strip().upper() not in {"PANIFICACION", "CARAMELO", "PANADERIA", "GOLOSINAS"}
    ]
    print(f"Blancos a borrar: {len(blancos)}")
    if dry:
        return len(blancos)
    for a in blancos:
        for c in list(a.codigos or []):
            db.delete(c)
        db.delete(a)
    db.commit()
    modo_especial_manager._incrementar_catalogo_version(db, ID_DESTINO)
    db.commit()
    return len(blancos)


def _rematch_barras(db: Session, dry: bool) -> dict[str, int]:
    negros = db.exec(
        select(Articulo)
        .where(Articulo.id_empresa == ID_NEGRO, Articulo.activo == True)
        .options(selectinload(Articulo.codigos))
    ).all()
    catalogo = []
    for a in negros:
        bars = [c.codigo.strip() for c in (a.codigos or []) if c.codigo and c.codigo.strip()]
        if not bars or not a.descripcion:
            continue
        catalogo.append({"desc": a.descripcion, "bars": bars, "norm": _norm(a.descripcion)})

    destinos = db.exec(
        select(Articulo)
        .where(Articulo.id_empresa == ID_DESTINO, Articulo.activo == True)
        .options(selectinload(Articulo.codigos))
    ).all()
    # solo los de Refugio (con precio) o los que siguen con REF-
    candidatos = [
        a
        for a in destinos
        if float(a.precio_venta or 0) > 0
        and (a.descripcion or "").strip().upper() not in {"PANIFICACION", "CARAMELO"}
    ]

    stats = {"match": 0, "sin_match": 0, "actualizados": 0, "errores": 0}
    print(f"Catalogo Negro CON barra: {len(catalogo)} | Rivadavia a matchear: {len(candidatos)}")

    for art in candidatos:
        best = None
        best_score = 0.0
        for c in catalogo:
            score = _similitud(art.descripcion or "", c["desc"])
            if score > best_score:
                best_score = score
                best = c

        if not best or best_score < FUZZY_MIN:
            stats["sin_match"] += 1
            continue

        stats["match"] += 1
        # Preferir EAN real; mantener codigo interno como barra secundaria si es distinto
        barras = list(best["bars"])
        codigo = (art.codigo_interno or "").strip()
        if codigo and codigo not in barras and not codigo.isdigit():
            # no mezclar REF con EAN como barcode primario — solo EANs del negro
            pass

        print(f"  [{best_score:.2f}] {(art.descripcion or '')[:40]!r} ← {best['desc'][:40]!r} → {barras[0]}")
        if dry:
            continue
        try:
            modo_especial_manager.actualizar_producto(
                db,
                ID_DESTINO,
                art.codigo_interno,
                ProductoModoEspecialUpdate(barcodes=barras),
                omitir_conflictos_barcode=True,
                commit=True,
            )
            stats["actualizados"] += 1
        except Exception as exc:
            stats["errores"] += 1
            print(f"  ERROR {art.codigo_interno}: {exc}")

    return stats


def _asegurar_especial(
    db: Session,
    *,
    codigo: str,
    descripcion: str,
    dry: bool,
) -> None:
    existente = db.exec(
        select(Articulo).where(
            Articulo.id_empresa == ID_DESTINO,
            Articulo.codigo_interno == codigo,
        )
    ).first()
    if existente:
        print(f"  Especial ya existe: {codigo} id={existente.id}")
        if not dry:
            existente.descripcion = descripcion
            existente.precio_venta = PRECIO_ESPECIAL
            existente.venta_negocio = PRECIO_ESPECIAL
            existente.precio_costo = 0.0
            existente.precio_manual = True
            existente.auto_actualizar_precio = False
            existente.stock_actual = 999999.0
            existente.activo = True
            db.add(existente)
            # barcode = codigo
            modo_especial_manager.actualizar_producto(
                db,
                ID_DESTINO,
                codigo,
                ProductoModoEspecialUpdate(barcodes=[codigo]),
                omitir_conflictos_barcode=True,
                commit=True,
            )
            db.commit()
        return

    print(f"  Crear especial: {descripcion} ({codigo}) precio={PRECIO_ESPECIAL} manual/ilimitado")
    if dry:
        return
    modo_especial_manager.crear_producto(
        db,
        ID_DESTINO,
        ProductoModoEspecialCreate(
            codigo_interno=codigo,
            descripcion=descripcion,
            precio_venta=PRECIO_ESPECIAL,
            precio_costo=0.0,
            categorias=["Especiales"],
            stock=999999.0,
            barcodes=[codigo],
            unidad=UnidadMedidaEnum.unidad,
            tasa_iva=0.21,
        ),
        omitir_conflictos_barcode=True,
        commit=True,
    )
    art = modo_especial_manager._obtener_articulo_por_codigo(db, ID_DESTINO, codigo)
    if art:
        art.precio_manual = True
        art.auto_actualizar_precio = False
        art.stock_actual = 999999.0
        db.add(art)
        db.commit()
        modo_especial_manager._incrementar_catalogo_version(db, ID_DESTINO)
        db.commit()


def main() -> int:
    dry = "--dry-run" in sys.argv
    print(f"=== Fix Rivadavia {'DRY-RUN' if dry else 'APPLY'} ===")
    with Session(engine) as db:
        n = _borrar_blancos(db, dry)
        print(f"Blancos: {n}")
        stats = _rematch_barras(db, dry)
        print(f"Match barras: {stats}")
        print("Especiales:")
        _asegurar_especial(db, codigo="PANIFICACION", descripcion="PANIFICACION", dry=dry)
        _asegurar_especial(db, codigo="CARAMELO", descripcion="CARAMELO", dry=dry)

        if not dry:
            total = db.exec(
                select(Articulo).where(Articulo.id_empresa == ID_DESTINO, Articulo.activo == True)
            ).all()
            con_ean = 0
            for a in total:
                db.refresh(a)
            arts = db.exec(
                select(Articulo)
                .where(Articulo.id_empresa == ID_DESTINO, Articulo.activo == True)
                .options(selectinload(Articulo.codigos))
            ).all()
            for a in arts:
                if any(c.codigo and c.codigo.isdigit() and len(c.codigo) >= 8 for c in (a.codigos or [])):
                    con_ean += 1
            print(f"\nTotal activos={len(arts)} con_EAN_real={con_ean}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
