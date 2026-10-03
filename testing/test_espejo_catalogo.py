# testing/test_espejo_catalogo.py
"""Unit tests del espejo de catálogo 35↔36 (sin DB real). No copia stock."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from back.gestion import espejo_catalogo
from back.modelos import Articulo


def _origen(**overrides):
    base = dict(
        id=1,
        id_empresa=35,
        codigo_interno="ABC",
        descripcion="Coca",
        precio_venta=100.0,
        precio_costo=40.0,
        venta_negocio=100.0,
        tasa_iva=0.21,
        margen_ganancia=0.0,
        auto_actualizar_precio=False,
        precio_manual=False,
        unidad_compra="Unidad",
        unidad_venta="Unidad",
        factor_conversion=1.0,
        ubicacion=None,
        activo=True,
        categorias=None,
        categoria=None,
        codigos=[],
        stock_actual=80.0,
        stock_minimo=5.0,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_peers_35_36():
    assert espejo_catalogo.peers_catalogo(35) == frozenset({36})
    assert espejo_catalogo.peers_catalogo(36) == frozenset({35})
    assert espejo_catalogo.peers_catalogo(37) is None
    assert espejo_catalogo.peers_catalogo(38) is None
    assert espejo_catalogo.peers_catalogo(1) is None


def test_espejar_copia_precio_y_no_toca_stock():
    peer = SimpleNamespace(
        id=9,
        id_empresa=36,
        codigo_interno="ABC",
        descripcion="Coca vieja",
        precio_venta=10.0,
        precio_costo=4.0,
        venta_negocio=10.0,
        tasa_iva=0.21,
        margen_ganancia=0.0,
        auto_actualizar_precio=False,
        precio_manual=False,
        unidad_compra="Unidad",
        unidad_venta="Unidad",
        factor_conversion=1.0,
        ubicacion=None,
        activo=True,
        categorias=None,
        categoria=None,
        codigos=[],
        stock_actual=3.0,
        stock_minimo=1.0,
        id_categoria=None,
    )
    db = MagicMock()
    db.exec.return_value.first.return_value = peer
    db.get.return_value = None

    n = espejo_catalogo.espejar_catalogo_articulo(db, _origen(precio_venta=150.0, venta_negocio=150.0))

    assert n == 1
    assert peer.precio_venta == 150.0
    assert peer.venta_negocio == 150.0
    assert peer.descripcion == "Coca"
    assert peer.stock_actual == 3.0
    assert peer.stock_minimo == 1.0


def test_espejar_no_escribe_si_ya_igual():
    peer = SimpleNamespace(
        id=9,
        id_empresa=36,
        codigo_interno="ABC",
        descripcion="Coca",
        precio_venta=100.0,
        precio_costo=40.0,
        venta_negocio=100.0,
        tasa_iva=0.21,
        margen_ganancia=0.0,
        auto_actualizar_precio=False,
        precio_manual=False,
        unidad_compra="Unidad",
        unidad_venta="Unidad",
        factor_conversion=1.0,
        ubicacion=None,
        activo=True,
        categorias=None,
        categoria=None,
        codigos=[],
        stock_actual=3.0,
        stock_minimo=1.0,
        id_categoria=None,
    )
    db = MagicMock()
    db.exec.return_value.first.return_value = peer

    n = espejo_catalogo.espejar_catalogo_articulo(db, _origen())

    assert n == 0
    assert peer.stock_actual == 3.0
    db.add.assert_not_called()


def test_espejar_copia_barcode_nuevo():
    peer = SimpleNamespace(
        id=9,
        id_empresa=36,
        codigo_interno="ABC",
        descripcion="Coca",
        precio_venta=100.0,
        precio_costo=40.0,
        venta_negocio=100.0,
        tasa_iva=0.21,
        margen_ganancia=0.0,
        auto_actualizar_precio=False,
        precio_manual=False,
        unidad_compra="Unidad",
        unidad_venta="Unidad",
        factor_conversion=1.0,
        ubicacion=None,
        activo=True,
        categorias=None,
        categoria=None,
        codigos=[],
        stock_actual=7.0,
        stock_minimo=2.0,
        id_categoria=None,
    )
    db = MagicMock()
    busqueda_peer = MagicMock()
    busqueda_peer.first.return_value = peer
    sin_conflicto = MagicMock()
    sin_conflicto.first.return_value = None
    db.exec.side_effect = [busqueda_peer, sin_conflicto]
    db.get.return_value = None

    origen = _origen(codigos=[SimpleNamespace(codigo="779000")])
    n = espejo_catalogo.espejar_catalogo_articulo(db, origen)

    assert n == 1
    assert [c.codigo for c in peer.codigos] == ["779000"]
    assert peer.stock_actual == 7.0


def test_espejar_crea_peer_con_stock_cero():
    db = MagicMock()
    db.exec.return_value.first.return_value = None
    db.get.return_value = None

    def _flush():
        for call in db.add.call_args_list:
            obj = call.args[0]
            if isinstance(obj, Articulo) and obj.id is None:
                obj.id = 50

    db.flush.side_effect = _flush

    n = espejo_catalogo.espejar_catalogo_articulo(db, _origen(stock_actual=80.0))

    creados = [call.args[0] for call in db.add.call_args_list if isinstance(call.args[0], Articulo)]
    assert n == 1
    assert len(creados) == 1
    assert creados[0].id_empresa == 36
    assert creados[0].codigo_interno == "ABC"
    assert creados[0].precio_venta == 100.0
    assert creados[0].stock_actual == 0.0
    assert creados[0].stock_minimo is None


def test_empresa_fuera_de_grupo_no_consulta():
    db = MagicMock()
    assert espejo_catalogo.espejar_catalogo_articulo(db, _origen(id_empresa=37)) == 0
    db.exec.assert_not_called()
