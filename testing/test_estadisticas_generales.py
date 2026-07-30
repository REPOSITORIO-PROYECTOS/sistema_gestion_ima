# testing/test_estadisticas_generales.py
"""Tests unitarios de helpers de período AR y schema de secciones."""

from datetime import date, datetime, timezone

from back.gestion.caja.consultas_caja import _rango_dia_ar_utc_naive, _rango_mes_ar_utc_naive
from back.schemas.perfil_operativo_schemas import PanelEstadisticasSecciones


def test_rango_dia_ar_cruza_utc():
    # 2026-07-30 00:00 AR = 2026-07-30 03:00 UTC
    desde, hasta = _rango_dia_ar_utc_naive(date(2026, 7, 30))
    assert desde == datetime(2026, 7, 30, 3, 0, 0)
    assert hasta == datetime(2026, 7, 31, 3, 0, 0)
    assert desde.tzinfo is None
    assert hasta.tzinfo is None


def test_rango_mes_ar():
    desde, hasta = _rango_mes_ar_utc_naive(2026, 7)
    assert desde == datetime(2026, 7, 1, 3, 0, 0)
    assert hasta == datetime(2026, 8, 1, 3, 0, 0)


def test_panel_secciones_defaults_todas_on():
    s = PanelEstadisticasSecciones()
    assert s.kpis_periodo is True
    assert s.alertas_diferencias_caja is True
    assert s.ranking_vendedores is True


def test_panel_secciones_parcial_off():
    s = PanelEstadisticasSecciones(alertas_diferencias_caja=False, medios_pago=False)
    assert s.alertas_diferencias_caja is False
    assert s.medios_pago is False
    assert s.alertas_stock is True
