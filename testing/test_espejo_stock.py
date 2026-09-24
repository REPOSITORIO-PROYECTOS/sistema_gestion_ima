# testing/test_espejo_stock.py
"""Unit tests del espejo de stock 37↔38 (sin DB real)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from back.gestion.stock import espejo_stock


def test_peers_37_38():
    assert espejo_stock.peers_espejo(37) == frozenset({38})
    assert espejo_stock.peers_espejo(38) == frozenset({37})
    assert espejo_stock.peers_espejo(35) is None
    assert espejo_stock.peers_espejo(1) is None


def test_empresas_en_mismo_espejo():
    assert espejo_stock.empresas_en_mismo_espejo(37, 38) is True
    assert espejo_stock.empresas_en_mismo_espejo(38, 37) is True
    assert espejo_stock.empresas_en_mismo_espejo(35, 36) is False
    assert espejo_stock.empresas_en_mismo_espejo(37, 35) is False


def test_espejar_copia_stock_a_peer():
    peer = SimpleNamespace(id=2, id_empresa=38, codigo_interno="ABC", stock_actual=0.0)
    db = MagicMock()
    db.exec.return_value.first.return_value = peer

    origen = SimpleNamespace(id=1, id_empresa=37, codigo_interno="ABC", stock_actual=42.5)
    n = espejo_stock.espejar_stock_articulo(db, origen)

    assert n == 1
    assert peer.stock_actual == 42.5
    db.add.assert_called_once_with(peer)


def test_espejar_no_toca_si_ya_igual():
    peer = SimpleNamespace(id=2, id_empresa=38, codigo_interno="ABC", stock_actual=10.0)
    db = MagicMock()
    db.exec.return_value.first.return_value = peer

    origen = SimpleNamespace(id=1, id_empresa=37, codigo_interno="ABC", stock_actual=10.0)
    n = espejo_stock.espejar_stock_articulo(db, origen)

    assert n == 0
    db.add.assert_not_called()


def test_espejar_sin_peer_no_falla():
    db = MagicMock()
    db.exec.return_value.first.return_value = None
    origen = SimpleNamespace(id=1, id_empresa=37, codigo_interno="XYZ", stock_actual=5.0)
    assert espejo_stock.espejar_stock_articulo(db, origen) == 0


def test_espejar_empresa_fuera_de_grupo():
    db = MagicMock()
    origen = SimpleNamespace(id=1, id_empresa=35, codigo_interno="ABC", stock_actual=9.0)
    assert espejo_stock.espejar_stock_articulo(db, origen) == 0
    db.exec.assert_not_called()
