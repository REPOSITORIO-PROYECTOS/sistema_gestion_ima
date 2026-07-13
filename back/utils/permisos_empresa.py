"""Reglas de permisos por empresa y rol."""

from sqlmodel import Session

from back.gestion import perfil_operativo_manager
from back.modelos import Rol, Usuario
from back.schemas.caja_schemas import ArticuloVendido

ROLES_SIN_DESCUENTO = frozenset({"Cajero", "Vendedora"})


def empresa_tiene_panel_estadisticas_caja(id_empresa: int, db: Session) -> bool:
    return perfil_operativo_manager.empresa_tiene_panel_estadisticas_caja(db, id_empresa)


def usuario_puede_aplicar_descuentos(db: Session, usuario: Usuario) -> bool:
    rol = db.get(Rol, usuario.id_rol) if usuario.id_rol else None
    if not rol or rol.nombre not in ROLES_SIN_DESCUENTO:
        return True
    if not usuario.id_empresa:
        return True
    return not perfil_operativo_manager.empresa_bloquea_descuentos_cajero(db, usuario.id_empresa)


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
