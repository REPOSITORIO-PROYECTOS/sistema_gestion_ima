"""El principal queda primero y un código no se repite en el mismo producto."""

import pytest

from back.gestion.modo_especial_manager import _asignar_barcodes
from back.utils.articulo_helpers import listar_codigos_ordenados


class _Codigo:
    def __init__(self, codigo: str, orden: int = 0) -> None:
        self.codigo = codigo
        self.orden = orden
        self.id_articulo = 1


class _Articulo:
    def __init__(self) -> None:
        self.id = 1
        self.id_empresa = 1
        self.codigos = [_Codigo("ALT-2", 0), _Codigo("PRINCIPAL", 0)]


def test_reasigna_el_principal_sin_tocar_la_base():
    articulo = _Articulo()
    _asignar_barcodes(None, articulo, ["PRINCIPAL", "ALT-2"])  # type: ignore[arg-type]
    ordenados = [codigo.codigo for codigo in listar_codigos_ordenados(articulo.codigos)]
    assert ordenados == ["PRINCIPAL", "ALT-2"]
    principal = next(codigo for codigo in articulo.codigos if codigo.codigo == "PRINCIPAL")
    assert principal.orden == 0


def test_rechaza_el_mismo_codigo_dos_veces_en_la_lista():
    articulo = _Articulo()
    with pytest.raises(ValueError, match="repetido"):
        _asignar_barcodes(None, articulo, ["PRINCIPAL", "PRINCIPAL"])  # type: ignore[arg-type]
