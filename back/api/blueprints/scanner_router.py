import asyncio
import os
import time
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from back.security import obtener_id_empresa_desde_token, obtener_usuario_actual
from back.modelos import Usuario

router = APIRouter(
    prefix="/scanner",
    tags=["Scanner"]
)

POLL_INTERVAL_SEC = float(os.getenv("SCANNER_POLL_INTERVAL_SEC", "0.25"))


class ScannerEvent(BaseModel):
    codigo: Optional[str] = None
    id_articulo: Optional[int] = None
    nombre: Optional[str] = None
    precio: Optional[float] = Field(default=None)
    peso: Optional[float] = Field(default=None)

_queues: Dict[int, List[ScannerEvent]] = {}


def _pop_event(empresa_id: int) -> Optional[ScannerEvent]:
    q = _queues.get(empresa_id)
    if not q:
        return None
    return q.pop(0)


def _enqueue_event(empresa_id: int, event: ScannerEvent) -> None:
    q = _queues.get(empresa_id)
    if q is None:
        _queues[empresa_id] = [event]
    else:
        q.append(event)


def _key_map() -> Dict[str, int]:
    raw = os.getenv("SCANNER_API_KEYS", "")
    m: Dict[str, int] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair:
            continue
        parts = pair.split(":")
        if len(parts) != 2:
            continue
        try:
            empresa_id = int(parts[0])
        except ValueError:
            continue
        m[parts[1]] = empresa_id
    return m


def _allowed_ip(request: Request) -> bool:
    raw = os.getenv("SCANNER_ALLOWED_IPS", "")
    if not raw:
        return True
    allowed = {ip.strip() for ip in raw.split(",") if ip.strip()}
    return request.client and request.client.host in allowed


async def _long_poll_event(empresa_id: int, timeout_sec: int) -> dict:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        event = _pop_event(empresa_id)
        if event is not None:
            return {"has_event": True, "event": event.model_dump()}
        await asyncio.sleep(POLL_INTERVAL_SEC)
    return {"has_event": False}


@router.post("/evento")
def push_event(
    event: ScannerEvent,
    current_user: Usuario = Depends(obtener_usuario_actual),
):
    empresa_id = current_user.id_empresa
    if empresa_id is None:
        raise HTTPException(status_code=400, detail="Usuario sin empresa asociada")
    _enqueue_event(empresa_id, event)
    return {"status": "ok"}


@router.get("/evento/poll")
async def poll_event(
    timeout: int = Query(25, ge=0, le=30, description="Long-poll: espera hasta N segundos por un evento"),
    empresa_id: int = Depends(obtener_id_empresa_desde_token),
):
    if timeout <= 0:
        event = _pop_event(empresa_id)
        if event is None:
            return {"has_event": False}
        return {"has_event": True, "event": event.model_dump()}
    return await _long_poll_event(empresa_id, timeout)


@router.post("/evento/public")
def push_event_public(
    event: ScannerEvent,
    request: Request,
):
    x_key = request.headers.get("X-Scanner-Key")
    empresa_id = _key_map().get(x_key or "")
    if not empresa_id:
        raise HTTPException(status_code=401, detail="Clave inválida")
    if not _allowed_ip(request):
        raise HTTPException(status_code=403, detail="IP no autorizada")
    _enqueue_event(empresa_id, event)
    return {"status": "ok"}


@router.get("/evento/poll/public")
async def poll_event_public(
    request: Request,
    timeout: int = Query(25, ge=0, le=30),
):
    x_key = request.headers.get("X-Scanner-Key")
    empresa_id = _key_map().get(x_key or "")
    if not empresa_id:
        raise HTTPException(status_code=401, detail="Clave inválida")
    if not _allowed_ip(request):
        raise HTTPException(status_code=403, detail="IP no autorizada")
    if timeout <= 0:
        event = _pop_event(empresa_id)
        if event is None:
            return {"has_event": False}
        return {"has_event": True, "event": event.model_dump()}
    return await _long_poll_event(empresa_id, timeout)
