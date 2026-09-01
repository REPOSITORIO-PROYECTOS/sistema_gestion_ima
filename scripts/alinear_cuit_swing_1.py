#!/usr/bin/env python3
"""Alinea CUIT de Swing (empresa 1) en empresas + configuracion_empresa.

No copia certificados de bóveda: 20-... es persona física y 30-... es
persona jurídica; el cert hay que subirlo de nuevo para el CUIT nuevo.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlmodel import Session

from back.database import engine
from back.modelos import ConfiguracionEmpresa, Empresa

ID_EMPRESA = 1
CUIT_ESPERADO_VIEJO = "20364237740"
CUIT_NUEVO = "30718863380"


def _solo_digitos(valor: object) -> str:
    return "".join(ch for ch in str(valor or "") if ch.isdigit())


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    with Session(engine) as db:
        empresa = db.get(Empresa, ID_EMPRESA)
        config = db.get(ConfiguracionEmpresa, ID_EMPRESA)
        if not empresa or not config:
            print(f"Empresa/config {ID_EMPRESA} no encontrada")
            return 1

        emp_cuit = _solo_digitos(empresa.cuit)
        cfg_cuit = _solo_digitos(config.cuit)
        print(
            f"[{ID_EMPRESA}] legal={empresa.nombre_legal!r} "
            f"fantasia={empresa.nombre_fantasia!r}"
        )
        print(f"  empresas.cuit={emp_cuit}")
        print(f"  configuracion_empresa.cuit={cfg_cuit}")

        if emp_cuit not in {CUIT_ESPERADO_VIEJO, CUIT_NUEVO} and cfg_cuit not in {
            CUIT_ESPERADO_VIEJO,
            CUIT_NUEVO,
        }:
            print(
                f"ABORT: ni empresa ni config tienen {CUIT_ESPERADO_VIEJO} "
                f"ni {CUIT_NUEVO}. No piso un CUIT ajeno."
            )
            return 2

        if args.dry_run:
            print(f"dry-run: quedaría {CUIT_NUEVO} en ambas tablas")
            return 0

        empresa.cuit = CUIT_NUEVO
        config.cuit = CUIT_NUEVO
        db.add(empresa)
        db.add(config)
        db.commit()

        empresa2 = db.get(Empresa, ID_EMPRESA)
        config2 = db.get(ConfiguracionEmpresa, ID_EMPRESA)
        print(
            f"  despues emp={_solo_digitos(empresa2.cuit if empresa2 else '')} "
            f"cfg={_solo_digitos(config2.cuit if config2 else '')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
