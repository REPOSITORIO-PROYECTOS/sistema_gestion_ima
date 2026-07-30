#!/usr/bin/env python3
"""
Alinea La Esquina 2 (38) con de-campo (37) en producción:

1) Datos fiscales: CUIT + campos AFIP de 37 → 38 (PV de 38 se conserva).
2) Catálogo faltante: artículos activos de 37 cuyo codigo_interno no está en 38.
3) Precios: en códigos comunes, precio_venta/costo/margen/tasa_iva de 37 → 38.

No toca stock de artículos existentes. Los nuevos se crean con stock=0.
No implementa autofactura por transferencia/POS.

Uso:
  python scripts/sync_campo37_a_esquina38.py --dry-run
  python scripts/sync_campo37_a_esquina38.py --apply
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from back.database import engine
from back.gestion import configuracion_manager, modo_especial_manager
from back.modelos import Articulo, ConfiguracionEmpresa, Empresa
from back.schemas.modo_especial_schemas import ProductoModoEspecialCreate, UnidadMedidaEnum

ID_ORIGEN = 37
ID_DESTINO = 38


def _categorias(articulo: Articulo) -> list[str]:
    raw = getattr(articulo, "categorias", None)
    if isinstance(raw, list) and raw:
        return [str(c).strip() for c in raw if str(c).strip()]
    if articulo.categoria and articulo.categoria.nombre:
        return [articulo.categoria.nombre]
    return ["General"]


def _unidad(articulo: Articulo) -> str:
    u = (articulo.unidad_venta or "unidad").strip().lower()
    valid = {e.value for e in UnidadMedidaEnum}
    return u if u in valid else "unidad"


def _precio_diffiere(a: Articulo, b: Articulo) -> bool:
    return (
        abs((a.precio_venta or 0) - (b.precio_venta or 0)) > 0.01
        or abs((a.precio_costo or 0) - (b.precio_costo or 0)) > 0.01
        or abs((a.margen_ganancia or 0) - (b.margen_ganancia or 0)) > 0.0001
        or abs((a.tasa_iva or 0) - (b.tasa_iva or 0)) > 0.0001
    )


def alinear_fiscales(db: Session, *, dry: bool) -> dict[str, str]:
    origen_e = db.get(Empresa, ID_ORIGEN)
    destino_e = db.get(Empresa, ID_DESTINO)
    origen_c = db.get(ConfiguracionEmpresa, ID_ORIGEN)
    destino_c = db.get(ConfiguracionEmpresa, ID_DESTINO)
    if not all((origen_e, destino_e, origen_c, destino_c)):
        raise RuntimeError("Faltan empresa/config 37 u 38")

    cambios: dict[str, str] = {}
    pv_destino = destino_c.afip_punto_venta_predeterminado  # conservar PV propio

    if destino_e.cuit != origen_e.cuit:
        cambios["empresa.cuit"] = f"{destino_e.cuit} -> {origen_e.cuit}"
        if not dry:
            destino_e.cuit = origen_e.cuit

    fields = (
        "cuit",
        "afip_condicion_iva",
        "ingresos_brutos",
        "inicio_actividades",
        "direccion_negocio",
        "telefono_negocio",
        "mail_negocio",
    )
    for field in fields:
        old = getattr(destino_c, field)
        new = getattr(origen_c, field)
        if old != new:
            cambios[f"config.{field}"] = f"{old!r} -> {new!r}"
            if not dry:
                setattr(destino_c, field, new)

    # Ticket: mantener identidad de sucursal si ya tiene nombre; si no, usar fantasia.
    if not (destino_c.nombre_negocio or "").strip():
        nombre = destino_e.nombre_fantasia or "La Esquina 2"
        cambios["config.nombre_negocio"] = f"{destino_c.nombre_negocio!r} -> {nombre!r}"
        if not dry:
            destino_c.nombre_negocio = nombre

    if destino_c.afip_punto_venta_predeterminado != pv_destino:
        # no debería pasar; defensa
        if not dry:
            destino_c.afip_punto_venta_predeterminado = pv_destino

    if not dry and cambios:
        db.add(destino_e)
        db.add(destino_c)
        db.commit()

    afip_ok = configuracion_manager.empresa_tiene_facturacion_afip_habilitada(db, ID_DESTINO)
    cambios["post.afip_ok_38"] = str(afip_ok)
    cambios["post.pv_38"] = str(destino_c.afip_punto_venta_predeterminado)
    return cambios


def sync_catalogo_y_precios(db: Session, *, dry: bool) -> dict[str, int]:
    origenes = db.exec(
        select(Articulo)
        .where(Articulo.id_empresa == ID_ORIGEN, Articulo.activo == True)  # noqa: E712
        .options(selectinload(Articulo.codigos), selectinload(Articulo.categoria))
    ).all()
    destinos = db.exec(
        select(Articulo)
        .where(Articulo.id_empresa == ID_DESTINO, Articulo.activo == True)  # noqa: E712
        .options(selectinload(Articulo.codigos))
    ).all()

    map37 = {(a.codigo_interno or "").strip(): a for a in origenes if (a.codigo_interno or "").strip()}
    map38 = {(a.codigo_interno or "").strip(): a for a in destinos if (a.codigo_interno or "").strip()}

    faltantes = sorted(set(map37) - set(map38))
    comunes = sorted(set(map37) & set(map38))
    a_actualizar = [k for k in comunes if _precio_diffiere(map37[k], map38[k])]

    stats = {
        "origen_activos": len(map37),
        "destino_activos": len(map38),
        "faltantes": len(faltantes),
        "comunes": len(comunes),
        "precios_a_actualizar": len(a_actualizar),
        "creados": 0,
        "precios_ok": 0,
        "errores_alta": 0,
    }

    print(f"faltantes={len(faltantes)} precios_diff={len(a_actualizar)}")
    for k in faltantes[:8]:
        a = map37[k]
        print(f"  + {k} | {(a.descripcion or '')[:50]} | pv={a.precio_venta}")
    for k in a_actualizar[:8]:
        a, b = map37[k], map38[k]
        print(f"  $ {k} | 38:{b.precio_venta} -> 37:{a.precio_venta}")

    if dry:
        return stats

    for codigo in faltantes:
        a = map37[codigo]
        bars = [c.codigo.strip() for c in (a.codigos or []) if c.codigo and c.codigo.strip()]
        try:
            modo_especial_manager.crear_producto(
                db,
                ID_DESTINO,
                ProductoModoEspecialCreate(
                    codigo_interno=codigo,
                    descripcion=(a.descripcion or codigo).strip(),
                    precio_venta=float(a.precio_venta or 0),
                    precio_costo=float(a.precio_costo or 0),
                    categorias=_categorias(a),
                    stock=0.0,
                    barcodes=bars,
                    unidad=UnidadMedidaEnum(_unidad(a)),
                    tasa_iva=float(a.tasa_iva if a.tasa_iva is not None else 0.21),
                ),
                omitir_conflictos_barcode=True,
                commit=True,
            )
            # margen no va en create schema: setear post-alta
            nuevo = db.exec(
                select(Articulo).where(
                    Articulo.id_empresa == ID_DESTINO,
                    Articulo.codigo_interno == codigo,
                )
            ).first()
            if nuevo is not None:
                nuevo.margen_ganancia = float(a.margen_ganancia or 0)
                db.add(nuevo)
                db.commit()
            stats["creados"] += 1
        except Exception as exc:
            stats["errores_alta"] += 1
            print(f"ERROR alta {codigo}: {exc}")

    for codigo in a_actualizar:
        a = map37[codigo]
        b = map38[codigo]
        b.precio_venta = float(a.precio_venta or 0)
        b.venta_negocio = float(a.precio_venta or 0)
        b.precio_costo = float(a.precio_costo or 0)
        b.margen_ganancia = float(a.margen_ganancia or 0)
        b.tasa_iva = float(a.tasa_iva if a.tasa_iva is not None else b.tasa_iva)
        db.add(b)
        stats["precios_ok"] += 1

    if a_actualizar:
        cfg = db.get(ConfiguracionEmpresa, ID_DESTINO)
        if cfg is not None:
            cfg.catalogo_version = int(cfg.catalogo_version or 0) + 1
            db.add(cfg)
        db.commit()

    return stats


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    dry = bool(args.dry_run)

    print(f"=== sync 37→38 ({'DRY-RUN' if dry else 'APPLY'}) ===")
    with Session(engine) as db:
        print("--- fiscales ---")
        fisc = alinear_fiscales(db, dry=dry)
        for k, v in fisc.items():
            print(f"  {k}: {v}")

        print("--- catalogo/precios ---")
        stats = sync_catalogo_y_precios(db, dry=dry)
        for k, v in stats.items():
            print(f"  {k}={v}")

        if not dry:
            # re-check afip
            afip = configuracion_manager.empresa_tiene_facturacion_afip_habilitada(db, ID_DESTINO)
            e38 = db.get(Empresa, ID_DESTINO)
            c38 = db.get(ConfiguracionEmpresa, ID_DESTINO)
            print("--- post ---")
            print(f"  38.cuit={e38.cuit if e38 else None} cfg.cuit={c38.cuit if c38 else None}")
            print(f"  38.iva={c38.afip_condicion_iva if c38 else None} pv={c38.afip_punto_venta_predeterminado if c38 else None}")
            print(f"  38.afip_ok={afip}")

    return 0 if stats.get("errores_alta", 0) == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
