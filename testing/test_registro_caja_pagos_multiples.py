# test_registro_caja_pagos_multiples.py

import sys
import os
from datetime import datetime, timezone

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from sqlmodel import Session, create_engine
from sqlalchemy.pool import StaticPool

from back.modelos import SQLModel, Empresa, Usuario, Articulo, CajaSesion
from back.schemas.caja_schemas import ArticuloVendido, PagoMultiple
from back.gestion.caja import registro_caja as registro_module


class DummyTablasHandler:
    def __init__(self, id_empresa: int, db: Session):
        self.id_empresa = id_empresa
        self.db = db

    def registrar_movimiento(self, datos):
        return True

    def restar_stock(self, db, items):
        return True


registro_module.TablasHandler = DummyTablasHandler


TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

SQLModel.metadata.create_all(engine)


_SUFFIX_COUNTER = 0


def _next_suffix() -> str:
    global _SUFFIX_COUNTER
    _SUFFIX_COUNTER += 1
    return str(_SUFFIX_COUNTER)


def crear_datos_prueba(db: Session):
    suffix = _next_suffix()
    empresa = Empresa(
        nombre_legal=f"Empresa Test {suffix}",
        nombre_fantasia="Test Corp",
        cuit=f"2030405060{suffix}",
        activa=True,
        creada_en=datetime.now(timezone.utc),
    )
    db.add(empresa)
    db.commit()
    db.refresh(empresa)

    usuario = Usuario(
        nombre_usuario=f"test_user_{suffix}",
        password_hash="hashed_password",
        activo=True,
        creado_en=datetime.now(timezone.utc),
        id_rol=1,
        id_empresa=empresa.id,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    sesion = CajaSesion(
        fecha_apertura=datetime.now(timezone.utc),
        saldo_inicial=0.0,
        estado="ABIERTA",
        id_usuario_apertura=usuario.id,
        id_empresa=empresa.id,
    )
    db.add(sesion)
    db.commit()
    db.refresh(sesion)

    articulo = Articulo(
        codigo_interno="TEST001",
        descripcion="Producto Test",
        precio_venta=50.0,
        tasa_iva=0.21,
        precio_costo=40.0,
        stock_actual=50.0,
        ubicacion="Estante A1",
        activo=True,
        id_empresa=empresa.id,
    )
    db.add(articulo)
    db.commit()
    db.refresh(articulo)

    return empresa, usuario, sesion, articulo


def test_pagos_multiples_ok():
    with Session(engine) as db:
        _, usuario, sesion, articulo = crear_datos_prueba(db)

        articulos_vendidos = [
            ArticuloVendido(
                id_articulo=articulo.id,
                cantidad=2,
                precio_unitario=50.0,
            )
        ]
        pagos = [
            PagoMultiple(metodo_pago="efectivo", monto=60.0),
            PagoMultiple(metodo_pago="transferencia", monto=40.0),
        ]

        venta, movimientos = registro_module.registrar_venta_y_movimientos_caja_multiples(
            db=db,
            usuario_actual=usuario,
            id_sesion_caja=sesion.id,
            total_venta=100.0,
            pagos_multiples=pagos,
            articulos_vendidos=articulos_vendidos,
            id_cliente=0,
            tipo_comprobante_solicitado="ticket",
        )

        assert venta.id_cliente is None
        assert len(movimientos) == 2
        assert {m.monto for m in movimientos} == {60.0, 40.0}
        assert {m.metodo_pago for m in movimientos} == {"EFECTIVO", "TRANSFERENCIA"}

        articulo_actualizado = db.get(Articulo, articulo.id)
        assert articulo_actualizado.stock_actual == 48.0


def test_pagos_multiples_suma_incorrecta():
    with Session(engine) as db:
        _, usuario, sesion, articulo = crear_datos_prueba(db)

        articulos_vendidos = [
            ArticuloVendido(
                id_articulo=articulo.id,
                cantidad=1,
                precio_unitario=50.0,
            )
        ]
        pagos = [
            PagoMultiple(metodo_pago="efectivo", monto=30.0),
            PagoMultiple(metodo_pago="transferencia", monto=10.0),
        ]

        try:
            registro_module.registrar_venta_y_movimientos_caja_multiples(
                db=db,
                usuario_actual=usuario,
                id_sesion_caja=sesion.id,
                total_venta=50.0,
                pagos_multiples=pagos,
                articulos_vendidos=articulos_vendidos,
                id_cliente=0,
                tipo_comprobante_solicitado="ticket",
            )
            raise AssertionError("Se esperaba ValueError por suma de pagos incorrecta.")
        except ValueError:
            pass


def run_all_tests():
    print("Ejecutando pruebas de pagos multiples...")
    test_pagos_multiples_ok()
    print("OK: test_pagos_multiples_ok")
    test_pagos_multiples_suma_incorrecta()
    print("OK: test_pagos_multiples_suma_incorrecta")


if __name__ == "__main__":
    run_all_tests()
