"""
Tests de alineación de columnas MOVIMIENTOS (sin Google Sheets en vivo).
"""
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from back.modelos import ConfiguracionEmpresa
from back.utils.tablas_handler import TablasHandler

FIXTURES_PATH = Path(__file__).parent / "fixtures" / "movimientos_encabezados_swing.json"


def _engine_memoria():
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _handler_sin_sheets() -> TablasHandler:
    engine = _engine_memoria()
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(
            ConfiguracionEmpresa(
                id_empresa=1,
                cuit="20123456789",
                link_google_sheets="sheet_id_prueba_unit_test",
                nombre_negocio="Swing Test",
            )
        )
        db.commit()
        handler = TablasHandler(id_empresa=1, db=db)
    return handler


def _cargar_fixture() -> Dict[str, Any]:
    return json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))


def test_fila_swing_21_columnas_desde_a():
    """Swing tiene 21 columnas (A:U); caja llena A:P y deja Q:U vacías para pedidos."""
    handler = _handler_sin_sheets()
    fixture = _cargar_fixture()
    enc = TablasHandler.encabezados_movimientos_swing()
    fila, mapa = handler._construir_fila_movimiento_desde_columna_a(
        enc, fixture["payload_ejemplo"], id_movimiento="test1234"
    )

    assert len(fila) == 21
    assert fila[0] == "test1234"
    assert fila[1] == "0"
    assert fila[4] == "cajero_swing"
    assert fila[13].startswith("$")
    assert fila[16] == ""
    assert fila[20] == ""
    assert mapa["monto"] == fila[13]


def test_encabezados_swing_mapean_campos_criticos():
    fixture = _cargar_fixture()
    handler = _handler_sin_sheets()
    payload = fixture["payload_ejemplo"]

    diag = handler.diagnosticar_fila_movimiento(payload)
    por_clave = {item["clave_normalizada"]: item for item in diag["detalle"]}

    assert por_clave["id_movimiento"]["valor"]
    assert por_clave["id_cliente"]["valor"] == "0"
    assert por_clave["id_ingresos"]["valor"] == "99999"
    assert por_clave["repartidor"]["valor"] == "cajero_swing"
    assert por_clave["fecha_y_hora_entrega"]["valor"]
    assert por_clave["cliente"]["valor"] == "cliente final"
    assert por_clave["tipo_de_movimiento"]["valor"] == "[ticket] Venta en EFECTIVO"
    assert por_clave["descripcion"]["valor"] == "Venta de prueba"
    assert por_clave["monto"]["valor"].startswith("$")

    # Q:U son solo pedidos; caja las deja vacías a propósito.
    columnas_solo_pedidos = {"ID Pedido", "Firma", "Estado", "Fecha de la Deuda", "Hash Sync"}
    sin_mapeo_titulados = [h for h in diag["sin_mapeo"] if h.strip()]
    assert set(sin_mapeo_titulados) == columnas_solo_pedidos, (
        f"Sin mapeo inesperado: {sin_mapeo_titulados}"
    )


def test_alias_fecha_y_hora_importe_cajero():
    handler = _handler_sin_sheets()
    encabezados = ["Fecha y Hora", "Importe", "Cajero", "Tipo Movimiento"]
    payload = {
        "Repartidor": "cajero_x",
        "Tipo_movimiento": "VENTA",
        "monto": 100,
    }
    diag = handler.diagnosticar_fila_movimiento(
        payload, encabezados=encabezados, usar_layout_fijo=False
    )
    valores = {item["clave_normalizada"]: item["valor"] for item in diag["detalle"]}

    assert valores["fecha_y_hora"]
    assert valores["importe"].startswith("$")
    assert valores["cajero"] == "cajero_x"
    assert valores["tipo_movimiento"] == "VENTA"


def test_fila_misma_longitud_que_encabezados():
    fixture = _cargar_fixture()
    handler = _handler_sin_sheets()
    encabezados = fixture["encabezados"]
    fila, _, _ = handler._construir_fila_movimiento(encabezados, fixture["payload_ejemplo"])
    assert len(fila) == 21
    assert len(fila) == len(encabezados)


def test_fallback_encabezados_cubre_layout_estandar():
    handler = _handler_sin_sheets()
    encabezados = TablasHandler.encabezados_movimientos_fallback()
    fila, mapa, sin_mapeo = handler._construir_fila_movimiento(
        encabezados,
        {"Repartidor": "u", "Tipo_movimiento": "T", "monto": 1, "descripcion": "d"},
    )
    assert len(fila) == 21
    assert mapa["repartidor"] == "u"
    assert set(sin_mapeo) == {
        "ID Pedido", "Firma", "Estado", "Fecha de la Deuda", "Hash Sync"
    }


def test_codigo_produccion_escribe_desde_columna_a_ancho_completo():
    fuente = (_ROOT / "back" / "utils" / "tablas_handler.py").read_text(encoding="utf-8")
    assert "_escribir_fila_movimientos_desde_a" in fuente
    assert "encabezados_movimientos_swing" in fuente
    assert "_construir_fila_movimiento_desde_columna_a" in fuente
    assert "_obtener_siguiente_fila_hoja" in fuente
    assert "row_count + 1" not in fuente.split("_escribir_fila_movimientos_desde_a")[1].split("def _construir_fila_movimiento")[0]


if __name__ == "__main__":
    test_fila_swing_21_columnas_desde_a()
    test_encabezados_swing_mapean_campos_criticos()
    test_alias_fecha_y_hora_importe_cajero()
    test_fila_misma_longitud_que_encabezados()
    test_fallback_encabezados_cubre_layout_estandar()
    test_codigo_produccion_escribe_desde_columna_a_ancho_completo()
    print("OK: todos los tests de movimientos_columnas pasaron.")
