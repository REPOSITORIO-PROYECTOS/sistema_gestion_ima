#!/usr/bin/env python3
"""Diag one-shot: estado de-campo (37) vs La Esquina 2 (38)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlmodel import Session, func, select

from back.database import engine
from back.gestion import configuracion_manager, perfil_operativo_manager
from back.modelos import Articulo, ConfiguracionEmpresa, Empresa


def main() -> int:
    with Session(engine) as db:
        for eid in (35, 36, 37, 38):
            e = db.get(Empresa, eid)
            c = db.get(ConfiguracionEmpresa, eid)
            if not e:
                print(f"=== {eid}: NO EXISTE ===")
                continue
            n_art = db.exec(
                select(func.count())
                .select_from(Articulo)
                .where(Articulo.id_empresa == eid, Articulo.activo == True)  # noqa: E712
            ).one()
            stock_sum = db.exec(
                select(func.coalesce(func.sum(Articulo.stock_actual), 0)).where(
                    Articulo.id_empresa == eid, Articulo.activo == True  # noqa: E712
                )
            ).one()
            perfil = perfil_operativo_manager.obtener_perfil_resuelto(db, eid)
            afip = configuracion_manager.empresa_tiene_facturacion_afip_habilitada(db, eid)
            print(f"=== {eid} {e.nombre_fantasia!r} ===")
            print(f"  cuit_emp={e.cuit} activa={e.activa}")
            if c:
                print(
                    f"  cfg.cuit={c.cuit} pv={c.afip_punto_venta_predeterminado} "
                    f"iva={c.afip_condicion_iva} negocio={c.nombre_negocio!r}"
                )
                print(f"  dir={c.direccion_negocio!r} iibb={c.ingresos_brutos} inicio={c.inicio_actividades}")
                print(f"  modo_esp={c.modo_especial_habilitado} tipo={c.tipo_esquema_empresa}")
            print(
                f"  plantilla={perfil.plantilla_origen} solo_comp={perfil.caja_solo_comprobante} "
                f"puede_fact={perfil.caja_puede_facturar} afip_ok={afip}"
            )
            print(f"  transf_ids={perfil.empresas_transferencia_ids}")
            print(f"  factura_auto_mp={perfil.factura_auto_mercado_pago}")
            print(f"  articulos={n_art} stock_sum={stock_sum}")

        # Match catalog 37 vs 38
        arts37 = {
            (a.codigo_interno or "").strip(): a
            for a in db.exec(
                select(Articulo).where(Articulo.id_empresa == 37, Articulo.activo == True)  # noqa: E712
            ).all()
            if (a.codigo_interno or "").strip()
        }
        arts38 = {
            (a.codigo_interno or "").strip(): a
            for a in db.exec(
                select(Articulo).where(Articulo.id_empresa == 38, Articulo.activo == True)  # noqa: E712
            ).all()
            if (a.codigo_interno or "").strip()
        }
        comunes = set(arts37) & set(arts38)
        solo37 = set(arts37) - set(arts38)
        solo38 = set(arts38) - set(arts37)
        diff_stock = sum(
            1
            for k in comunes
            if abs((arts37[k].stock_actual or 0) - (arts38[k].stock_actual or 0)) > 0.001
        )
        diff_precio = sum(
            1
            for k in comunes
            if abs((arts37[k].precio_venta or 0) - (arts38[k].precio_venta or 0)) > 0.01
        )
        print("--- MATCH 37 vs 38 por codigo_interno ---")
        print(f"  comunes={len(comunes)} solo_campo={len(solo37)} solo_esquina2={len(solo38)}")
        print(f"  comunes_diff_stock={diff_stock} comunes_diff_precio={diff_precio}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
