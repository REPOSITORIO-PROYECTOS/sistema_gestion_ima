#!/usr/bin/env python3
"""
Asigna códigos de barras a productos de Rivadavia (39) que no tienen.

1) Match con El Negro (33) → copia barcodes reales si existen.
2) Si no hay match / sin barras en Negro → usa codigo_interno como barcode.

Uso:
  back/venv/bin/python scripts/cargar_barras_rivadavia.py --dry-run
  back/venv/bin/python scripts/cargar_barras_rivadavia.py
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
from back.modelos import Articulo
from back.schemas.modo_especial_schemas import ProductoModoEspecialUpdate

ID_NEGRO = 33
ID_DESTINO = 39
FUZZY_MIN = 0.78


def _strip_accents(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _norm(texto: str) -> str:
    t = _strip_accents(texto).upper()
    t = re.sub(r"\d+[.,]?\d*\s*(G|GR|GRS|KG|ML|CC|L|LT|LTS|U|UN|UNI|UNID|UNIDAD)S?\b", " ", t)
    t = re.sub(r"\b\d+\s*X\s*\d+(\s*X\s*\d+)?\b", " ", t)
    t = re.sub(r"[^A-Z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _tokens(texto: str) -> set[str]:
    stop = {"DE", "DEL", "LA", "LAS", "LOS", "EL", "Y", "CON", "SIN", "X", "PARA", "GALLETAS", "ALFAJOR"}
    return {tok for tok in _norm(texto).split() if len(tok) > 1 and tok not in stop}


def _similitud(a: str, b: str) -> float:
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    seq = SequenceMatcher(None, na, nb).ratio()
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return seq
    inter = ta & tb
    if not inter:
        return 0.0
    jacc = len(inter) / len(ta | tb)
    return max(seq, 0.45 * seq + 0.55 * jacc)


def main() -> int:
    dry = "--dry-run" in sys.argv
    with Session(engine) as db:
        negros = db.exec(
            select(Articulo)
            .where(Articulo.id_empresa == ID_NEGRO, Articulo.activo == True)
            .options(selectinload(Articulo.codigos))
        ).all()
        catalogo = [
            {
                "desc": a.descripcion or "",
                "norm": _norm(a.descripcion or ""),
                "bars": [c.codigo for c in (a.codigos or []) if c.codigo],
            }
            for a in negros
            if a.descripcion
        ]
        con_barra_negro = sum(1 for c in catalogo if c["bars"])
        print(f"El Negro: {len(catalogo)} arts, {con_barra_negro} con barcode")

        destinos = db.exec(
            select(Articulo)
            .where(Articulo.id_empresa == ID_DESTINO, Articulo.activo == True)
            .options(selectinload(Articulo.codigos))
        ).all()

        stats = {"desde_negro": 0, "desde_codigo": 0, "ya_tenia": 0, "errores": 0}

        for art in destinos:
            actuales = [c.codigo for c in (art.codigos or []) if c.codigo]
            if actuales:
                stats["ya_tenia"] += 1
                continue

            barras: list[str] = []
            origen = "codigo"
            best = None
            best_score = 0.0
            for c in catalogo:
                if not c["bars"]:
                    continue
                score = _similitud(art.descripcion or "", c["desc"])
                if score > best_score:
                    best_score = score
                    best = c

            if best and best_score >= FUZZY_MIN:
                barras = list(best["bars"])
                origen = "negro"
            else:
                # fallback: codigo interno como barra escaneable/buscable
                codigo = (art.codigo_interno or "").strip()
                if codigo:
                    barras = [codigo]

            if not barras:
                continue

            if dry:
                tag = f"[{origen} {best_score:.2f}]" if origen == "negro" else "[codigo]"
                print(f"  {tag} {(art.descripcion or '')[:45]!r} → {barras[:3]}")
                if origen == "negro":
                    stats["desde_negro"] += 1
                else:
                    stats["desde_codigo"] += 1
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
                if origen == "negro":
                    stats["desde_negro"] += 1
                else:
                    stats["desde_codigo"] += 1
            except Exception as exc:
                stats["errores"] += 1
                print(f"ERROR {art.codigo_interno}: {exc}")

        print("\n=== Resultado ===")
        for k, v in stats.items():
            print(f"  {k}: {v}")
        if dry:
            print("[dry-run] sin escribir")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
