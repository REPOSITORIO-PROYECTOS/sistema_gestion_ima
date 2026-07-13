#!/usr/bin/env python3
"""
Seed idempotente: empresas 35-38 → esquema especial con plantilla prod/demo.

Uso (desde raíz del repo, con venv y DB configurada):
  python scripts/seed_perfil_operativo_prod.py
  python scripts/seed_perfil_operativo_prod.py --dry-run
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
    parser = argparse.ArgumentParser(description="Seed perfil operativo empresas 35-38")
    parser.add_argument("--dry-run", action="store_true", help="Solo muestra qué haría")
    args = parser.parse_args()

    if args.dry_run:
        print("Dry-run: se migrarían 35,36 → modo_especial_pos y 37,38 → modo_especial_demo")
        return 0

    with Session(engine) as db:
        resultados = perfil_operativo_manager.seed_empresas_especiales_prod(db)

    for key, value in sorted(resultados.items()):
        print(f"  {key}: {value}")
    print("Seed perfil operativo completado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
