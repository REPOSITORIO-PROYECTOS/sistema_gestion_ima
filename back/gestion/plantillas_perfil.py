# back/gestion/plantillas_perfil.py

from back.schemas.perfil_operativo_schemas import PerfilOperativoEmpresa

PLANTILLA_RETAIL_ESTANDAR = PerfilOperativoEmpresa(
    plantilla_origen="retail_estandar",
    modo_especial=False,
    sincronizar_google_sheets=True,
    caja_solo_comprobante=False,
    caja_permitir_remito_presupuesto=False,
    panel_estadisticas_caja=False,
    mesas_habilitado=False,
    bloquear_descuentos_cajero=False,
    empresas_transferencia_ids=[],
)

PLANTILLA_MODO_ESPECIAL_POS = PerfilOperativoEmpresa(
    plantilla_origen="modo_especial_pos",
    modo_especial=True,
    sincronizar_google_sheets=False,
    caja_solo_comprobante=True,
    caja_permitir_remito_presupuesto=False,
    panel_estadisticas_caja=True,
    mesas_habilitado=False,
    bloquear_descuentos_cajero=True,
    cache_degradado=True,
    empresas_transferencia_ids=[35, 36],
)

PLANTILLA_MODO_ESPECIAL_DEMO = PerfilOperativoEmpresa(
    plantilla_origen="modo_especial_demo",
    modo_especial=True,
    sincronizar_google_sheets=False,
    caja_solo_comprobante=False,
    caja_permitir_remito_presupuesto=False,
    panel_estadisticas_caja=True,
    mesas_habilitado=False,
    bloquear_descuentos_cajero=True,
    cache_degradado=True,
    empresas_transferencia_ids=[37, 38],
)

PLANTILLAS: dict[str, PerfilOperativoEmpresa] = {
    "retail_estandar": PLANTILLA_RETAIL_ESTANDAR,
    "modo_especial_pos": PLANTILLA_MODO_ESPECIAL_POS,
    "modo_especial_demo": PLANTILLA_MODO_ESPECIAL_DEMO,
}

DESCRIPCIONES_PLANTILLAS: dict[str, tuple[str, str]] = {
    "retail_estandar": (
        "Retail estándar IMA",
        "Sync Google Sheets, factura AFIP si corresponde, sin modo especial.",
    ),
    "modo_especial_pos": (
        "Modo especial POS",
        "La Esquina / FULL24: catálogo manual, solo comprobante, panel estadísticas.",
    ),
    "modo_especial_demo": (
        "Modo especial demo",
        "Demos de-campo / La Esquina 2: catálogo manual, factura AFIP en caja si bóveda OK, transferencias demo.",
    ),
}
