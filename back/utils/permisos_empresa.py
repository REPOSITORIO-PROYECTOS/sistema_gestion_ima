"""Reglas de permisos por empresa y rol."""

from typing import Optional

from sqlmodel import Session

from back.modelos import ConfiguracionEmpresa, Rol, Usuario
from back.schemas.caja_schemas import ArticuloVendido

ROLES_SIN_DESCUENTO = frozenset({"Cajero", "Vendedora"})

# La Esquina (35) y FULL24 (36): panel de cajas abiertas en home/navbar.
EMPRESAS_PANEL_ESTADISTICAS_CAJA = frozenset({35, 36})


def empresa_tiene_panel_estadisticas_caja(id_empresa: int) -> bool:
    return id_empresa in EMPRESAS_PANEL_ESTADISTICAS_CAJA


def empresa_bloquea_descuentos_cajero(config: Optional[ConfiguracionEmpresa]) -> bool:
    if not config:
        return False
    aclaraciones = config.aclaraciones_legales or {}
    valor = str(aclaraciones.get("bloquear_descuentos_cajero", "")).lower()
    return valor in {"true", "1", "si", "sí"}


def usuario_puede_aplicar_descuentos(db: Session, usuario: Usuario) -> bool:
    rol = db.get(Rol, usuario.id_rol) if usuario.id_rol else None
    if not rol or rol.nombre not in ROLES_SIN_DESCUENTO:
        return True
    config = db.get(ConfiguracionEmpresa, usuario.id_empresa)
    return not empresa_bloquea_descuentos_cajero(config)


def validar_descuentos_permitidos(
    db: Session,
    usuario: Usuario,
    articulos_vendidos: list[ArticuloVendido],
    descuento_total: float = 0.0,
) -> None:
    if usuario_puede_aplicar_descuentos(db, usuario):
        return
    if (descuento_total or 0) > 0:
        raise ValueError("Su rol no puede aplicar descuentos en esta empresa.")
    for item in articulos_vendidos:
        if (item.descuento_especifico or 0) > 0 or (item.descuento_especifico_por or 0) > 0:
            raise ValueError("Su rol no puede aplicar descuentos en esta empresa.")
