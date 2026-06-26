# back/gestion/modo_especial_manager.py

import csv
import io
import re
import unicodedata
from contextlib import nullcontext
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from back.modelos import Articulo, ArticuloCodigo, Categoria, ConfiguracionEmpresa, StockMovimiento
from back.schemas.modo_especial_schemas import (
    BulkProductosRequest,
    ImportExportResumen,
    IngresoStockRequest,
    ProductoModoEspecialCreate,
    ProductoModoEspecialUpdate,
    SubaPreciosRequest,
)

UNIDADES_VALIDAS = {"unidad", "gramos", "kilogramos", "litros", "mililitros"}

_ALIASES_UNIDAD: Dict[str, str] = {
    "unidad": "unidad",
    "unidades": "unidad",
    "u": "unidad",
    "und": "unidad",
    "unds": "unidad",
    "gramo": "gramos",
    "gramos": "gramos",
    "g": "gramos",
    "gr": "gramos",
    "kilogramo": "kilogramos",
    "kilogramos": "kilogramos",
    "kg": "kilogramos",
    "kgs": "kilogramos",
    "litro": "litros",
    "litros": "litros",
    "l": "litros",
    "lt": "litros",
    "lts": "litros",
    "mililitro": "mililitros",
    "mililitros": "mililitros",
    "ml": "mililitros",
    "cc": "mililitros",
}

CSV_HEADERS = [
    "Codigo",
    "Producto",
    "Precio",
    "Costo",
    "Categorias",
    "Stock",
    "StockMinimo",
    "CodigoBarras",
    "Unidad",
    "CantidadEnvase",
    "Ubicacion",
]


def _normalizar_unidad(unidad: str) -> str:
    valor = _sin_acentos((unidad or "unidad").strip().lower())
    valor = _ALIASES_UNIDAD.get(valor, valor)
    if valor not in UNIDADES_VALIDAS:
        raise ValueError(f"Unidad '{unidad}' no válida. Use: {', '.join(sorted(UNIDADES_VALIDAS))}")
    return valor


def _unidad_a_db(unidad: str) -> str:
    mapa = {
        "unidad": "Unidad",
        "gramos": "Gramos",
        "kilogramos": "Kilogramos",
        "litros": "Litros",
        "mililitros": "Mililitros",
    }
    return mapa[_normalizar_unidad(unidad)]


def _ubicacion_desde_envase(cantidad_envase: Optional[float], unidad: str, ubicacion: Optional[str]) -> Optional[str]:
    if ubicacion and ubicacion.strip():
        return ubicacion.strip()
    if cantidad_envase is not None and cantidad_envase > 0:
        return f"{cantidad_envase:g} {_normalizar_unidad(unidad)}"
    return None


def _parse_cantidad_envase(ubicacion: Optional[str]) -> Optional[float]:
    if not ubicacion:
        return None
    match = re.match(r"^([\d.,]+)\s", ubicacion.strip())
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", "."))
    except ValueError:
        return None


def _obtener_o_crear_categoria(db: Session, id_empresa: int, nombre: str) -> Optional[Categoria]:
    if not nombre or not nombre.strip():
        return None
    nombre_limpio = nombre.strip()
    instancia = db.exec(
        select(Categoria).where(Categoria.nombre == nombre_limpio, Categoria.id_empresa == id_empresa)
    ).first()
    if instancia:
        return instancia
    nueva = Categoria(nombre=nombre_limpio, id_empresa=id_empresa)
    db.add(nueva)
    db.flush()
    return nueva


def _normalizar_lista_categorias(nombres: List[str]) -> List[str]:
    """Deduplica categorías preservando orden (mismo criterio que el POS paralelo)."""
    vistos: set[str] = set()
    resultado: List[str] = []
    for nombre in nombres:
        limpio = nombre.strip()
        if not limpio:
            continue
        clave = limpio.lower()
        if clave in vistos:
            continue
        vistos.add(clave)
        resultado.append(limpio)
    return resultado


def _leer_categorias_articulo(articulo: Articulo) -> List[str]:
    """
    Lee categorías del array JSON (fuente de verdad en modo especial).
    Si no hay JSON, usa la FK legacy id_categoria (artículos de Sheets u otros orígenes).
    """
    json_cats = getattr(articulo, "categorias", None)
    if isinstance(json_cats, list) and json_cats:
        return _normalizar_lista_categorias([str(c) for c in json_cats])
    if articulo.categoria and articulo.categoria.nombre:
        return [articulo.categoria.nombre]
    return []


def _asignar_categorias_articulo(
    db: Session,
    id_empresa: int,
    articulo: Articulo,
    nombres: List[str],
) -> None:
    """
    Persiste el array completo en articulos.categorias (como products.categories en el POS).
    Mantiene id_categoria = primera categoría para compatibilidad con el resto del sistema IMA.
    """
    categorias = _normalizar_lista_categorias(nombres)
    if not categorias:
        raise ValueError("Debe indicar al menos una categoría.")

    articulo.categorias = categorias
    primera = _obtener_o_crear_categoria(db, id_empresa, categorias[0])
    articulo.id_categoria = primera.id if primera else None
    for nombre in categorias[1:]:
        _obtener_o_crear_categoria(db, id_empresa, nombre)


def _incrementar_catalogo_version(db: Session, id_empresa: int) -> None:
    config = db.get(ConfiguracionEmpresa, id_empresa)
    if config:
        config.catalogo_version = (config.catalogo_version or 0) + 1
        db.add(config)


def _asignar_barcodes(
    db: Session,
    articulo: Articulo,
    barcodes: Optional[List[str]],
    omitir_conflictos: bool = False,
) -> None:
    if barcodes is None:
        return
    codigos_actuales = {c.codigo for c in (articulo.codigos or [])}
    deseados = set(barcodes)
    for codigo in codigos_actuales - deseados:
        obj = db.get(ArticuloCodigo, codigo)
        if obj:
            db.delete(obj)
    for codigo in deseados - codigos_actuales:
        existente = db.get(ArticuloCodigo, codigo)
        if existente and existente.id_articulo != articulo.id:
            if omitir_conflictos:
                continue
            raise ValueError(f"El código de barras '{codigo}' ya está asignado a otro artículo.")
        db.add(ArticuloCodigo(codigo=codigo, id_articulo=articulo.id))


def _articulo_a_response(articulo: Articulo) -> Dict[str, Any]:
    categorias = _leer_categorias_articulo(articulo)
    return {
        "id": articulo.id,
        "codigo_interno": articulo.codigo_interno or "",
        "descripcion": articulo.descripcion,
        "precio_venta": articulo.precio_venta,
        "precio_costo": articulo.precio_costo,
        "venta_negocio": articulo.venta_negocio,
        "categorias": categorias,
        "stock_actual": articulo.stock_actual,
        "stock_minimo": articulo.stock_minimo,
        "barcodes": [c.codigo for c in (articulo.codigos or [])],
        "unidad": (articulo.unidad_venta or "Unidad").lower(),
        "cantidad_envase": _parse_cantidad_envase(articulo.ubicacion),
        "ubicacion": articulo.ubicacion,
        "activo": articulo.activo,
    }


def _obtener_articulo_por_codigo(db: Session, id_empresa: int, codigo_interno: str) -> Optional[Articulo]:
    return db.exec(
        select(Articulo)
        .where(Articulo.codigo_interno == codigo_interno, Articulo.id_empresa == id_empresa)
        .options(selectinload(Articulo.codigos), selectinload(Articulo.categoria))
    ).first()


def crear_producto(
    db: Session,
    id_empresa: int,
    data: ProductoModoEspecialCreate,
    *,
    omitir_conflictos_barcode: bool = False,
    commit: bool = True,
) -> Dict[str, Any]:
    if _obtener_articulo_por_codigo(db, id_empresa, data.codigo_interno):
        raise ValueError(f"El código '{data.codigo_interno}' ya existe.")

    articulo = Articulo(
        codigo_interno=data.codigo_interno.strip(),
        descripcion=data.descripcion.strip(),
        precio_venta=data.precio_venta,
        venta_negocio=data.precio_venta,
        precio_costo=data.precio_costo or 0.0,
        auto_actualizar_precio=False,
        stock_actual=data.stock if data.stock is not None else 0.0,
        stock_minimo=data.stock_minimo,
        unidad_venta=_unidad_a_db(data.unidad.value),
        unidad_compra=_unidad_a_db(data.unidad.value),
        ubicacion=_ubicacion_desde_envase(data.cantidad_envase, data.unidad.value, data.ubicacion),
        id_empresa=id_empresa,
        activo=True,
    )
    _asignar_categorias_articulo(db, id_empresa, articulo, data.categorias)
    db.add(articulo)
    db.flush()
    _asignar_barcodes(db, articulo, data.barcodes, omitir_conflictos=omitir_conflictos_barcode)
    _incrementar_catalogo_version(db, id_empresa)
    if commit:
        db.commit()
        db.refresh(articulo)
    return _articulo_a_response(articulo)


def actualizar_producto(
    db: Session,
    id_empresa: int,
    codigo_interno: str,
    data: ProductoModoEspecialUpdate,
    *,
    omitir_conflictos_barcode: bool = False,
    commit: bool = True,
) -> Dict[str, Any]:
    articulo = _obtener_articulo_por_codigo(db, id_empresa, codigo_interno)
    if not articulo:
        raise ValueError(f"Producto '{codigo_interno}' no encontrado.")

    update = data.model_dump(exclude_unset=True)
    if "descripcion" in update and update["descripcion"]:
        articulo.descripcion = update["descripcion"].strip()
    if "precio_venta" in update and update["precio_venta"] is not None:
        articulo.precio_venta = update["precio_venta"]
        articulo.venta_negocio = update["precio_venta"]
    if "precio_costo" in update and update["precio_costo"] is not None:
        articulo.precio_costo = update["precio_costo"]
    if "stock" in update and update["stock"] is not None:
        articulo.stock_actual = update["stock"]
    if "stock_minimo" in update:
        articulo.stock_minimo = update["stock_minimo"]
    if "activo" in update and update["activo"] is not None:
        articulo.activo = update["activo"]
    if "categorias" in update and update["categorias"]:
        _asignar_categorias_articulo(db, id_empresa, articulo, update["categorias"])
    if "unidad" in update and update["unidad"]:
        unidad_db = _unidad_a_db(update["unidad"].value if hasattr(update["unidad"], "value") else update["unidad"])
        articulo.unidad_venta = unidad_db
        articulo.unidad_compra = unidad_db
    if "cantidad_envase" in update or "ubicacion" in update:
        unidad = (articulo.unidad_venta or "unidad").lower()
        cantidad = update.get("cantidad_envase", _parse_cantidad_envase(articulo.ubicacion))
        ubicacion = update.get("ubicacion", articulo.ubicacion)
        articulo.ubicacion = _ubicacion_desde_envase(cantidad, unidad, ubicacion)
    if "barcodes" in update:
        _asignar_barcodes(db, articulo, update["barcodes"], omitir_conflictos=omitir_conflictos_barcode)

    db.add(articulo)
    _incrementar_catalogo_version(db, id_empresa)
    if commit:
        db.commit()
        db.refresh(articulo)
    return _articulo_a_response(articulo)


def listar_productos(db: Session, id_empresa: int) -> List[Dict[str, Any]]:
    articulos = db.exec(
        select(Articulo)
        .where(Articulo.id_empresa == id_empresa, Articulo.activo == True)
        .order_by(Articulo.descripcion)
        .options(selectinload(Articulo.codigos), selectinload(Articulo.categoria))
    ).all()
    return [_articulo_a_response(a) for a in articulos]


def bulk_upsert(
    db: Session,
    id_empresa: int,
    req: BulkProductosRequest,
    *,
    omitir_conflictos_barcode: bool = False,
    commit_por_producto: bool = True,
) -> ImportExportResumen:
    resumen = ImportExportResumen()
    for producto in req.productos:
        try:
            if commit_por_producto:
                ctx = nullcontext()
            else:
                ctx = db.begin_nested()
            with ctx:
                existente = _obtener_articulo_por_codigo(db, id_empresa, producto.codigo_interno)
                if existente:
                    actualizar_producto(
                        db,
                        id_empresa,
                        producto.codigo_interno,
                        ProductoModoEspecialUpdate(
                            descripcion=producto.descripcion,
                            precio_venta=producto.precio_venta,
                            precio_costo=producto.precio_costo,
                            categorias=producto.categorias,
                            stock=producto.stock,
                            stock_minimo=producto.stock_minimo,
                            barcodes=producto.barcodes,
                            unidad=producto.unidad,
                            cantidad_envase=producto.cantidad_envase,
                            ubicacion=producto.ubicacion,
                        ),
                        omitir_conflictos_barcode=omitir_conflictos_barcode,
                        commit=commit_por_producto,
                    )
                    resumen.actualizados += 1
                else:
                    crear_producto(
                        db,
                        id_empresa,
                        producto,
                        omitir_conflictos_barcode=omitir_conflictos_barcode,
                        commit=commit_por_producto,
                    )
                    resumen.creados += 1
        except Exception as e:
            resumen.errores += 1
            resumen.detalle_errores.append(f"{producto.codigo_interno}: {e}")
    if not commit_por_producto and (resumen.creados or resumen.actualizados):
        db.commit()
    return resumen


def ingresar_stock(db: Session, id_empresa: int, id_usuario: int, req: IngresoStockRequest) -> Dict[str, Any]:
    procesados = []
    for item in req.items:
        if not item.codigo_interno and not item.id_articulo:
            raise ValueError("Cada ítem debe tener codigo_interno o id_articulo.")
        if item.codigo_interno:
            articulo = _obtener_articulo_por_codigo(db, id_empresa, item.codigo_interno)
        else:
            articulo = db.exec(
                select(Articulo)
                .where(Articulo.id == item.id_articulo, Articulo.id_empresa == id_empresa)
                .options(selectinload(Articulo.codigos))
            ).first()
        if not articulo:
            ident = item.codigo_interno or str(item.id_articulo)
            raise ValueError(f"Artículo '{ident}' no encontrado.")

        stock_anterior = articulo.stock_actual or 0.0
        stock_nuevo = stock_anterior + item.cantidad
        articulo.stock_actual = stock_nuevo
        movimiento = StockMovimiento(
            tipo="INGRESO",
            cantidad=item.cantidad,
            stock_anterior=stock_anterior,
            stock_nuevo=stock_nuevo,
            id_articulo=articulo.id,
            id_usuario=id_usuario,
            id_empresa=id_empresa,
        )
        db.add(articulo)
        db.add(movimiento)
        procesados.append({
            "codigo_interno": articulo.codigo_interno,
            "descripcion": articulo.descripcion,
            "cantidad": item.cantidad,
            "stock_nuevo": stock_nuevo,
            "observacion": item.observacion,
        })

    _incrementar_catalogo_version(db, id_empresa)
    db.commit()
    return {"procesados": procesados, "total": len(procesados)}


def subir_precios(db: Session, id_empresa: int, req: SubaPreciosRequest) -> Dict[str, Any]:
    actualizados = 0
    if req.productos:
        for item in req.productos:
            articulo = _obtener_articulo_por_codigo(db, id_empresa, item.codigo_interno)
            if not articulo:
                continue
            articulo.precio_venta = item.precio_venta
            articulo.venta_negocio = item.precio_venta
            db.add(articulo)
            actualizados += 1
    else:
        articulos = db.exec(
            select(Articulo)
            .where(Articulo.id_empresa == id_empresa, Articulo.activo == True)
            .options(selectinload(Articulo.categoria))
        ).all()
        if req.categoria:
            cat_busqueda = req.categoria.strip().lower()
            articulos = [
                a for a in articulos
                if cat_busqueda in [c.lower() for c in _leer_categorias_articulo(a)]
            ]
        if req.porcentaje_general is None:
            raise ValueError("Indique porcentaje_general, categoria o lista de productos.")
        factor = 1 + (req.porcentaje_general / 100.0)
        for articulo in articulos:
            articulo.precio_venta = round(articulo.precio_venta * factor, 2)
            articulo.venta_negocio = articulo.precio_venta
            db.add(articulo)
            actualizados += 1

    _incrementar_catalogo_version(db, id_empresa)
    db.commit()
    return {"actualizados": actualizados}


def _parse_categorias_csv(valor: str) -> List[str]:
    if not valor or not valor.strip():
        return ["General"]
    partes = re.split(r"[,;|]", valor)
    return _normalizar_lista_categorias(partes)


def _parse_barcodes_csv(valor: str) -> Optional[List[str]]:
    if not valor or not valor.strip():
        return None
    partes = re.split(r"[,;|]", valor)
    limpios = [p.strip() for p in partes if p.strip()]
    return limpios or None


def _sin_acentos(texto: str) -> str:
    normalizado = unicodedata.normalize("NFD", texto)
    return "".join(c for c in normalizado if unicodedata.category(c) != "Mn")


def _normalizar_clave_csv(clave: str) -> str:
    limpia = _sin_acentos((clave or "").strip().lower())
    return re.sub(r"[^a-z0-9]+", "_", limpia).strip("_")


_ALIASES_CSV: Dict[str, str] = {
    "codigo": "codigo",
    "sku": "codigo",
    "producto": "producto",
    "descripcion": "producto",
    "nombre": "producto",
    "precio": "precio",
    "precio_venta": "precio",
    "costo": "costo",
    "categorias": "categorias",
    "categoria": "categorias",
    "stock": "stock",
    "stockminimo": "stock_minimo",
    "stock_minimo": "stock_minimo",
    "codigobarras": "codigo_barras",
    "codigo_barras": "codigo_barras",
    "barcode": "codigo_barras",
    "barcodes": "codigo_barras",
    "unidad": "unidad",
    "cantidadenvase": "cantidad_envase",
    "cantidad_envase": "cantidad_envase",
    "ubicacion": "ubicacion",
}


def _mapear_clave_csv(clave: str) -> Optional[str]:
    return _ALIASES_CSV.get(_normalizar_clave_csv(clave))


def _detectar_delimitador_csv(contenido: str) -> str:
    primera = ""
    for linea in contenido.splitlines():
        if linea.strip():
            primera = linea
            break
    if not primera:
        return ","
    if primera.count(";") > primera.count(","):
        return ";"
    try:
        dialect = csv.Sniffer().sniff(primera, delimiters=";,\t|")
        return dialect.delimiter
    except csv.Error:
        return ","


def _normalizar_fila_csv(fila: Dict[str, Any]) -> Dict[str, str]:
    normalizada: Dict[str, str] = {}
    for clave, valor in fila.items():
        destino = _mapear_clave_csv(clave or "")
        if not destino or valor is None:
            continue
        texto = str(valor).strip()
        if texto:
            normalizada[destino] = texto
    return normalizada


def _parse_numero_csv(valor: Optional[str], default: Optional[float] = None) -> Optional[float]:
    if valor is None:
        return default
    texto = str(valor).strip()
    if not texto:
        return default
    texto = texto.replace("$", "").replace(" ", "")
    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        partes = texto.split(",")
        if len(partes) == 2 and len(partes[1]) <= 2:
            texto = texto.replace(",", ".")
        else:
            texto = texto.replace(",", "")
    try:
        return float(texto)
    except ValueError as e:
        raise ValueError(f"Número inválido '{valor}'") from e


def _leer_filas_csv(contenido: str) -> List[Dict[str, str]]:
    delimitador = _detectar_delimitador_csv(contenido)
    reader = csv.DictReader(io.StringIO(contenido), delimiter=delimitador)
    return [_normalizar_fila_csv(fila) for fila in reader]


def exportar_csv(db: Session, id_empresa: int) -> str:
    productos = listar_productos(db, id_empresa)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_HEADERS)
    writer.writeheader()
    for p in productos:
        writer.writerow({
            "Codigo": p["codigo_interno"],
            "Producto": p["descripcion"],
            "Precio": p["precio_venta"],
            "Costo": p["precio_costo"],
            "Categorias": ", ".join(p["categorias"]),
            "Stock": p["stock_actual"],
            "StockMinimo": p.get("stock_minimo") or "",
            "CodigoBarras": ", ".join(p["barcodes"]),
            "Unidad": p["unidad"],
            "CantidadEnvase": p.get("cantidad_envase") or "",
            "Ubicacion": p.get("ubicacion") or "",
        })
    return buffer.getvalue()


def importar_csv(db: Session, id_empresa: int, contenido: str) -> ImportExportResumen:
    filas = _leer_filas_csv(contenido)
    productos: List[ProductoModoEspecialCreate] = []
    resumen = ImportExportResumen()

    if not filas and contenido.strip():
        resumen.errores = 1
        resumen.detalle_errores.append(
            "No se pudieron leer filas del CSV. Verifique que use columnas Codigo y Producto "
            "(coma o punto y coma como separador)."
        )
        return resumen

    for fila in filas:
        codigo = (fila.get("codigo") or "").strip()
        nombre = (fila.get("producto") or "").strip()
        if not codigo or not nombre:
            resumen.errores += 1
            resumen.detalle_errores.append(f"Fila omitida: falta código o nombre ({fila})")
            continue
        try:
            precio = _parse_numero_csv(fila.get("precio"), 0.0)
            costo = _parse_numero_csv(fila.get("costo"))
            stock = _parse_numero_csv(fila.get("stock"))
            if stock is not None and stock < 0:
                stock = 0.0
            stock_min = _parse_numero_csv(fila.get("stock_minimo"))
            unidad = _normalizar_unidad(fila.get("unidad") or "unidad")
            cantidad_envase = _parse_numero_csv(fila.get("cantidad_envase"))
            productos.append(ProductoModoEspecialCreate(
                codigo_interno=codigo,
                descripcion=nombre,
                precio_venta=precio or 0.0,
                precio_costo=costo,
                categorias=_parse_categorias_csv(fila.get("categorias") or ""),
                stock=stock,
                stock_minimo=stock_min,
                barcodes=_parse_barcodes_csv(fila.get("codigo_barras") or ""),
                unidad=unidad,
                cantidad_envase=cantidad_envase,
                ubicacion=(fila.get("ubicacion") or "").strip() or None,
            ))
        except Exception as e:
            resumen.errores += 1
            resumen.detalle_errores.append(f"{codigo}: {e}")

    if productos:
        bulk_resumen = bulk_upsert(
            db,
            id_empresa,
            BulkProductosRequest(productos=productos),
            omitir_conflictos_barcode=True,
            commit_por_producto=False,
        )
        resumen.creados += bulk_resumen.creados
        resumen.actualizados += bulk_resumen.actualizados
        resumen.errores += bulk_resumen.errores
        resumen.detalle_errores.extend(bulk_resumen.detalle_errores)

    return resumen
