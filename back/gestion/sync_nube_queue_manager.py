import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from back.modelos import SyncNubePendiente
from back.schemas.caja_schemas import ArticuloVendido
from back.utils.tablas_handler import TablasHandler

logger = logging.getLogger(__name__)


OPERACION_REGISTRAR_MOVIMIENTO = "registrar_movimiento"
OPERACION_RESTAR_STOCK = "restar_stock"


def encolar_sync_nube_pendiente(
    db: Session,
    id_empresa: int,
    operacion: str,
    payload: Dict[str, Any],
    id_venta: Optional[int] = None,
    max_intentos: int = 10,
) -> SyncNubePendiente:
    ahora = datetime.utcnow()
    pendiente = SyncNubePendiente(
        id_empresa=id_empresa,
        id_venta=id_venta,
        operacion=operacion,
        payload=payload,
        estado="pendiente",
        intentos=0,
        max_intentos=max_intentos,
        proximo_reintento_en=ahora,
        actualizado_en=ahora,
    )
    db.add(pendiente)
    db.flush()
    return pendiente


def _calcular_proximo_reintento(intentos_realizados: int) -> datetime:
    # Backoff exponencial con tope de 5 minutos.
    delay_segundos = min(300, max(10, 2 ** max(1, intentos_realizados)))
    return datetime.utcnow() + timedelta(seconds=delay_segundos)


def _procesar_registrar_movimiento(handler: TablasHandler, payload: Dict[str, Any]) -> None:
    ok = handler.registrar_movimiento(payload)
    if not ok:
        raise RuntimeError(handler.ultimo_error_sync or "Fallo al registrar movimiento en Google Sheets.")


def _procesar_restar_stock(handler: TablasHandler, payload: Dict[str, Any]) -> None:
    items_payload = payload.get("articulos_vendidos", [])
    items: List[ArticuloVendido] = []
    for item in items_payload:
        items.append(
            ArticuloVendido(
                id_articulo=int(item["id_articulo"]),
                cantidad=float(item["cantidad"]),
                precio_unitario=float(item.get("precio_unitario", 0.0)),
            )
        )
    ok = handler.restar_stock(handler.db, items)
    if not ok:
        raise RuntimeError(handler.ultimo_error_sync or "Fallo al actualizar stock en Google Sheets.")


def procesar_cola_sync_nube(db: Session, max_items: int = 50) -> Dict[str, int]:
    ahora = datetime.utcnow()
    pendientes = db.exec(
        select(SyncNubePendiente)
        .where(SyncNubePendiente.estado == "pendiente")
        .where(SyncNubePendiente.proximo_reintento_en <= ahora)
        .order_by(SyncNubePendiente.creado_en.asc())
        .limit(max_items)
    ).all()

    procesados = 0
    completados = 0
    reprogramados = 0
    fallidos = 0

    for item in pendientes:
        procesados += 1
        item.estado = "procesando"
        item.actualizado_en = datetime.utcnow()
        db.add(item)
        db.flush()

        try:
            handler = TablasHandler(id_empresa=item.id_empresa, db=db)
            if item.operacion == OPERACION_REGISTRAR_MOVIMIENTO:
                _procesar_registrar_movimiento(handler, item.payload)
            elif item.operacion == OPERACION_RESTAR_STOCK:
                _procesar_restar_stock(handler, item.payload)
            else:
                raise ValueError(f"Operación de sync no soportada: {item.operacion}")

            item.estado = "completado"
            item.ultimo_error = None
            item.actualizado_en = datetime.utcnow()
            db.add(item)
            completados += 1
        except Exception as e:
            item.intentos = (item.intentos or 0) + 1
            item.ultimo_error = f"{type(e).__name__}: {e}"
            item.actualizado_en = datetime.utcnow()

            if item.intentos >= item.max_intentos:
                item.estado = "fallido"
                fallidos += 1
            else:
                item.estado = "pendiente"
                item.proximo_reintento_en = _calcular_proximo_reintento(item.intentos)
                reprogramados += 1
            db.add(item)

    db.commit()
    return {
        "procesados": procesados,
        "completados": completados,
        "reprogramados": reprogramados,
        "fallidos": fallidos,
    }


def procesar_cola_sync_nube_en_background(max_items: int = 50) -> None:
    """Procesa la cola sync_nube en un hilo aparte, tras commit de la venta."""
    from back.database import SessionLocal

    try:
        with SessionLocal() as db:
            resumen = procesar_cola_sync_nube(db=db, max_items=max_items)
            if resumen.get("procesados", 0) > 0:
                logger.info("Cola sync_nube (background): %s", resumen)
    except Exception:
        logger.exception("Error procesando cola sync_nube en background")
