#!/usr/bin/env python3
"""
Seed mínimo para desarrollo local: empresa con modo especial + usuarios + productos.

Requisitos:
  - Docker MySQL en 127.0.0.1:3308 (docker compose up -d db)
  - .env con DB_HOST=127.0.0.1 y DB_PORT=3308

Uso (desde la raíz del repo):
  $env:PYTHONPATH = (Get-Location).Path
  .\.venv\Scripts\python.exe scripts\seed_local_modo_especial.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sqlmodel import Session, select

from back.database import create_db_and_tables, engine
from back.gestion.admin import admin_manager
from back.gestion.plantillas_perfil import PLANTILLA_MODO_ESPECIAL_DEMO
from back.modelos import Articulo, ArticuloCodigo, ConfiguracionEmpresa, Empresa, Rol, Usuario
from back.schemas.perfil_operativo_schemas import TipoEsquemaEmpresa
from back.schemas.admin_schemas import UsuarioCreate

ADMIN_USER = "admin_local"
ADMIN_PASSWORD = "Local2026!"
ENCARGADA_USER = "encargada_local"
ENCARGADA_PASSWORD = "Local2026!"

ROLES = ["Admin", "Gerente", "Encargada", "Cajero", "Vendedora", "Soporte", "Mozo"]

PRODUCTOS_DEMO = [
    {
        "codigo_interno": "LOC-001",
        "descripcion": "Yerba mate 500g",
        "precio_venta": 3500.0,
        "precio_costo": 2800.0,
        "stock_actual": 24.0,
        "stock_minimo": 5.0,
        "categorias": ["Almacén"],
        "barcode": "7790001000011",
    },
    {
        "codigo_interno": "LOC-002",
        "descripcion": "Aceite girasol 900ml",
        "precio_venta": 4200.0,
        "precio_costo": 3300.0,
        "stock_actual": 18.0,
        "stock_minimo": 4.0,
        "categorias": ["Almacén"],
        "barcode": "7790001000028",
    },
    {
        "codigo_interno": "LOC-003",
        "descripcion": "Arroz largo fino 1kg",
        "precio_venta": 2100.0,
        "precio_costo": 1600.0,
        "stock_actual": 40.0,
        "stock_minimo": 10.0,
        "categorias": ["Almacén", "Granos"],
        "barcode": "7790001000035",
    },
    {
        "codigo_interno": "LOC-004",
        "descripcion": "Gaseosa cola 2.25L",
        "precio_venta": 3800.0,
        "precio_costo": 2900.0,
        "stock_actual": 12.0,
        "stock_minimo": 6.0,
        "categorias": ["Bebidas"],
        "barcode": "7790001000042",
    },
    {
        "codigo_interno": "LOC-005",
        "descripcion": "Pan lactal integral",
        "precio_venta": 3200.0,
        "precio_costo": 2400.0,
        "stock_actual": 8.0,
        "stock_minimo": 3.0,
        "categorias": ["Panadería"],
        "barcode": "7790001000059",
    },
]


def ensure_roles(db: Session) -> dict[str, Rol]:
    by_name: dict[str, Rol] = {}
    for nombre in ROLES:
        rol = db.exec(select(Rol).where(Rol.nombre == nombre)).first()
        if not rol:
            rol = Rol(nombre=nombre)
            db.add(rol)
            db.flush()
        by_name[nombre] = rol
    db.commit()
    return by_name


def _aplicar_perfil_modo_especial_local(config: ConfiguracionEmpresa) -> None:
    config.modo_especial_habilitado = True
    config.tipo_esquema_empresa = TipoEsquemaEmpresa.ESPECIAL.value
    config.perfil_operativo = PLANTILLA_MODO_ESPECIAL_DEMO.model_dump()
    config.nombre_negocio = "Demo Modo Especial Local"


def ensure_empresa_modo_especial(db: Session) -> Empresa:
    empresa = db.exec(
        select(Empresa).where(Empresa.cuit == "20999999999")
    ).first()
    if empresa:
        config = db.get(ConfiguracionEmpresa, empresa.id)
        if config:
            _aplicar_perfil_modo_especial_local(config)
            db.add(config)
            db.commit()
        return empresa

    empresa = Empresa(
        nombre_legal="Demo Modo Especial Local SRL",
        nombre_fantasia="Demo Local",
        cuit="20999999999",
        activa=True,
    )
    db.add(empresa)
    db.flush()

    config = ConfiguracionEmpresa(
        id_empresa=empresa.id,
        cuit=empresa.cuit,
        nombre_negocio="Demo Modo Especial Local",
        modo_especial_habilitado=True,
        tipo_esquema_empresa=TipoEsquemaEmpresa.ESPECIAL.value,
        perfil_operativo=PLANTILLA_MODO_ESPECIAL_DEMO.model_dump(),
        color_principal="bg-amber-700",
    )
    db.add(config)
    db.commit()
    db.refresh(empresa)
    return empresa


def ensure_user(
    db: Session,
    nombre_usuario: str,
    password: str,
    id_rol: int,
    id_empresa: int,
) -> Usuario:
    existente = db.exec(
        select(Usuario).where(Usuario.nombre_usuario == nombre_usuario)
    ).first()
    if existente:
        return existente

    return admin_manager.crear_usuario(
        db,
        UsuarioCreate(
            nombre_usuario=nombre_usuario,
            password=password,
            id_rol=id_rol,
            id_empresa=id_empresa,
        ),
    )


def ensure_productos(db: Session, id_empresa: int) -> int:
    creados = 0
    for item in PRODUCTOS_DEMO:
        codigo = item["codigo_interno"]
        articulo = db.exec(
            select(Articulo).where(
                Articulo.codigo_interno == codigo,
                Articulo.id_empresa == id_empresa,
            )
        ).first()
        if articulo:
            continue

        articulo = Articulo(
            codigo_interno=codigo,
            descripcion=item["descripcion"],
            precio_venta=item["precio_venta"],
            precio_costo=item["precio_costo"],
            stock_actual=item["stock_actual"],
            stock_minimo=item["stock_minimo"],
            categorias=item["categorias"],
            unidad_compra="unidad",
            unidad_venta="unidad",
            id_empresa=id_empresa,
            activo=True,
        )
        db.add(articulo)
        db.flush()
        db.add(ArticuloCodigo(codigo=item["barcode"], id_articulo=articulo.id))
        creados += 1

    db.commit()
    return creados


def main() -> None:
    print("=== Seed local modo especial ===")
    create_db_and_tables()

    with Session(engine) as db:
        roles = ensure_roles(db)
        empresa = ensure_empresa_modo_especial(db)

        admin = ensure_user(
            db,
            ADMIN_USER,
            ADMIN_PASSWORD,
            roles["Admin"].id,
            empresa.id,
        )
        encargada = ensure_user(
            db,
            ENCARGADA_USER,
            ENCARGADA_PASSWORD,
            roles["Encargada"].id,
            empresa.id,
        )
        productos_nuevos = ensure_productos(db, empresa.id)
        empresa_id = empresa.id
        empresa_nombre = empresa.nombre_fantasia or empresa.nombre_legal

    print()
    print("Listo. Credenciales locales:")
    print(f"  Admin:     {ADMIN_USER} / {ADMIN_PASSWORD}")
    print(f"  Encargada: {ENCARGADA_USER} / {ENCARGADA_PASSWORD}")
    print(f"  Empresa:   {empresa_nombre} (id={empresa_id}, modo especial ON)")
    print(f"  Productos demo nuevos: {productos_nuevos}")
    print()
    print("Frontend: http://localhost:3000")
    print("Login y luego: http://localhost:3000/dashboard/stock")


if __name__ == "__main__":
    main()
