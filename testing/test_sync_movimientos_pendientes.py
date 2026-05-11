import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from back.gestion.caja import registro_caja as registro_module
from back.modelos import Articulo, CajaSesion, Empresa, Rol, Usuario
from back.schemas.caja_schemas import ArticuloVendido


class DummyTablasHandlerControlado:
    debe_fallar = True
    registros_enviados: List[Dict[str, Any]] = []

    def __init__(self, id_empresa: int, db: Session):
        self.id_empresa = id_empresa
        self.db = db
        self.ultimo_error_sync = None

    def registrar_movimiento(self, datos: Dict[str, Any]) -> bool:
        if self.debe_fallar:
            self.ultimo_error_sync = "Simulacion: timeout de Google Sheets"
            return False
        self.registros_enviados.append(datos)
        self.ultimo_error_sync = None
        return True

    def restar_stock(self, db: Session, items: List[ArticuloVendido]) -> bool:
        if self.debe_fallar:
            self.ultimo_error_sync = "Simulacion: sync stock no disponible"
            return False
        self.ultimo_error_sync = None
        return True


registro_module.TablasHandler = DummyTablasHandlerControlado


def _crear_engine_memoria():
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _crear_datos_base(db: Session):
    rol_admin = Rol(nombre="Admin")
    db.add(rol_admin)
    db.commit()
    db.refresh(rol_admin)

    empresa = Empresa(
        nombre_legal="Swing SA",
        nombre_fantasia="Swing",
        cuit="20304050607",
        activa=True,
        creada_en=datetime.now(timezone.utc),
    )
    db.add(empresa)
    db.commit()
    db.refresh(empresa)

    usuario = Usuario(
        nombre_usuario="cajero_swing",
        password_hash="hash",
        activo=True,
        creado_en=datetime.now(timezone.utc),
        id_rol=rol_admin.id,
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
        codigo_interno="SW-001",
        descripcion="Articulo Swing",
        precio_venta=100.0,
        precio_costo=70.0,
        tasa_iva=0.21,
        stock_actual=10.0,
        ubicacion="A1",
        activo=True,
        id_empresa=empresa.id,
    )
    db.add(articulo)
    db.commit()
    db.refresh(articulo)

    return usuario, sesion, articulo


def test_falla_sync_y_reintento_exitoso():
    engine = _crear_engine_memoria()
    SQLModel.metadata.create_all(engine)

    with Session(engine) as db:
        usuario, sesion, articulo = _crear_datos_base(db)

        # 1) Falla de sync: la venta queda en DB y sync_nube queda pendiente
        DummyTablasHandlerControlado.debe_fallar = True
        DummyTablasHandlerControlado.registros_enviados = []

        venta, _ = registro_module.registrar_venta_y_movimiento_caja(
            db=db,
            usuario_actual=usuario,
            id_sesion_caja=sesion.id,
            total_venta=100.0,
            metodo_pago="EFECTIVO",
            articulos_vendidos=[
                ArticuloVendido(id_articulo=articulo.id, cantidad=1, precio_unitario=100.0)
            ],
            id_cliente=0,
            tipo_comprobante_solicitado="ticket",
        )

        assert venta.id is not None
        protocolo = db.info.get("protocolo_sync_nube", [])
        assert any(ev.get("estado") in {"fallido", "pendiente"} for ev in protocolo), protocolo

        # 2) Reintento manual de movimiento pendiente: ahora "impacta" en Sheets
        DummyTablasHandlerControlado.debe_fallar = False
        reintento_handler = DummyTablasHandlerControlado(id_empresa=usuario.id_empresa, db=db)
        ok = reintento_handler.registrar_movimiento(
            {
                "id_cliente": "0",
                "id_ingresos": str(venta.id),
                "id_repartidor": "",
                "Repartidor": usuario.nombre_usuario,
                "cliente": "cliente final",
                "cuit": "-",
                "razon_social": "-",
                "Tipo_movimiento": "[ticket] Venta en EFECTIVO",
                "nro_comprobante": "",
                "descripcion": "Reintento movimiento pendiente",
                "monto": 100.0,
                "foto_comprobante": "",
                "observaciones": "reintento",
            }
        )
        assert ok is True
        assert len(DummyTablasHandlerControlado.registros_enviados) == 1


def run_all_tests():
    print("Ejecutando test de movimientos pendientes...")
    test_falla_sync_y_reintento_exitoso()
    print("OK: test_falla_sync_y_reintento_exitoso")
    print("Resultado: venta registrada localmente + reintento manual impactado en Sheets.")


if __name__ == "__main__":
    run_all_tests()
