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
    assert perfil.panel_estadisticas_caja is True
    assert perfil.panel_estadisticas_secciones.alertas_diferencias_caja is True
    assert perfil.panel_estadisticas_secciones.kpis_periodo is True
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
    assert perfil.factura_auto_transferencia_pos is True
    assert perfil.panel_estadisticas_caja is True
    assert perfil.panel_estadisticas_secciones.top_categorias is True
    assert perfil.panel_estadisticas_secciones.ranking_vendedores is True


def test_cargar_perfil_sin_secciones_rellena_defaults_si_panel_on():
    config = _config(
        perfil_operativo={
            "plantilla_origen": "modo_especial_demo",
            "modo_especial": True,
            "panel_estadisticas_caja": True,
        }
    )
    perfil = cargar_perfil_desde_json(config)
    assert perfil.panel_estadisticas_secciones.alertas_stock is True
    assert perfil.panel_estadisticas_secciones.medios_pago is True


def test_secciones_por_establecimiento_segun_sucursales():
    from back.gestion.perfil_operativo_manager import _secciones_para_empresa
    from back.schemas.perfil_operativo_schemas import PerfilOperativoEmpresa

    una = PerfilOperativoEmpresa(empresas_transferencia_ids=[39])
    assert _secciones_para_empresa(una).por_establecimiento is False

    multi = PerfilOperativoEmpresa(empresas_transferencia_ids=[35, 36])
    assert _secciones_para_empresa(multi).por_establecimiento is True


def test_autofactura_transferencia_pos_fuerza_factura_b():
    from back.gestion.perfil_operativo_manager import (
        aplicar_autofactura_transferencia_pos_a_request,
    )
    from back.schemas.perfil_operativo_schemas import PerfilOperativoResuelto

    perfil = PerfilOperativoResuelto(
        factura_auto_transferencia_pos=True,
        caja_puede_facturar=True,
        facturacion_afip_habilitada=True,
    )
    quiere, tipo = aplicar_autofactura_transferencia_pos_a_request(
        perfil,
        quiere_factura=False,
        tipo_comprobante_solicitado="recibo",
        metodo_pago="TRANSFERENCIA",
        pagos_multiples=None,
        cuit_receptor="0",
    )
    assert quiere is True
    assert tipo == "factura_b"


def test_autofactura_transferencia_pos_no_pisa_remito():
    from back.gestion.perfil_operativo_manager import (
        aplicar_autofactura_transferencia_pos_a_request,
    )
    from back.schemas.perfil_operativo_schemas import PerfilOperativoResuelto

    perfil = PerfilOperativoResuelto(
        factura_auto_transferencia_pos=True,
        caja_puede_facturar=True,
    )
    quiere, tipo = aplicar_autofactura_transferencia_pos_a_request(
        perfil,
        quiere_factura=False,
        tipo_comprobante_solicitado="remito",
        metodo_pago="bancario",
        pagos_multiples=None,
    )
    assert quiere is False
    assert tipo == "remito"


def test_autofactura_efectivo_no_dispara():
    from back.gestion.perfil_operativo_manager import (
        aplicar_autofactura_transferencia_pos_a_request,
    )
    from back.schemas.perfil_operativo_schemas import PerfilOperativoResuelto

    perfil = PerfilOperativoResuelto(
        factura_auto_transferencia_pos=True,
        caja_puede_facturar=True,
    )
    quiere, tipo = aplicar_autofactura_transferencia_pos_a_request(
        perfil,
        quiere_factura=False,
        tipo_comprobante_solicitado="recibo",
        metodo_pago="EFECTIVO",
        pagos_multiples=None,
    )
    assert quiere is False
    assert tipo == "recibo"


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
