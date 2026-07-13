#!/usr/bin/env python3
"""
Migra flags operativos de aclaraciones_legales → perfil_operativo.

Uso:
  python scripts/migrar_aclaraciones_a_perfil.py
  python scripts/migrar_aclaraciones_a_perfil.py --empresa 35
  python scripts/migrar_aclaraciones_a_perfil.py --dry-run
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sqlmodel import Session

from back.database import engine
from back.gestion import perfil_operativo_manager


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrar aclaraciones operativas a perfil")
    parser.add_argument("--empresa", type=int, help="ID empresa (default: todas con flags operativos)")
    parser.add_argument("--dry-run", action="store_true", help="Solo listar, no escribir")
    args = parser.parse_args()

    if args.dry_run:
        print("Dry-run: se migrarían aclaraciones operativas a perfil_operativo")
        if args.empresa:
            print(f"  Empresa objetivo: {args.empresa}")
        else:
            print("  Todas las empresas con keys operativas en aclaraciones_legales")
        return 0

    with Session(engine) as db:
        if args.empresa:
            result = perfil_operativo_manager.migrar_aclaraciones_operativas_a_perfil(
                db, args.empresa
            )
            print(result)
        else:
            resultados = perfil_operativo_manager.migrar_aclaraciones_todas_empresas(db)
            for row in resultados:
                print(row)
            print(f"Total empresas migradas: {len(resultados)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
