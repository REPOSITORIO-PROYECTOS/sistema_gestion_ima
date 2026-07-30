#!/usr/bin/env python3
"""Habilita facturación en caja solo para empresa 39 (CUIT de la config)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlmodel import Session

from back.database import engine
from back.gestion import configuracion_manager, perfil_operativo_manager
from back.modelos import ConfiguracionEmpresa, Empresa
from back.schemas.perfil_operativo_schemas import PerfilOperativoUpdate

ID = 39


def main() -> int:
    with Session(engine) as db:
        emp = db.get(Empresa, ID)
        cfg = db.get(ConfiguracionEmpresa, ID)
        if not emp or not cfg:
            print("Empresa/config 39 no encontrada")
            return 1

        cuit_emp = "".join(filter(str.isdigit, emp.cuit or ""))
        cuit_cfg = "".join(filter(str.isdigit, str(cfg.cuit or "")))
        print(f"ANTES cuit_empresa={cuit_emp} cuit_config={cuit_cfg} pv={cfg.afip_punto_venta_predeterminado}")

        # Alinear config.cuit con empresa.cuit (fuente de verdad cargada)
        if cuit_emp and cuit_cfg != cuit_emp:
            cfg.cuit = cuit_emp
            db.add(cfg)
            db.commit()
            print(f"  config.cuit alineado → {cuit_emp}")

        if not cfg.afip_punto_venta_predeterminado:
            cfg.afip_punto_venta_predeterminado = 1
            db.add(cfg)
            db.commit()
            print("  PV seteado a 1")

        afip_ok = configuracion_manager.empresa_tiene_facturacion_afip_habilitada(db, ID)
        print(f"  bóveda/AFIP habilitada={afip_ok}")

        # Permitir factura desde caja (solo esta empresa)
        perfil_operativo_manager.actualizar_perfil_operativo(
            db,
            ID,
            PerfilOperativoUpdate(caja_solo_comprobante=False),
        )

        resuelto = perfil_operativo_manager.obtener_perfil_resuelto(db, ID)
        print("DESPUES:")
        print(f"  cuit={emp.cuit}")
        print(f"  facturacion_afip={resuelto.facturacion_afip_habilitada}")
        print(f"  caja_solo_comprobante={resuelto.caja_solo_comprobante}")
        print(f"  caja_puede_facturar={resuelto.caja_puede_facturar}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
