# back/gestion/stock/espejo_stock.py
"""Espejo de stock entre sucursales (mismo stock_actual por codigo_interno).

Grupo actual: de-campo (37) ↔ La Esquina 2 (38).
No aplica a La Esquina / FULL24 (35/36), que son depósitos reales separados.
"""
from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from back.modelos import Articulo

# Pares que deben quedar igualados. Ampliar solo con decisión de negocio.
ESPEJO_STOCK_GRUPOS: tuple[frozenset[int], ...] = (frozenset({37, 38}),)


def peers_espejo(id_empresa: int) -> Optional[frozenset[int]]:
    for grupo in ESPEJO_STOCK_GRUPOS:
        if id_empresa in grupo:
            return grupo - {id_empresa}
    return None


def empresas_en_mismo_espejo(id_a: int, id_b: int) -> bool:
    for grupo in ESPEJO_STOCK_GRUPOS:
        if id_a in grupo and id_b in grupo:
            return True
    return False


def espejar_stock_articulo(db: Session, articulo: Articulo) -> int:
    """Copia stock_actual del artículo a los peers del grupo por codigo_interno.

    No hace commit. No reentra (setea peers sin volver a llamar).
    Returns: cantidad de peers actualizados.
    """
    peers = peers_espejo(getattr(articulo, "id_empresa", None) or 0)
    if not peers:
        return 0

    codigo = (articulo.codigo_interno or "").strip()
    if not codigo:
        return 0

    stock = float(articulo.stock_actual or 0.0)
    actualizados = 0
    for peer_id in peers:
        peer = db.exec(
            select(Articulo).where(
                Articulo.id_empresa == peer_id,
                Articulo.codigo_interno == codigo,
            )
        ).first()
        if peer is None:
            continue
        if abs(float(peer.stock_actual or 0.0) - stock) < 1e-9:
            continue
        peer.stock_actual = stock
        db.add(peer)
        actualizados += 1
    return actualizados
