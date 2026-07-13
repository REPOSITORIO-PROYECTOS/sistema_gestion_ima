#!/usr/bin/env python3
"""
Revierte cambios sobre La Esquina prod (35) y crea demo separada: La Esquina 2 + de-campo.

NO toca FULL24 (36) ni usuarios originales de La Esquina (35).
"""
from __future__ import annotations

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
from back.modelos import ConfiguracionEmpresa, Empresa, Rol, Usuario
from back.schemas.admin_schemas import UsuarioCreate
from back.schemas.configuracion_schemas import ConfiguracionUpdate
from back.schemas.empresa_schemas import EmpresaCreate

ID_LA_ESQUINA_PROD = 35
ID_F24_PROD = 36
USUARIOS_DEMO_A_ELIMINAR = ("admin_esquina", "encargada_esquina", "vendedora_esquina")

DEMO_SUCURSALES = (
    {
        "nombre_fantasia": "La Esquina 2",
        "nombre_legal": "LA ESQUINA 2 DEMO SRL",
        "cuit": "20111222333",
        "admin_username": "admin_esquina2",
        "admin_password": "esquina2123",
        "usuarios_extra": (
            ("encargada_esquina2", "Encargada", "encargada123"),
            ("vendedora_esquina2", "Vendedora", "vendedor123"),
        ),
    },
    {
        "nombre_fantasia": "de-campo",
        "nombre_legal": "DE CAMPO DEMO SRL",
        "cuit": "20987654321",
        "admin_username": "admin_campo",
        "admin_password": "decampo123",
        "usuarios_extra": (
            ("encargada_campo", "Encargada", "encargada123"),
            ("vendedora_campo", "Vendedora", "vendedor123"),
        ),
    },
)


def _obtener_rol(db: Session, nombre: str) -> Rol:
    rol = db.exec(select(Rol).where(Rol.nombre == nombre)).first()
    if not rol:
        raise RuntimeError(f"Rol '{nombre}' no encontrado.")
    return rol


def _revertir_la_esquina_prod(db: Session) -> None:
    print("\n=== Revertir La Esquina prod (id=35) ===")
    empresa = db.get(Empresa, ID_LA_ESQUINA_PROD)
    if not empresa:
        print("  Empresa 35 no encontrada, omitiendo.")
        return

    if empresa.nombre_fantasia != "LA ESQUINA":
        empresa.nombre_fantasia = "LA ESQUINA"
        db.add(empresa)
        db.commit()
        print("  nombre_fantasia restaurado a 'LA ESQUINA'")

    for username in USUARIOS_DEMO_A_ELIMINAR:
        usuario = db.exec(select(Usuario).where(Usuario.nombre_usuario == username)).first()
        if usuario and usuario.id_empresa == ID_LA_ESQUINA_PROD:
            db.delete(usuario)
            print(f"  Usuario demo eliminado: {username}")

    db.commit()
    print("  Usuarios originales de La Esquina intactos.")


def _buscar_demo(db: Session, nombre_fantasia: str) -> Empresa | None:
    return db.exec(
        select(Empresa).where(Empresa.nombre_fantasia == nombre_fantasia)
    ).first()


def _asegurar_modo_especial(db: Session, id_empresa: int) -> None:
    config = db.get(ConfiguracionEmpresa, id_empresa)
    if not config:
        raise RuntimeError(f"Sin config para empresa {id_empresa}")
    if not config.modo_especial_habilitado:
        configuracion_manager.actualizar_configuracion_parcial(
            db=db,
            id_empresa=id_empresa,
            data=ConfiguracionUpdate(modo_especial_habilitado=True),
        )
        db.commit()


def _crear_usuario_demo(
    db: Session,
    *,
    nombre_usuario: str,
    password: str,
    id_rol: int,
    id_empresa: int,
) -> None:
    existente = db.exec(
        select(Usuario).where(Usuario.nombre_usuario == nombre_usuario)
    ).first()
    if existente:
        if existente.id_empresa != id_empresa:
            raise RuntimeError(
                f"Usuario '{nombre_usuario}' existe en otra empresa (id={existente.id_empresa})."
            )
        admin_manager.actualizar_password_usuario(db, existente.id, password)
        print(f"  · {nombre_usuario} (password actualizada)")
        return

    admin_manager.crear_usuario(
        db,
        UsuarioCreate(
            nombre_usuario=nombre_usuario,
            password=password,
            id_rol=id_rol,
            id_empresa=id_empresa,
        ),
    )
    print(f"  · {nombre_usuario} creado")


def _asegurar_demo(db: Session, datos: dict) -> Empresa:
    nombre = datos["nombre_fantasia"]
    print(f"\n=== Demo: {nombre} ===")

    empresa = _buscar_demo(db, nombre)
    if empresa and empresa.id in (ID_LA_ESQUINA_PROD, ID_F24_PROD):
        raise RuntimeError(f"'{nombre}' colisiona con empresa prod id={empresa.id}")

    if empresa:
        print(f"  Empresa existente id={empresa.id}")
    else:
        empresa = empresa_manager.crear_empresa_y_primer_admin(
            db,
            EmpresaCreate(
                nombre_legal=datos["nombre_legal"],
                nombre_fantasia=datos["nombre_fantasia"],
                cuit=datos["cuit"],
                afip_condicion_iva="MONOTRIBUTO",
                afip_punto_venta_predeterminado=1,
                admin_username=datos["admin_username"],
                admin_password=datos["admin_password"],
            ),
        )
        print(f"  Empresa creada id={empresa.id}")

    _asegurar_modo_especial(db, empresa.id)
    print("  Modo especial: habilitado")

    rol_admin = _obtener_rol(db, "Admin")
    _crear_usuario_demo(
        db,
        nombre_usuario=datos["admin_username"],
        password=datos["admin_password"],
        id_rol=rol_admin.id,
        id_empresa=empresa.id,
    )
    for username, rol_nombre, password in datos["usuarios_extra"]:
        rol = _obtener_rol(db, rol_nombre)
        _crear_usuario_demo(
            db,
            nombre_usuario=username,
            password=password,
            id_rol=rol.id,
            id_empresa=empresa.id,
        )

    return empresa


def main() -> int:
    ids_demo: list[int] = []
    with Session(engine) as db:
        _revertir_la_esquina_prod(db)
        for datos in DEMO_SUCURSALES:
            empresa = _asegurar_demo(db, datos)
            ids_demo.append(empresa.id)

    print("\n=== Resumen demo (separado de prod 35/36) ===")
    for datos, id_empresa in zip(DEMO_SUCURSALES, ids_demo, strict=True):
        print(f"\n{datos['nombre_fantasia']} (id={id_empresa})")
        print(f"  Admin: {datos['admin_username']} / {datos['admin_password']}")
        for username, rol, password in datos["usuarios_extra"]:
            print(f"  {rol}: {username} / {password}")

    print(f"\nIDs demo transferencias: {sorted(ids_demo)}")
    print(f"Prod intacto: La Esquina={ID_LA_ESQUINA_PROD}, FULL24={ID_F24_PROD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
