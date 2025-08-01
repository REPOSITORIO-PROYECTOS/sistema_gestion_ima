# back/api/blueprints/clientes_router.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from typing import List

from back.gestion.contabilidad.clientes_contabilidad import manager as clientes_manager
from back.database import get_db
from back.modelos import Usuario
from back.schemas.cliente_schemas import ClienteCreate, ClienteUpdate, ClienteResponse
from back.schemas.caja_schemas import RespuestaGenerica
from back.security import obtener_usuario_actual
# Importaremos la seguridad cuando esté lista
# from back.security import es_cajero

router = APIRouter(
    prefix="/clientes",
    tags=["Clientes"],
    # dependencies=[Depends(es_cajero)] # Seguridad desactivada temporalmente
)

@router.post("/crear", response_model=ClienteResponse, status_code=201)
def api_crear_cliente(req: ClienteCreate, db: Session = Depends(get_db),current_user: Usuario = Depends(obtener_usuario_actual)):
    """Crea un nuevo cliente directamente en la base de datos SQL."""
    try:
        id_empresa = current_user.id_empresa
        return clientes_manager.crear_cliente(id_empresa,db, req.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/obtener-todos", response_model=List[ClienteResponse])
def api_obtener_clientes(db: Session = Depends(get_db),current_user: Usuario = Depends(obtener_usuario_actual)):
    """
    Obtiene la lista COMPLETA de todos los clientes activos, sin paginación.
    
    ADVERTENCIA: Si la base de datos tiene miles de clientes, esta
    operación puede ser lenta y consumir mucha memoria.
    """
    # La llamada a la lógica de negocio ahora es más simple, sin parámetros.
    id_empresa = current_user.id_empresa
    lista_clientes_db = clientes_manager.obtener_todos_los_clientes(id_empresa,db)
    
    return lista_clientes_db


@router.get("/obtener/{id_cliente}", response_model=ClienteResponse)
def api_obtener_cliente(id_cliente: int, db: Session = Depends(get_db),current_user: Usuario = Depends(obtener_usuario_actual)):
    """Obtiene un cliente específico por su ID desde la base de datos SQL."""
    id_empresa = current_user.id_empresa
    cliente = clientes_manager.obtener_cliente_por_id(id_empresa,db, id_cliente)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    return cliente

@router.patch("/actualizar/{id_cliente}", response_model=ClienteResponse)
def api_actualizar_cliente(id_cliente: int, req: ClienteUpdate, db: Session = Depends(get_db),current_user: Usuario = Depends(obtener_usuario_actual)):
    """Actualiza los datos de un cliente en la base de datos SQL."""
    update_data = req.model_dump(exclude_unset=True)
    id_empresa = current_user.id_empresa
    if not update_data:
        raise HTTPException(status_code=400, detail="No se enviaron datos para actualizar.")
    try:
        return clientes_manager.actualizar_cliente(id_empresa,db, id_cliente, update_data)
    except ValueError as e:
        status_code = 404 if "no encontrado" in str(e).lower() else 409
        raise HTTPException(status_code=status_code, detail=str(e))

@router.delete("/desactivar/{id_cliente}", response_model=RespuestaGenerica)
def api_desactivar_cliente(id_cliente: int, db: Session = Depends(get_db),current_user: Usuario = Depends(obtener_usuario_actual)):
    """Desactiva un cliente (borrado lógico) en la base de datos SQL."""
    try:
        id_empresa = current_user.id_empresa
        clientes_manager.desactivar_cliente(id_empresa,id_empresa,db, id_cliente)
        return RespuestaGenerica(status="success", message="Cliente desactivado correctamente.")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))