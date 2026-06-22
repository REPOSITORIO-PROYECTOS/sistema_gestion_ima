"""
Tests de ingresos/egresos manuales: DB local + payload encolado para MOVIMIENTOS.
"""
import os
import sys
from datetime import datetime, timezone

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from back.gestion.caja import registro_caja as registro_module
from back.gestion.sync_nube_queue_manager import OPERACION_REGISTRAR_MOVIMIENTO
from back.modelos import (
    Articulo,
    CajaMovimiento,
    CajaSesion,
    Empresa,
    Rol,
    SyncNubePendiente,
    Usuario,
)
from back.utils.tablas_handler import TablasHandler


def _engine_memoria():
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _crear_datos_base(db: Session):
    rol = Rol(nombre="Cajero")
    db.add(rol)
    db.commit()
    db.refresh(rol)

    empresa = Empresa(
        nombre_legal="Test SA",
        nombre_fantasia="Test",
        cuit="20123456789",
        activa=True,
        creada_en=datetime.now(timezone.utc),
    )
    db.add(empresa)
    db.commit()
    db.refresh(empresa)

    usuario = Usuario(
        nombre_usuario="cajero_test",
        password_hash="hash",
        activo=True,
        creado_en=datetime.now(timezone.utc),
        id_rol=rol.id,
        id_empresa=empresa.id,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    sesion = CajaSesion(
        fecha_apertura=datetime.now(timezone.utc),
        saldo_inicial=100.0,
        estado="ABIERTA",
        id_usuario_apertura=usuario.id,
        id_empresa=empresa.id,
    )
    db.add(sesion)
    db.commit()
    db.refresh(sesion)

    return usuario, sesion


def _registrar_manual(db: Session, usuario: Usuario, sesion: CajaSesion, tipo: str, monto: float, concepto: str):
    mov = registro_module.registrar_ingreso_egreso(
        db=db,
        usuario_actual=usuario,
        id_sesion_caja=sesion.id,
        concepto=concepto,
        monto=monto,
        tipo=tipo,
        metodo_pago="EFECTIVO",
    )
    db.commit()
    db.refresh(mov)
    return mov


def test_ingreso_crea_movimiento_y_encola_sync():
    engine = _engine_memoria()
    SQLModel.metadata.create_all(engine)

    with Session(engine) as db:
        usuario, sesion = _crear_datos_base(db)
        mov = _registrar_manual(db, usuario, sesion, "INGRESO", 250.0, "Aporte caja chica")

        assert mov.id is not None
        assert mov.tipo == "INGRESO"
        assert mov.monto == 250.0
        assert mov.concepto == "Aporte caja chica"

        pendientes = db.exec(select(SyncNubePendiente)).all()
        assert len(pendientes) == 1
        item = pendientes[0]
        assert item.operacion == OPERACION_REGISTRAR_MOVIMIENTO
        assert item.id_venta is None
        assert item.payload["Tipo_movimiento"] == "[INGRESO] en EFECTIVO"
        assert item.payload["descripcion"] == "Aporte caja chica"
        assert item.payload["monto"] == 250.0
        assert item.payload["Repartidor"] == "cajero_test"
        assert item.payload["id_ingresos"] == str(mov.id)


def test_egreso_tipo_correcto_en_payload():
    engine = _engine_memoria()
    SQLModel.metadata.create_all(engine)

    with Session(engine) as db:
        usuario, sesion = _crear_datos_base(db)
        mov = _registrar_manual(db, usuario, sesion, "EGRESO", 80.0, "Compra insumos")

        assert mov.tipo == "EGRESO"

        item = db.exec(select(SyncNubePendiente)).first()
        assert item is not None
        assert item.payload["Tipo_movimiento"] == "[EGRESO] en EFECTIVO"
        assert item.payload["descripcion"] == "Compra insumos"
        assert item.payload["monto"] == 80.0


def test_payload_manual_mapea_columnas_swing():
    engine = _engine_memoria()
    SQLModel.metadata.create_all(engine)

    with Session(engine) as db:
        usuario, sesion = _crear_datos_base(db)
        mov = _registrar_manual(db, usuario, sesion, "INGRESO", 100.0, "Test columnas")

        item = db.exec(select(SyncNubePendiente)).first()
        handler = TablasHandler(id_empresa=usuario.id_empresa, db=db)
        diag = handler.diagnosticar_fila_movimiento(item.payload, id_movimiento="movtest01")

        por_clave = {d["clave_normalizada"]: d["valor"] for d in diag["detalle"]}
        assert por_clave["tipo_de_movimiento"] == "[INGRESO] en EFECTIVO"
        assert por_clave["descripcion"] == "Test columnas"
        assert por_clave["repartidor"] == "cajero_test"
        assert por_clave["monto"].startswith("$")
        assert por_clave["id_ingresos"] == str(mov.id)
        assert len(diag["fila"]) == 21


def test_monto_invalido_no_crea_movimiento():
    engine = _engine_memoria()
    SQLModel.metadata.create_all(engine)

    with Session(engine) as db:
        usuario, sesion = _crear_datos_base(db)
        try:
            registro_module.registrar_ingreso_egreso(
                db=db,
                usuario_actual=usuario,
                id_sesion_caja=sesion.id,
                concepto="Invalido",
                monto=0,
                tipo="INGRESO",
                metodo_pago="EFECTIVO",
            )
            assert False, "Debía fallar con monto <= 0"
        except ValueError:
            pass

        movs = db.exec(select(CajaMovimiento)).all()
        pendientes = db.exec(select(SyncNubePendiente)).all()
        assert len(movs) == 0
        assert len(pendientes) == 0


def run_all_tests():
    test_ingreso_crea_movimiento_y_encola_sync()
    print("OK: test_ingreso_crea_movimiento_y_encola_sync")
    test_egreso_tipo_correcto_en_payload()
    print("OK: test_egreso_tipo_correcto_en_payload")
    test_payload_manual_mapea_columnas_swing()
    print("OK: test_payload_manual_mapea_columnas_swing")
    test_monto_invalido_no_crea_movimiento()
    print("OK: test_monto_invalido_no_crea_movimiento")
    print("Todos los tests de ingreso/egreso pasaron.")


if __name__ == "__main__":
    run_all_tests()
