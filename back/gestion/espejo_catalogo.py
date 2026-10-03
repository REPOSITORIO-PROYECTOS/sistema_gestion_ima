# back/gestion/espejo_catalogo.py
"""Espejo de catálogo entre sucursales (producto, precios y códigos de barra).

Grupo: La Esquina (35) ↔ FULL24 (36).
No copia stock_actual ni stock_minimo: cada local mantiene su depósito.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import NoInspectionAvailable
from sqlmodel import Session, select

from back.modelos import Articulo, ArticuloCodigo, Categoria, ConfiguracionEmpresa
from back.utils.articulo_helpers import articulo_con_barcode_en_empresa, mensaje_barcode_duplicado

# Pares que comparten catálogo. Ampliar solo con decisión de negocio.
ESPEJO_CATALOGO_GRUPOS: tuple[frozenset[int], ...] = (frozenset({35, 36}),)

_CAMPOS_CATALOGO: tuple[str, ...] = (
    "descripcion",
    "precio_venta",
    "precio_costo",
    "venta_negocio",
    "tasa_iva",
    "margen_ganancia",
    "auto_actualizar_precio",
    "precio_manual",
    "unidad_compra",
    "unidad_venta",
    "factor_conversion",
    "ubicacion",
    "activo",
)


def peers_catalogo(id_empresa: int) -> Optional[frozenset[int]]:
    for grupo in ESPEJO_CATALOGO_GRUPOS:
        if id_empresa in grupo:
            return grupo - {id_empresa}
    return None


def _distinto(actual, nuevo) -> bool:
    if isinstance(actual, (int, float)) or isinstance(nuevo, (int, float)):
        try:
            return abs(float(actual or 0) - float(nuevo or 0)) >= 1e-9
        except (TypeError, ValueError):
            return actual != nuevo
    return actual != nuevo


def _nombres_categoria(articulo: Articulo) -> list[str]:
    json_cats = getattr(articulo, "categorias", None)
    if isinstance(json_cats, list) and json_cats:
        return [str(nombre).strip() for nombre in json_cats if str(nombre).strip()]
    categoria = getattr(articulo, "categoria", None)
    nombre = getattr(categoria, "nombre", None) if categoria is not None else None
    if nombre and str(nombre).strip():
        return [str(nombre).strip()]
    return []


def _codigos_si_estan_cargados(articulo: Articulo) -> Optional[set[str]]:
    """None si la relación no está cargada: no pisar barcodes del peer."""
    try:
        state = sa_inspect(articulo)
        unloaded = getattr(state, "unloaded", None)
        if unloaded is not None and "codigos" in unloaded:
            return None
    except NoInspectionAvailable:
        pass
    except Exception:
        pass
    codigos = getattr(articulo, "codigos", None)
    if codigos is None:
        return None
    return {str(codigo.codigo) for codigo in codigos if getattr(codigo, "codigo", None)}


def _incrementar_catalogo_version(db: Session, id_empresa: int) -> None:
    config = db.get(ConfiguracionEmpresa, id_empresa)
    if config is None:
        return
    try:
        actual = int(config.catalogo_version or 0)
    except (TypeError, ValueError):
        actual = 0
    config.catalogo_version = actual + 1
    db.add(config)


def _asegurar_categoria(db: Session, id_empresa: int, nombre: str) -> Optional[int]:
    instancia = db.exec(
        select(Categoria).where(
            Categoria.nombre == nombre,
            Categoria.id_empresa == id_empresa,
        )
    ).first()
    if instancia is not None:
        return instancia.id
    nueva = Categoria(nombre=nombre, id_empresa=id_empresa)
    db.add(nueva)
    db.flush()
    return nueva.id


def _aplicar_categorias(db: Session, origen: Articulo, destino: Articulo) -> bool:
    nombres = _nombres_categoria(origen)
    if not nombres:
        return False
    cambio = list(getattr(destino, "categorias", None) or []) != nombres
    destino.categorias = list(nombres)
    id_categoria = _asegurar_categoria(db, destino.id_empresa, nombres[0])
    if destino.id_categoria != id_categoria:
        destino.id_categoria = id_categoria
        cambio = True
    for nombre in nombres[1:]:
        _asegurar_categoria(db, destino.id_empresa, nombre)
    return cambio


def _sincronizar_barcodes(db: Session, origen: Articulo, destino: Articulo) -> bool:
    origen_codes = _codigos_si_estan_cargados(origen)
    if origen_codes is None:
        return False
    if getattr(destino, "id", None) is None:
        return False

    destino_codes = _codigos_si_estan_cargados(destino)
    if destino_codes is None:
        destino_codes = set()

    if origen_codes == destino_codes:
        return False

    cambio = False
    for codigo_obj in list(getattr(destino, "codigos", None) or []):
        if codigo_obj.codigo not in origen_codes:
            destino.codigos.remove(codigo_obj)
            db.delete(codigo_obj)
            cambio = True

    actuales = _codigos_si_estan_cargados(destino) or set()
    for codigo in sorted(origen_codes - actuales):
        otro = articulo_con_barcode_en_empresa(db, codigo, destino.id, destino.id_empresa)
        if otro is not None:
            raise ValueError(mensaje_barcode_duplicado(codigo, otro))
        nuevo = ArticuloCodigo(codigo=codigo, id_articulo=destino.id)
        if destino.codigos is None:
            destino.codigos = []
        destino.codigos.append(nuevo)
        db.add(nuevo)
        cambio = True
    return cambio


def _aplicar_campos(origen: Articulo, destino: Articulo) -> bool:
    cambio = False
    for campo in _CAMPOS_CATALOGO:
        if not hasattr(origen, campo):
            continue
        nuevo = getattr(origen, campo)
        if _distinto(getattr(destino, campo, None), nuevo):
            setattr(destino, campo, nuevo)
            cambio = True
    return cambio


def _crear_peer(db: Session, origen: Articulo, peer_id: int, codigo: str) -> Articulo:
    peer = Articulo(
        codigo_interno=codigo,
        descripcion=origen.descripcion,
        precio_venta=float(origen.precio_venta or 0.0),
        precio_costo=float(getattr(origen, "precio_costo", 0.0) or 0.0),
        venta_negocio=float(getattr(origen, "venta_negocio", None) or origen.precio_venta or 0.0),
        tasa_iva=float(getattr(origen, "tasa_iva", 0.21) or 0.21),
        margen_ganancia=float(getattr(origen, "margen_ganancia", 0.0) or 0.0),
        auto_actualizar_precio=bool(getattr(origen, "auto_actualizar_precio", False)),
        precio_manual=bool(getattr(origen, "precio_manual", False)),
        unidad_compra=getattr(origen, "unidad_compra", None) or "Unidad",
        unidad_venta=getattr(origen, "unidad_venta", None) or "Unidad",
        factor_conversion=float(getattr(origen, "factor_conversion", 1.0) or 1.0),
        ubicacion=getattr(origen, "ubicacion", None),
        activo=bool(getattr(origen, "activo", True)),
        stock_actual=0.0,
        stock_minimo=None,
        id_empresa=peer_id,
        categorias=list(_nombres_categoria(origen)) or None,
    )
    db.add(peer)
    db.flush()
    _aplicar_categorias(db, origen, peer)
    _sincronizar_barcodes(db, origen, peer)
    return peer


def espejar_catalogo_articulo(db: Session, articulo: Articulo) -> int:
    """Copia producto, precios y barcodes al peer. No toca stock. No hace commit.

    Returns: cantidad de peers creados o actualizados.
    """
    peers = peers_catalogo(getattr(articulo, "id_empresa", None) or 0)
    if not peers:
        return 0

    codigo = (getattr(articulo, "codigo_interno", None) or "").strip()
    if not codigo:
        return 0

    actualizados = 0
    for peer_id in peers:
        peer = db.exec(
            select(Articulo).where(
                Articulo.id_empresa == peer_id,
                Articulo.codigo_interno == codigo,
            )
        ).first()
        if peer is None:
            _crear_peer(db, articulo, peer_id, codigo)
            _incrementar_catalogo_version(db, peer_id)
            actualizados += 1
            continue

        cambio = _aplicar_campos(articulo, peer)
        cambio = _aplicar_categorias(db, articulo, peer) or cambio
        cambio = _sincronizar_barcodes(db, articulo, peer) or cambio
        if not cambio:
            continue
        db.add(peer)
        _incrementar_catalogo_version(db, peer_id)
        actualizados += 1
    return actualizados
