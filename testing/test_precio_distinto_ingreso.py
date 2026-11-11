"""El ingreso masivo no trata un precio igual al vigente como un cambio."""

from back.gestion.modo_especial_manager import precio_distinto


def test_precio_igual_no_es_cambio():
    assert precio_distinto(6200, 6200) is False
    assert precio_distinto(6200.0, 6200.0004) is False
    assert precio_distinto(None, 0) is False


def test_precio_distinto_si_cambia():
    assert precio_distinto(3500, 6200) is True
    assert precio_distinto(None, 10) is True
