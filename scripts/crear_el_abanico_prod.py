#!/usr/bin/env python3
"""
Alta idempotente en PROD: empresa El Abanico (modo especial POS) + usuarios.

  Admin:     osvaldo
  Encargada: guada, belen
  Cajero:    nataly, celina

Uso (en S1, desde raíz del repo, con .env cargado):
  export PYTHONPATH=/home/dev_taup/proyectos/sistema_gestion_ima:$PYTHONPATH
  set -a && . .env && set +a
  back/venv/bin/python scripts/crear_el_abanico_prod.py
  back/venv/bin/python scripts/crear_el_abanico_prod.py --dry-run
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
import back.gestion.admin.admin_manager as admin_manager
import back.gestion.configuracion_manager as configuracion_manager
import back.gestion.empresa_manager as empresa_manager
from back.gestion import perfil_operativo_manager as perfil_operativo_manager
from back.modelos import ConfiguracionEmpresa, Empresa, Rol, Usuario
from back.schemas.admin_schemas import UsuarioCreate
from back.schemas.configuracion_schemas import ConfiguracionUpdate, FormatoComprobanteEnum
from back.schemas.empresa_schemas import EmpresaCreate

NOMBRE_LEGAL = "EL ABANICO"
NOMBRE_FANTASIA = "El Abanico"
# CUIT placeholder único (11 dígitos). Reemplazar por CUIT real cuando lo tengan.
CUIT = "20999888778"
DIRECCION = "Mendoza y Calle 10, Pocito, San Juan"
COLOR_PRINCIPAL = "bg-green-800"  # Verde — selector de gestión de negocio
AFIP_CONDICION_IVA = "MONOTRIBUTO"
AFIP_PUNTO_VENTA = 1

ADMIN_USERNAME = "osvaldo"
ADMIN_PASSWORD = "osvaldo123"

USUARIOS_EXTRA: tuple[tuple[str, str, str], ...] = (
    ("guada", "Encargada", "guada123"),
    ("belen", "Encargada", "belen123"),
    ("nataly", "Cajero", "nataly123"),
    ("celina", "Cajero", "celina123"),
)


def _obtener_rol(db: Session, nombre: str) -> Rol:
    rol = db.exec(select(Rol).where(Rol.nombre == nombre)).first()
    if not rol:
        raise RuntimeError(f"Rol '{nombre}' no encontrado.")
    return rol


def _buscar_empresa(db: Session) -> Empresa | None:
    por_cuit = db.exec(select(Empresa).where(Empresa.cuit == CUIT)).first()
    if por_cuit:
        return por_cuit
    return db.exec(
        select(Empresa).where(Empresa.nombre_fantasia == NOMBRE_FANTASIA)
    ).first()


def _asegurar_usuario(
    db: Session,
    *,
    nombre_usuario: str,
    password: str,
    id_rol: int,
    id_empresa: int,
    regenerar_password: bool,
) -> tuple[Usuario, str]:
    existente = db.exec(
        select(Usuario).where(Usuario.nombre_usuario == nombre_usuario)
    ).first()
    if existente:
        if existente.id_empresa != id_empresa:
            raise RuntimeError(
                f"Usuario '{nombre_usuario}' existe en otra empresa "
                f"(id={existente.id_empresa})."
            )
        if regenerar_password:
            admin_manager.actualizar_password_usuario(db, existente.id, password)
            return existente, password
        return existente, "(sin cambio — usuario ya existía)"

    admin_manager.crear_usuario(
        db,
        UsuarioCreate(
            nombre_usuario=nombre_usuario,
            password=password,
            id_rol=id_rol,
            id_empresa=id_empresa,
        ),
    )
    creado = db.exec(
        select(Usuario).where(Usuario.nombre_usuario == nombre_usuario)
    ).first()
    if not creado:
        raise RuntimeError(f"No se pudo crear el usuario '{nombre_usuario}'.")
    return creado, password


def main() -> int:
    parser = argparse.ArgumentParser(description="Crear El Abanico + usuarios en prod")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("=== Alta El Abanico (PROD, modo especial POS) ===")
    print(f"  Empresa: {NOMBRE_FANTASIA} / {NOMBRE_LEGAL}")
    print(f"  CUIT placeholder: {CUIT}")
    print(f"  Dirección: {DIRECCION}")
    print(f"  Color: {COLOR_PRINCIPAL}")
    print(f"  Admin: {ADMIN_USERNAME}")
    print(f"  Extra: {', '.join(u[0] + '/' + u[1] for u in USUARIOS_EXTRA)}")
    if args.dry_run:
        print("  [dry-run] No se escribe nada.")
        return 0

    credenciales: list[tuple[str, str, str]] = []

    with Session(engine) as db:
        empresa = _buscar_empresa(db)
        empresa_nueva = empresa is None

        if empresa:
            print(f"  Empresa ya existe id={empresa.id}")
            id_empresa = empresa.id
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
                direccion_negocio=DIRECCION,
                formato_comprobante_predeterminado=FormatoComprobanteEnum.ticket,
            ),
        )
        perfil_operativo_manager.migrar_empresa_a_esquema_especial(
            db, id_empresa, "modo_especial_pos"
        )

        rol_admin = _obtener_rol(db, "Admin")
        admin, pass_admin = _asegurar_usuario(
            db,
            nombre_usuario=ADMIN_USERNAME,
            password=ADMIN_PASSWORD,
            id_rol=rol_admin.id,
            id_empresa=id_empresa,
            regenerar_password=empresa_nueva,
        )
        credenciales.append((ADMIN_USERNAME, "Admin", pass_admin))
        print(f"  · {ADMIN_USERNAME} (Admin) id={admin.id}")

        for username, rol_nombre, password in USUARIOS_EXTRA:
            rol = _obtener_rol(db, rol_nombre)
            usuario, pass_mostrada = _asegurar_usuario(
                db,
                nombre_usuario=username,
                password=password,
                id_rol=rol.id,
                id_empresa=id_empresa,
                regenerar_password=False,
            )
            credenciales.append((username, rol_nombre, pass_mostrada))
            print(f"  · {username} ({rol_nombre}) id={usuario.id}")

        config = db.get(ConfiguracionEmpresa, id_empresa)
        perfil = perfil_operativo_manager.obtener_perfil_resuelto(db, id_empresa)

        print("\n=== Resumen ===")
        print(f"  Empresa ID: {id_empresa}")
        print(f"  Nombre: {empresa.nombre_fantasia}")
        print(f"  CUIT: {empresa.cuit}")
        print(f"  Dirección: {config.direccion_negocio if config else '?'}")
        print(f"  Color: {config.color_principal if config else '?'}")
        print(f"  Nombre negocio: {config.nombre_negocio if config else '?'}")
        print(f"  Modo especial: {perfil.modo_especial} ({perfil.plantilla_origen})")
        print("  Logins:")
        for username, rol_nombre, password in credenciales:
            print(f"    {rol_nombre:10} {username} / {password}")
        print("  URL: https://sistema-ima.sistemataup.online")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
