# testing/test_estadisticas_generales.py
"""Tests unitarios de helpers de período AR y schema de secciones."""

from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.dialects import mysql

from back.gestion.caja.consultas_caja import _rango_dia_ar_utc_naive, _rango_mes_ar_utc_naive
from back.modelos import Articulo, Categoria, Venta, VentaDetalle
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


def test_query_top_categorias_sql_no_duplica_alias():
    """Regression: select_from(Articulo) evita 'Not unique table/alias: categorias'."""
    monto_linea = (
        VentaDetalle.cantidad * VentaDetalle.precio_unitario
        - func.coalesce(VentaDetalle.descuento_aplicado, 0.0)
    )
    nombre_cat = func.coalesce(Categoria.nombre, "Sin categoría")
    stmt = (
        select(
            nombre_cat.label("categoria"),
            func.coalesce(func.sum(VentaDetalle.cantidad), 0.0),
            func.coalesce(func.sum(monto_linea), 0.0),
        )
        .select_from(Articulo)
        .join(VentaDetalle, VentaDetalle.id_articulo == Articulo.id)
        .join(Venta, Venta.id == VentaDetalle.id_venta)
        .outerjoin(Categoria, Categoria.id == Articulo.id_categoria)
        .group_by(nombre_cat)
    )
    sql = str(stmt.compile(dialect=mysql.dialect(), compile_kwargs={"literal_binds": False})).lower()
    assert "from articulos" in sql
    assert "from categorias" not in sql
    assert sql.count("join categorias") == 1
