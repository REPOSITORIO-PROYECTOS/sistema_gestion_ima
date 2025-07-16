# back/api/blueprints/clientes_router.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from typing import List

from back.gestion.contabilidad.clientes_contabilidad import manager as clientes_manager
from back.database import get_db
from back.schemas.cliente_schemas import ClienteCreate, ClienteUpdate, ClienteResponse
from back.schemas.caja_schemas import RespuestaGenerica
# Importaremos la seguridad cuando esté lista
# from back.security import es_cajero

router = APIRouter(
    prefix="/clientes",
    tags=["Clientes"],
    # dependencies=[Depends(es_cajero)] # Seguridad desactivada temporalmente
)

@router.post("/crear", response_model=ClienteResponse, status_code=201)
def api_crear_cliente(req: ClienteCreate, db: Session = Depends(get_db)):
    """Crea un nuevo cliente directamente en la base de datos SQL."""
    try:
        return clientes_manager.crear_cliente(db, req.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/obtener-todos", response_model=List[ClienteResponse])
def api_obtener_clientes(
    db: Session = Depends(get_db),
    pagina: int = Query(1, ge=1),
    limite: int = Query(100, ge=1, le=200)
):
    """Obtiene una lista paginada de clientes desde la base de datos SQL."""
    skip = (pagina - 1) * limite
    return clientes_manager.obtener_todos_los_clientes(db, skip=skip, limit=limite)


@router.get("/obtener/{id_cliente}", response_model=ClienteResponse)
def api_obtener_cliente(id_cliente: int, db: Session = Depends(get_db)):
    """Obtiene un cliente específico por su ID desde la base de datos SQL."""
    cliente = clientes_manager.obtener_cliente_por_id(db, id_cliente)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    return cliente

@router.patch("/actualizar/{id_cliente}", response_model=ClienteResponse)
def api_actualizar_cliente(id_cliente: int, req: ClienteUpdate, db: Session = Depends(get_db)):
    """Actualiza los datos de un cliente en la base de datos SQL."""
    update_data = req.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No se enviaron datos para actualizar.")
    try:
        return clientes_manager.actualizar_cliente(db, id_cliente, update_data)
    except ValueError as e:
        status_code = 404 if "no encontrado" in str(e).lower() else 409
        raise HTTPException(status_code=status_code, detail=str(e))

@router.delete("/desactivar/{id_cliente}", response_model=RespuestaGenerica)
def api_desactivar_cliente(id_cliente: int, db: Session = Depends(get_db)):
    """Desactiva un cliente (borrado lógico) en la base de datos SQL."""
    try:
        clientes_manager.desactivar_cliente(db, id_cliente)
        return RespuestaGenerica(status="success", message="Cliente desactivado correctamente.")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))