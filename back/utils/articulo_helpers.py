"""Utilidades compartidas para reglas de negocio de artículos."""

from typing import Optional

from sqlmodel import Session, select

from back.modelos import Articulo, ArticuloCodigo

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


def obtener_codigo_barras_articulo(
    db: Session,
    codigo: str,
    id_articulo: int,
) -> Optional[ArticuloCodigo]:
    return db.exec(
        select(ArticuloCodigo).where(
            ArticuloCodigo.codigo == codigo,
            ArticuloCodigo.id_articulo == id_articulo,
        )
    ).first()


def articulo_con_barcode_en_empresa(
    db: Session,
    codigo: str,
    id_articulo: int,
    id_empresa: int,
) -> Optional[Articulo]:
    """Devuelve el artículo que ya tiene ese barcode en la misma empresa (excluye id_articulo)."""
    return db.exec(
        select(Articulo)
        .join(ArticuloCodigo, ArticuloCodigo.id_articulo == Articulo.id)
        .where(
            ArticuloCodigo.codigo == codigo,
            Articulo.id_empresa == id_empresa,
            ArticuloCodigo.id_articulo != id_articulo,
        )
    ).first()


def conflicto_barcode_en_empresa(
    db: Session,
    codigo: str,
    id_articulo: int,
    id_empresa: int,
) -> bool:
    """True si el barcode ya está asignado a otro artículo de la misma empresa."""
    return articulo_con_barcode_en_empresa(db, codigo, id_articulo, id_empresa) is not None


def mensaje_barcode_duplicado(codigo: str, otro: Articulo) -> str:
    ref = otro.codigo_interno or str(otro.id)
    nombre = (otro.descripcion or "").strip()
    if nombre:
        return (
            f"El código de barras '{codigo}' está duplicado: "
            f"ya lo usa el producto {ref} ({nombre})."
        )
    return f"El código de barras '{codigo}' está duplicado: ya lo usa el producto {ref}."
