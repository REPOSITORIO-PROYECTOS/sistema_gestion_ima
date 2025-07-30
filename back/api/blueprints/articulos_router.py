# back/api/blueprints/articulos_router.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from typing import List

from back.database import get_db
from back.security import es_admin, obtener_usuario_actual
from back.modelos import Articulo, Usuario # <-- Ya no necesitamos Usuario aquí
from back.gestion.stock import articulos as mod_articulos
from back.schemas.articulo_schemas import ArticuloCreate, ArticuloUpdate, ArticuloResponse
from back.schemas.caja_schemas import RespuestaGenerica

router = APIRouter(prefix="/articulos", tags=["Artículos"])

@router.get("/obtener_todos", response_model=List[ArticuloResponse]) # <-- CORRECCIÓN: Usamos el schema de respuesta
def api_get_all_articulos(
    db: Session = Depends(get_db), 
    current_user: Usuario = Depends(obtener_usuario_actual),
    pagina: int = Query(1, ge=1, description="Número de página"), 
    limite: int = Query(100, ge=1, le=200, description="Tamaño de la página")
):
    skip = (pagina - 1) * limite
    id_empresa = current_user.id_empresa
    # --- CORRECCIÓN: Llamamos a la función con el nombre correcto ---
    lista_articulos = mod_articulos.obtener_todos_los_articulos(id_empresa,db=db, skip=skip, limit=limite)
    
    return lista_articulos


@router.get("/obtener/{id_articulo}", response_model=ArticuloResponse)
def api_get_articulo(id_articulo: int, db: Session = Depends(get_db),current_user: Usuario = Depends(obtener_usuario_actual)):
    # Esta función ya era compatible, no necesita cambios.
    id_empresa = current_user.id_empresa

    articulo_db = mod_articulos.obtener_articulo_por_id(id_empresa,db, id_articulo)
    if not articulo_db:
        raise HTTPException(status_code=404, detail=f"Artículo con ID {id_articulo} no encontrado.")
    return articulo_db


@router.post("/crear", response_model=ArticuloResponse, status_code=201, dependencies=[Depends(es_admin)])
def api_create_articulo(req: ArticuloCreate, db: Session = Depends(get_db),current_user: Usuario = Depends(obtener_usuario_actual)):
    try:
        # --- CORRECCIÓN: Pasamos el objeto del schema 'req' directamente, sin .model_dump() ---
        id_empresa = current_user.id_empresa
        nuevo_articulo = mod_articulos.crear_articulo(id_empresa,db, req)
        return nuevo_articulo
    except ValueError as e:
        # El manager ahora lanza ValueError para códigos duplicados, lo capturamos aquí.
        raise HTTPException(status_code=409, detail=str(e)) # 409 Conflict es más apropiado
    

@router.patch("/actualizar/{id_articulo}", response_model=ArticuloResponse, dependencies=[Depends(es_admin)])
def api_update_articulo(id_articulo: int, req: ArticuloUpdate, db: Session = Depends(get_db),current_user: Usuario = Depends(obtener_usuario_actual)):
    try:
        id_empresa = current_user.id_empresa
        # --- CORRECCIÓN: Pasamos el objeto del schema 'req' directamente ---
        articulo_actualizado = mod_articulos.actualizar_articulo(id_empresa,db, id_articulo, req)
        
        if not articulo_actualizado:
            # Esta comprobación es más robusta
            raise HTTPException(status_code=404, detail=f"Artículo con ID {id_articulo} no encontrado.")
            
        return articulo_actualizado
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    

@router.delete("/eliminar/{id_articulo}", response_model=RespuestaGenerica, dependencies=[Depends(es_admin)])
def api_delete_articulo(id_articulo: int, db: Session = Depends(get_db)):
    # --- CORRECCIÓN: La lógica ahora comprueba la respuesta del manager ---
    articulo_eliminado = mod_articulos.eliminar_articulo(db, id_articulo)
    
    if not articulo_eliminado:
        raise HTTPException(status_code=404, detail=f"Artículo con ID {id_articulo} no encontrado.")
        
    return RespuestaGenerica(status="success", message=f"Artículo con ID {id_articulo} marcado como inactivo.")