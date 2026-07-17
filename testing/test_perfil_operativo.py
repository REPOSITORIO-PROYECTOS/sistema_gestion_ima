# testing/test_perfil_operativo.py

"""Tests unitarios del resolver de perfil operativo (sin DB)."""

from types import SimpleNamespace

from back.gestion.perfil_operativo_manager import (
    aplicar_fallback_legacy,
    cargar_perfil_desde_json,
)
from back.gestion.plantillas_perfil import PLANTILLAS
from back.schemas.perfil_operativo_schemas import PerfilOperativoEmpresa, TipoEsquemaEmpresa


def _config(**kwargs: object) -> SimpleNamespace:
    defaults = {
        "id_empresa": 1,
        "tipo_esquema_empresa": TipoEsquemaEmpresa.ESTANDAR.value,
        "modo_especial_habilitado": False,
        "perfil_operativo": {},
        "aclaraciones_legales": {},
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_plantilla_retail_estandar_sync_on():
    perfil = PLANTILLAS["retail_estandar"]
    assert perfil.modo_especial is False
    assert perfil.sincronizar_google_sheets is True
    assert perfil.panel_estadisticas_caja is False


def test_plantilla_modo_especial_pos():
    perfil = PLANTILLAS["modo_especial_pos"]
    assert perfil.modo_especial is True
    assert perfil.caja_solo_comprobante is True
    assert perfil.cache_degradado is True
    assert perfil.empresas_transferencia_ids == [35, 36]


def test_fallback_legacy_modo_especial_habilitado():
    config = _config(id_empresa=35, modo_especial_habilitado=True)
    perfil = aplicar_fallback_legacy(config, PerfilOperativoEmpresa())
    assert perfil.modo_especial is True
    assert perfil.sincronizar_google_sheets is False
    assert perfil.caja_solo_comprobante is True


def test_fallback_legacy_bloquear_descuentos_aclaraciones():
    config = _config(
        aclaraciones_legales={"bloquear_descuentos_cajero": "true"},
    )
    perfil = aplicar_fallback_legacy(config, PerfilOperativoEmpresa())
    assert perfil.bloquear_descuentos_cajero is True


def test_cargar_perfil_desde_json_vacio():
    config = _config(perfil_operativo=None)
    perfil = cargar_perfil_desde_json(config)
    assert perfil.modo_especial is False


def test_cargar_perfil_desde_json_valido():
    config = _config(
        perfil_operativo={
            "modo_especial": True,
            "panel_estadisticas_caja": True,
            "empresas_transferencia_ids": [35, 36],
        }
    )
    perfil = cargar_perfil_desde_json(config)
    assert perfil.modo_especial is True
    assert perfil.panel_estadisticas_caja is True


def test_fallback_legacy_mesas_y_balanza():
    config = _config(
        aclaraciones_legales={
            "mesas_enabled": "true",
            "balanza_auto_agregar": "1",
            "balanza_articulo_id": "42",
        },
    )
    perfil = aplicar_fallback_legacy(config, PerfilOperativoEmpresa())
    assert perfil.mesas_habilitado is True
    assert perfil.balanza_auto_agregar is True
    assert perfil.casos_especiales.get("balanza_articulo_id") == "42"


def test_plantilla_demo_transferencias_y_factura():
    from back.gestion.plantillas_perfil import PLANTILLAS

    perfil = PLANTILLAS["modo_especial_demo"]
    assert perfil.empresas_transferencia_ids == [37, 38]
    assert perfil.caja_solo_comprobante is False


def test_cargar_perfil_backfill_cache_degradado_desde_plantilla():
    config = _config(
        tipo_esquema_empresa=TipoEsquemaEmpresa.ESPECIAL.value,
        perfil_operativo={
            "plantilla_origen": "modo_especial_demo",
            "modo_especial": True,
            "panel_estadisticas_caja": True,
        },
    )
    perfil = cargar_perfil_desde_json(config)
    assert perfil.cache_degradado is True
