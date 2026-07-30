#!/usr/bin/env python3
"""
Habilita panel de estadísticas en todas las empresas con modo especial.

Uso (raíz del repo, venv + DB prod/local):
  python scripts/habilitar_panel_estadisticas_especial.py
  python scripts/habilitar_panel_estadisticas_especial.py --dry-run
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sqlmodel import Session, select

from back.database import engine
from back.gestion import perfil_operativo_manager
from back.modelos import ConfiguracionEmpresa
from back.schemas.perfil_operativo_schemas import TipoEsquemaEmpresa


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Habilitar panel estadísticas en empresas modo especial"
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with Session(engine) as db:
        if args.dry_run:
            configs = db.exec(select(ConfiguracionEmpresa)).all()
            candidatas: list[int] = []
            for config in configs:
                tipo = perfil_operativo_manager._parse_tipo_esquema(config)
                perfil = perfil_operativo_manager.aplicar_fallback_legacy(
                    config, perfil_operativo_manager.cargar_perfil_desde_json(config)
                )
                if (
                    tipo == TipoEsquemaEmpresa.ESPECIAL
                    or perfil.modo_especial
                    or bool(getattr(config, "modo_especial_habilitado", False))
                ):
                    candidatas.append(int(config.id_empresa))
            print(f"Dry-run: se habilitaría panel en empresas {candidatas}")
            return 0

        resultado = perfil_operativo_manager.habilitar_panel_estadisticas_modo_especial(db)
        print(f"Actualizadas ({resultado['total_actualizadas']}): {resultado['actualizadas']}")
        print(f"Omitidas estándar: {len(resultado['omitidas_estandar'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
