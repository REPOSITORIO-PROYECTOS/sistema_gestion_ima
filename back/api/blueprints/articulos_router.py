# back/api/blueprints/articulos_router.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from typing import List

from back.database import get_db
from back.security import get_current_user, es_admin
from back.modelos import Articulo, Usuario
from back.gestion.stock import articulos as mod_articulos
from back.schemas.articulo_schemas import ArticuloCreate, ArticuloUpdate, ArticuloResponse
from back.schemas.caja_schemas import RespuestaGenerica

router = APIRouter(prefix="/articulos", tags=["Artículos"])

@router.get("/obtener_todos", response_model=List[Articulo])
def api_get_all_articulos(
    db: Session = Depends(get_db), 
    pagina: int = Query(1, ge=1, description="Número de página"), 
    limite: int = Query(100, ge=1, le=200, description="Tamaño de la página")
):
    # Calculamos el 'skip' (offset) a partir de la página y el límite
    skip = (pagina - 1) * limite
    
    # Llamamos a nuestra nueva función de lógica ORM
    lista_articulos = mod_articulos.obtener_todos_los_articulos_orm(db=db, skip=skip, limit=limite)
    
    return lista_articulos

@router.get("/obtener/{id_articulo}", response_model=ArticuloResponse)
def api_get_articulo(id_articulo: int, db: Session = Depends(get_db)):
    articulo_db = mod_articulos.obtener_articulo_por_id(db, id_articulo)
    if not articulo_db:
        raise HTTPException(status_code=404, detail=f"Artículo con ID {id_articulo} no encontrado.")
    return articulo_db

@router.post("/crear", response_model=ArticuloResponse, status_code=201, dependencies=[Depends(es_admin)])
def api_create_articulo(req: ArticuloCreate, db: Session = Depends(get_db)):
    return mod_articulos.crear_articulo(db, req.model_dump())

@router.patch("/actualizar/{id_articulo}", response_model=ArticuloResponse, dependencies=[Depends(es_admin)])
def api_update_articulo(id_articulo: int, req: ArticuloUpdate, db: Session = Depends(get_db)):
    update_data = req.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No se enviaron datos para actualizar.")
    try:
        return mod_articulos.actualizar_articulo(db, id_articulo, update_data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/eliminar/{id_articulo}", response_model=RespuestaGenerica, dependencies=[Depends(es_admin)])
def api_delete_articulo(id_articulo: int, db: Session = Depends(get_db)):
    try:
        mod_articulos.eliminar_articulo(db, id_articulo)
        return RespuestaGenerica(status="success", message=f"Artículo con ID {id_articulo} eliminado.")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))