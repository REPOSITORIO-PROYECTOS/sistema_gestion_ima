#!/usr/bin/env python3
"""
Alta idempotente en PROD: empresa Kiosco Rivadavia + admin Juan.

Uso (en S1, desde raíz del repo, con back/.env cargado):
  export PYTHONPATH=/home/dev_taup/proyectos/sistema_gestion_ima:$PYTHONPATH
  set -a && . back/.env && set +a
  back/venv/bin/python scripts/crear_kiosco_rivadavia_prod.py
  back/venv/bin/python scripts/crear_kiosco_rivadavia_prod.py --dry-run
"""
from __future__ import annotations

import argparse
import secrets
import string
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlmodel import Session, select

from back.database import engine
import back.gestion.configuracion_manager as configuracion_manager
import back.gestion.empresa_manager as empresa_manager
from back.gestion import perfil_operativo_manager as perfil_operativo_manager
from back.modelos import ConfiguracionEmpresa, Empresa, Usuario
from back.schemas.configuracion_schemas import ConfiguracionUpdate
from back.schemas.empresa_schemas import EmpresaCreate

# Datos del alta (nombre de empresa se puede cambiar después)
NOMBRE_LEGAL = "KIOSCO RIVADAVIA"
NOMBRE_FANTASIA = "Kiosco Rivadavia"
# CUIT placeholder único (11 dígitos). Reemplazar por CUIT real cuando lo tengan.
CUIT = "20999888776"
ADMIN_USERNAME = "juan_rivadavia"
COLOR_PRINCIPAL = "bg-amber-300"  # Amarillo claro — distintivo kiosco
AFIP_CONDICION_IVA = "MONOTRIBUTO"
AFIP_PUNTO_VENTA = 1


def _generar_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _buscar_empresa(db: Session) -> Empresa | None:
    por_cuit = db.exec(select(Empresa).where(Empresa.cuit == CUIT)).first()
    if por_cuit:
        return por_cuit
    return db.exec(
        select(Empresa).where(Empresa.nombre_fantasia == NOMBRE_FANTASIA)
    ).first()


def main() -> int:
    parser = argparse.ArgumentParser(description="Crear Kiosco Rivadavia + Juan en prod")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--password",
        default="",
        help="Password del admin (si vacío, se genera una)",
    )
    args = parser.parse_args()

    password = args.password.strip() or _generar_password()

    print("=== Alta Kiosco Rivadavia (PROD) ===")
    print(f"  Empresa: {NOMBRE_FANTASIA} / {NOMBRE_LEGAL}")
    print(f"  CUIT: {CUIT}")
    print(f"  Admin: {ADMIN_USERNAME}")
    print(f"  Color: {COLOR_PRINCIPAL}")
    if args.dry_run:
        print("  [dry-run] No se escribe nada.")
        return 0

    with Session(engine) as db:
        existente_user = db.exec(
            select(Usuario).where(Usuario.nombre_usuario == ADMIN_USERNAME)
        ).first()
        empresa = _buscar_empresa(db)

        if empresa:
            print(f"  Empresa ya existe id={empresa.id}")
            if existente_user and existente_user.id_empresa != empresa.id:
                raise RuntimeError(
                    f"Usuario '{ADMIN_USERNAME}' existe en otra empresa "
                    f"(id={existente_user.id_empresa})."
                )
            if not existente_user:
                raise RuntimeError(
                    "Empresa existe pero falta el usuario admin; "
                    "revisar manualmente antes de recrear."
                )
            print(f"  Admin existente id={existente_user.id} (password NO se regenera)")
            id_empresa = empresa.id
            password_mostrada = "(sin cambio — empresa ya existía)"
        else:
            if existente_user:
                raise RuntimeError(
                    f"Usuario '{ADMIN_USERNAME}' ya existe en empresa "
                    f"id={existente_user.id_empresa}."
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
                    admin_password=password,
                ),
            )
            id_empresa = empresa.id
            password_mostrada = password
            print(f"  Empresa creada id={id_empresa}")

        configuracion_manager.actualizar_configuracion_parcial(
            db=db,
            id_empresa=id_empresa,
            data=ConfiguracionUpdate(
                color_principal=COLOR_PRINCIPAL,
                nombre_negocio=NOMBRE_FANTASIA,
            ),
        )
        # Kioscos = modo especial POS (catálogo manual, solo comprobante, sin Sheets)
        perfil_operativo_manager.migrar_empresa_a_esquema_especial(
            db, id_empresa, "modo_especial_pos"
        )

        config = db.get(ConfiguracionEmpresa, id_empresa)
        admin = db.exec(
            select(Usuario).where(Usuario.nombre_usuario == ADMIN_USERNAME)
        ).first()
        perfil = perfil_operativo_manager.obtener_perfil_resuelto(db, id_empresa)

        print("\n=== Resumen ===")
        print(f"  Empresa ID: {id_empresa}")
        print(f"  Nombre: {empresa.nombre_fantasia}")
        print(f"  CUIT: {empresa.cuit}")
        print(f"  Color: {config.color_principal if config else '?'}")
        print(f"  Nombre negocio: {config.nombre_negocio if config else '?'}")
        print(f"  Modo especial: {perfil.modo_especial} ({perfil.plantilla_origen})")
        print(f"  Admin user ID: {admin.id if admin else '?'}")
        print(f"  Login: {ADMIN_USERNAME}")
        print(f"  Password: {password_mostrada}")
        print("  URL: https://sistema-ima.sistemataup.online")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
