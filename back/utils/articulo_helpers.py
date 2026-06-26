"""Utilidades compartidas para reglas de negocio de artículos."""

from typing import Optional

DESCRIPCIONES_PRECIO_MANUAL = frozenset({"GOLOSINAS", "PANADERIA"})
CODIGOS_PRECIO_MANUAL = frozenset({"000498", "002992"})


def es_articulo_precio_manual(
    descripcion: Optional[str],
    codigo_interno: Optional[str] = None,
) -> bool:
    """Indica si el artículo requiere que el cajero ingrese el precio al vender."""
    if descripcion and descripcion.strip().upper() in DESCRIPCIONES_PRECIO_MANUAL:
        return True
    if codigo_interno and codigo_interno.strip() in CODIGOS_PRECIO_MANUAL:
        return True
    return False
