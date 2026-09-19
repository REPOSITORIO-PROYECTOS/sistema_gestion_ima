#!/usr/bin/env python3
"""
Alta idempotente en PROD: Panadería Hercules (modo especial POS)
+ productos base PANADERIA / GOLOSINAS (precio_manual).

  Admin: pan-hercules

Uso (en S1, desde raíz del repo, con .env cargado):
  export PYTHONPATH=/home/dev_taup/proyectos/sistema_gestion_ima:$PYTHONPATH
  set -a && . .env && set +a
  back/venv/bin/python scripts/crear_panaderia_hercules_prod.py
  back/venv/bin/python scripts/crear_panaderia_hercules_prod.py --dry-run
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
import back.gestion.configuracion_manager as configuracion_manager
import back.gestion.empresa_manager as empresa_manager
from back.gestion import modo_especial_manager
from back.gestion import perfil_operativo_manager as perfil_operativo_manager
from back.modelos import Articulo, ConfiguracionEmpresa, Empresa, Usuario
from back.schemas.configuracion_schemas import ConfiguracionUpdate, FormatoComprobanteEnum
from back.schemas.empresa_schemas import EmpresaCreate
from back.schemas.modo_especial_schemas import ProductoModoEspecialCreate, UnidadMedidaEnum

NOMBRE_LEGAL = "PANADERIA HERCULES"
NOMBRE_FANTASIA = "Panadería Hercules"
# CUIT placeholder único (11 dígitos). Reemplazar por CUIT real cuando lo tengan.
CUIT = "20999888779"
ADMIN_USERNAME = "pan-hercules"
ADMIN_PASSWORD = "hercules123"
COLOR_PRINCIPAL = "bg-amber-700"
AFIP_CONDICION_IVA = "MONOTRIBUTO"
AFIP_PUNTO_VENTA = 1

# Productos base (mismo patrón que La Esquina / FULL24)
PRODUCTOS_BASE: tuple[tuple[str, str], ...] = (
    ("002992", "PANADERIA"),
    ("000498", "GOLOSINAS"),
)
PRECIO_PLACEHOLDER = 1.0
STOCK_ILIMITADO = 999999.0


def _buscar_empresa(db: Session) -> Empresa | None:
    por_cuit = db.exec(select(Empresa).where(Empresa.cuit == CUIT)).first()
    if por_cuit:
        return por_cuit
    return db.exec(
        select(Empresa).where(Empresa.nombre_fantasia == NOMBRE_FANTASIA)
    ).first()


def _asegurar_producto_base(
    db: Session,
    id_empresa: int,
    *,
    codigo: str,
    descripcion: str,
    dry: bool,
) -> str:
    existente = db.exec(
        select(Articulo).where(
            Articulo.id_empresa == id_empresa,
            Articulo.codigo_interno == codigo,
        )
    ).first()
    if existente:
        print(
            f"  · {codigo} {descripcion} ya existe id={existente.id} "
            f"pm={existente.precio_manual}"
        )
        if dry:
            return "exists"
        existente.descripcion = descripcion
        existente.precio_venta = PRECIO_PLACEHOLDER
        existente.venta_negocio = PRECIO_PLACEHOLDER
        existente.precio_costo = 0.0
        existente.tasa_iva = 0.21
        existente.precio_manual = True
        existente.auto_actualizar_precio = False
        existente.stock_actual = STOCK_ILIMITADO
        existente.unidad_venta = "Unidad"
        existente.unidad_compra = "Unidad"
        existente.activo = True
        modo_especial_manager._asignar_categorias_articulo(
            db, id_empresa, existente, [descripcion]
        )
        db.add(existente)
        db.commit()
        return "updated"

    print(f"  · crear {codigo} / {descripcion} (precio_manual)")
    if dry:
        return "would_create"

    modo_especial_manager.crear_producto(
        db,
        id_empresa,
        ProductoModoEspecialCreate(
            codigo_interno=codigo,
            descripcion=descripcion,
            precio_venta=PRECIO_PLACEHOLDER,
            precio_costo=0.0,
            categorias=[descripcion],
            stock=STOCK_ILIMITADO,
            barcodes=None,
            unidad=UnidadMedidaEnum.unidad,
            tasa_iva=0.21,
        ),
        omitir_conflictos_barcode=True,
        commit=True,
    )
    art = modo_especial_manager._obtener_articulo_por_codigo(db, id_empresa, codigo)
    if art is None:
        raise RuntimeError(f"No se pudo crear {codigo} en empresa {id_empresa}")
    art.precio_manual = True
    art.auto_actualizar_precio = False
    art.stock_actual = STOCK_ILIMITADO
    art.descripcion = descripcion
    db.add(art)
    db.commit()
    return "created"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Crear Panadería Hercules + productos base en prod"
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("=== Alta Panadería Hercules (PROD, modo especial POS) ===")
    print(f"  Empresa: {NOMBRE_FANTASIA} / {NOMBRE_LEGAL}")
    print(f"  CUIT placeholder: {CUIT}")
    print(f"  Admin: {ADMIN_USERNAME}")
    print(f"  Color: {COLOR_PRINCIPAL}")
    print(f"  Productos base: {', '.join(d for _, d in PRODUCTOS_BASE)}")
    if args.dry_run:
        print("  [dry-run] No se escribe nada.")
        return 0

    with Session(engine) as db:
        empresa = _buscar_empresa(db)
        empresa_nueva = empresa is None
        password_mostrada = ADMIN_PASSWORD

        if empresa:
            print(f"  Empresa ya existe id={empresa.id}")
            id_empresa = empresa.id
            admin = db.exec(
                select(Usuario).where(Usuario.nombre_usuario == ADMIN_USERNAME)
            ).first()
            if admin and admin.id_empresa != id_empresa:
                raise RuntimeError(
                    f"Usuario '{ADMIN_USERNAME}' existe en otra empresa "
                    f"(id={admin.id_empresa})."
                )
            if not admin:
                raise RuntimeError(
                    "Empresa existe pero falta el usuario admin; "
                    "revisar manualmente antes de recrear."
                )
            password_mostrada = "(sin cambio — empresa ya existía)"
            print(f"  Admin existente id={admin.id}")
        else:
            existente_admin = db.exec(
                select(Usuario).where(Usuario.nombre_usuario == ADMIN_USERNAME)
            ).first()
            if existente_admin:
                raise RuntimeError(
                    f"Usuario '{ADMIN_USERNAME}' ya existe en empresa "
                    f"id={existente_admin.id_empresa}."
                )
            empresa = empresa_manager.crear_empresa_y_primer_admin(
                db,
                EmpresaCreate(
                    nombre_legal=NOMBRE_LEGAL,
                    nombre_fantasia=NOMBRE_FANTASIA,
                    cuit=CUIT,
                    afip_condicion_iva=AFIP_CONDICION_IVA,
                    afip_punto_venta_predeterminado=AFIP_PUNTO_VENTA,
                    admin_username=ADMIN_USERNAME,
                    admin_password=ADMIN_PASSWORD,
                ),
            )
            id_empresa = empresa.id
            print(f"  Empresa creada id={id_empresa}")

        configuracion_manager.actualizar_configuracion_parcial(
            db=db,
            id_empresa=id_empresa,
            data=ConfiguracionUpdate(
                color_principal=COLOR_PRINCIPAL,
                nombre_negocio=NOMBRE_FANTASIA,
                formato_comprobante_predeterminado=FormatoComprobanteEnum.ticket,
            ),
        )
        perfil_operativo_manager.migrar_empresa_a_esquema_especial(
            db, id_empresa, "modo_especial_pos"
        )

        print("  Productos base:")
        for codigo, descripcion in PRODUCTOS_BASE:
            _asegurar_producto_base(
                db, id_empresa, codigo=codigo, descripcion=descripcion, dry=False
            )

        cfg = db.get(ConfiguracionEmpresa, id_empresa)
        if cfg is not None:
            cfg.catalogo_version = int(cfg.catalogo_version or 0) + 1
            db.add(cfg)
            db.commit()

        config = db.get(ConfiguracionEmpresa, id_empresa)
        admin = db.exec(
            select(Usuario).where(Usuario.nombre_usuario == ADMIN_USERNAME)
        ).first()
        perfil = perfil_operativo_manager.obtener_perfil_resuelto(db, id_empresa)
        arts = db.exec(
            select(Articulo).where(
                Articulo.id_empresa == id_empresa,
                Articulo.codigo_interno.in_([c for c, _ in PRODUCTOS_BASE]),
            )
        ).all()

        print("\n=== Resumen ===")
        print(f"  Empresa ID: {id_empresa}")
        print(f"  Nombre: {empresa.nombre_fantasia}")
        print(f"  CUIT: {empresa.cuit}")
        print(f"  Color: {config.color_principal if config else '?'}")
        print(f"  Nombre negocio: {config.nombre_negocio if config else '?'}")
        print(f"  Modo especial: {perfil.modo_especial} ({perfil.plantilla_origen})")
        print(f"  Nueva: {empresa_nueva}")
        print(f"  Admin user ID: {admin.id if admin else '?'}")
        print(f"  Login: {ADMIN_USERNAME}")
        print(f"  Password: {password_mostrada}")
        print("  Productos:")
        for art in arts:
            print(
                f"    {art.codigo_interno} {art.descripcion} "
                f"pm={art.precio_manual} pv={art.precio_venta} id={art.id}"
            )
        print("  URL: https://sistema-ima.sistemataup.online")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
