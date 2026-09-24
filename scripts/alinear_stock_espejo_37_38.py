#!/usr/bin/env python3
"""
Alinea stock de La Esquina 2 (38) con de-campo (37) por codigo_interno.

Uso one-shot tras activar el espejo en runtime (ingreso/venta ya espejan solos).

  python scripts/alinear_stock_espejo_37_38.py --dry-run
  python scripts/alinear_stock_espejo_37_38.py --apply
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
from back.modelos import Articulo

ID_FUENTE = 37
ID_DESTINO = 38


def main() -> int:
    parser = argparse.ArgumentParser(description="Alinear stock 37→38 por codigo_interno")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.dry_run == args.apply:
        print("Indicá --dry-run o --apply")
        return 2

    with Session(engine) as db:
        fuente = {
            (a.codigo_interno or "").strip(): a
            for a in db.exec(select(Articulo).where(Articulo.id_empresa == ID_FUENTE)).all()
            if (a.codigo_interno or "").strip()
        }
        destino = {
            (a.codigo_interno or "").strip(): a
            for a in db.exec(select(Articulo).where(Articulo.id_empresa == ID_DESTINO)).all()
            if (a.codigo_interno or "").strip()
        }
        comunes = set(fuente) & set(destino)
        cambios = 0
        for codigo in sorted(comunes):
            s_f = float(fuente[codigo].stock_actual or 0.0)
            s_d = float(destino[codigo].stock_actual or 0.0)
            if abs(s_f - s_d) < 1e-9:
                continue
            cambios += 1
            print(f"  {codigo}: 38 {s_d} -> {s_f}")
            if args.apply:
                destino[codigo].stock_actual = s_f
                db.add(destino[codigo])
        solo_f = sorted(set(fuente) - set(destino))
        solo_d = sorted(set(destino) - set(fuente))
        print(f"comunes={len(comunes)} a_alinear={cambios} solo_37={len(solo_f)} solo_38={len(solo_d)}")
        if args.apply and cambios:
            db.commit()
            print("OK commit")
        elif args.dry_run:
            print("dry-run (sin escribir)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
