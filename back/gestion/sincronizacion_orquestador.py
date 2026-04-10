"""
Orquestador unificado para sincronización por empresa.

Centraliza la ejecución de sincronización de artículos, clientes y proveedores
para que API manual y scheduler compartan la misma lógica de secuenciado,
errores y reporte.
"""

import logging
from time import perf_counter
from typing import Any, Dict
from sqlalchemy import text
from sqlmodel import Session

from back.gestion.sincronizacion_manager import sincronizar_articulos_desde_sheet
from back.gestion.actualizaciones.actualizaciones_masivas import (
    sincronizar_clientes_desde_sheets,
    sincronizar_proveedores_desde_sheets,
)

logger = logging.getLogger(__name__)


def _acquire_sync_lock(db: Session, id_empresa: int, timeout_seconds: int = 0) -> bool:
    """Obtiene un lock de base de datos para evitar sincronizaciones concurrentes por empresa."""
    lock_name = f"sync_empresa_{id_empresa}"
    try:
        row = db.execute(
            text("SELECT GET_LOCK(:lock_name, :timeout_seconds) AS lock_acquired"),
            {"lock_name": lock_name, "timeout_seconds": timeout_seconds},
        ).first()
        if isinstance(row, tuple):
            return bool(row[0])
        if isinstance(row, dict):
            return bool(row.get("lock_acquired"))
        return bool(getattr(row, "lock_acquired", row))
    except Exception as e:
        # Fallback defensivo: no rompemos sincronización por un problema de lock.
        logger.warning("No se pudo adquirir lock de sincronización para empresa %s: %s", id_empresa, e)
        return True


def _release_sync_lock(db: Session, id_empresa: int) -> None:
    """Libera el lock de sincronización por empresa."""
    lock_name = f"sync_empresa_{id_empresa}"
    try:
        db.execute(text("SELECT RELEASE_LOCK(:lock_name)"), {"lock_name": lock_name})
    except Exception as e:
        logger.warning("No se pudo liberar lock de sincronización para empresa %s: %s", id_empresa, e)


def _ejecutar_paso(nombre: str, fn, *args, **kwargs) -> Dict[str, Any]:
    inicio = perf_counter()
    try:
        resultado = fn(*args, **kwargs)
        duracion_ms = round((perf_counter() - inicio) * 1000, 2)
        return {
            "paso": nombre,
            "ok": True,
            "duracion_ms": duracion_ms,
            "resultado": resultado,
        }
    except Exception as e:
        duracion_ms = round((perf_counter() - inicio) * 1000, 2)
        return {
            "paso": nombre,
            "ok": False,
            "duracion_ms": duracion_ms,
            "error": str(e),
        }


def sincronizar_empresa_unificada(
    db: Session,
    id_empresa: int,
    incluir_articulos: bool = True,
    incluir_clientes: bool = True,
    incluir_proveedores: bool = False,
    detener_en_error: bool = False,
    usar_lock: bool = True,
) -> Dict[str, Any]:
    """
    Ejecuta sincronización unificada por empresa y devuelve reporte homogéneo.

    - `detener_en_error=False`: continúa con los siguientes pasos aunque falle uno.
    - `detener_en_error=True`: corta en el primer error.
    """
    inicio_total = perf_counter()
    pasos: Dict[str, Dict[str, Any]] = {}
    orden = []

    lock_adquirido = False
    if usar_lock:
        lock_adquirido = _acquire_sync_lock(db, id_empresa)
        if not lock_adquirido:
            return {
                "status": "busy",
                "message": "Sincronización omitida: ya existe una sincronización en curso para esta empresa.",
                "id_empresa": id_empresa,
                "duracion_total_ms": round((perf_counter() - inicio_total) * 1000, 2),
                "resumen": {
                    "pasos_solicitados": 0,
                    "pasos_exitosos": 0,
                    "pasos_fallidos": 0,
                },
                "pasos": {},
            }

    if incluir_articulos:
        orden.append(("articulos", sincronizar_articulos_desde_sheet))
    if incluir_clientes:
        orden.append(("clientes", sincronizar_clientes_desde_sheets))
    if incluir_proveedores:
        orden.append(("proveedores", sincronizar_proveedores_desde_sheets))

    try:
        for nombre, fn in orden:
            paso = _ejecutar_paso(nombre, fn, db, id_empresa)
            pasos[nombre] = paso
            if detener_en_error and not paso["ok"]:
                break

        total = len(orden)
        exitosos = sum(1 for p in pasos.values() if p.get("ok"))
        fallidos = total - exitosos
        duracion_total_ms = round((perf_counter() - inicio_total) * 1000, 2)

        if total == 0:
            estado = "sin_acciones"
            mensaje = "No se solicitaron pasos de sincronización."
        elif fallidos == 0:
            estado = "success"
            mensaje = f"Sincronización completada ({exitosos}/{total} pasos OK)."
        elif exitosos == 0:
            estado = "error"
            mensaje = "Sincronización fallida: no se pudo completar ningún paso."
        else:
            estado = "partial"
            mensaje = f"Sincronización parcial ({exitosos}/{total} pasos OK, {fallidos} con error)."

        return {
            "status": estado,
            "message": mensaje,
            "id_empresa": id_empresa,
            "duracion_total_ms": duracion_total_ms,
            "resumen": {
                "pasos_solicitados": total,
                "pasos_exitosos": exitosos,
                "pasos_fallidos": fallidos,
            },
            "pasos": pasos,
        }
    finally:
        if usar_lock and lock_adquirido:
            _release_sync_lock(db, id_empresa)
