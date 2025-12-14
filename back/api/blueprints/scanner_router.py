import os
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session
from typing import Optional, Dict, List

from back.database import get_db
from back.modelos import Usuario
from back.security import obtener_usuario_actual

from pydantic import BaseModel, Field

router = APIRouter(
    prefix="/scanner",
    tags=["Scanner"]
)

class ScannerEvent(BaseModel):
    codigo: Optional[str] = None
    id_articulo: Optional[int] = None
    nombre: Optional[str] = None
    precio: Optional[float] = Field(default=None)
    peso: Optional[float] = Field(default=None)

_queues: Dict[int, List[ScannerEvent]] = {}

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

@router.post("/evento")
def push_event(
    event: ScannerEvent,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    empresa_id = current_user.id_empresa
    if empresa_id is None:
        raise HTTPException(status_code=400, detail="Usuario sin empresa asociada")
    q = _queues.get(empresa_id)
    if q is None:
        _queues[empresa_id] = [event]
    else:
        q.append(event)
    return {"status": "ok"}

@router.get("/evento/poll")
def poll_event(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    empresa_id = current_user.id_empresa
    if empresa_id is None:
        raise HTTPException(status_code=400, detail="Usuario sin empresa asociada")
    q = _queues.get(empresa_id)
    if not q:
        return {"has_event": False}
    event = q.pop(0)
    return {"has_event": True, "event": event.model_dump()}

@router.post("/evento/public")
def push_event_public(
    event: ScannerEvent,
    request: Request,
    db: Session = Depends(get_db)
):
    x_key = request.headers.get("X-Scanner-Key")
    empresa_id = _key_map().get(x_key or "")
    if not empresa_id:
        raise HTTPException(status_code=401, detail="Clave inválida")
    if not _allowed_ip(request):
        raise HTTPException(status_code=403, detail="IP no autorizada")
    q = _queues.get(empresa_id)
    if q is None:
        _queues[empresa_id] = [event]
    else:
        q.append(event)
    return {"status": "ok"}

@router.get("/evento/poll/public")
def poll_event_public(
    request: Request,
    db: Session = Depends(get_db)
):
    x_key = request.headers.get("X-Scanner-Key")
    empresa_id = _key_map().get(x_key or "")
    if not empresa_id:
        raise HTTPException(status_code=401, detail="Clave inválida")
    if not _allowed_ip(request):
        raise HTTPException(status_code=403, detail="IP no autorizada")
    q = _queues.get(empresa_id)
    if not q:
        return {"has_event": False}
    event = q.pop(0)
    return {"has_event": True, "event": event.model_dump()}
