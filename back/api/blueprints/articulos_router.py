# back/api/articulos_router.py

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional

# Importamos la lógica de negocio y los modelos Pydantic
from back.gestion.stock import articulos as mod_articulos
from back.api.blueprints.schemas import Articulo, ArticuloCreate, ArticuloUpdate, RespuestaGenerica
# Importamos nuestros guardianes de seguridad
from back.security import es_cajero, es_admin

router = APIRouter(
    prefix="/articulos",
    tags=["Artículos"],
    # Todas las operaciones de artículos requerirán al menos ser cajero
    dependencies=[Depends(es_cajero)]
)

@router.get("/", response_model=List[Articulo])
async def api_obtener_articulos(
    pagina: int = Query(1, ge=1),
    limite: int = Query(100, ge=1, le=200)
):
    """Obtiene una lista paginada de artículos."""
    articulos_db = mod_articulos.obtener_todos_los_articulos(limite=limite, pagina=pagina)
    return articulos_db

@router.get("/{id_articulo}", response_model=Articulo)
async def api_obtener_articulo(id_articulo: str):
    """Obtiene un artículo específico por su ID."""
    articulo_db = mod_articulos.obtener_articulo_por_id(id_articulo)
    if not articulo_db:
        raise HTTPException(status_code=404, detail=f"Artículo con ID {id_articulo} no encontrado.")
    return articulo_db

@router.post("/", response_model=RespuestaGenerica, status_code=201, dependencies=[Depends(es_admin)])
async def api_crear_articulo(articulo_data: ArticuloCreate):
    """Crea un nuevo artículo. Requiere permisos de administrador."""
    resultado = mod_articulos.crear_articulo(**articulo_data.dict())
    if resultado["status"] != "success":
        raise HTTPException(status_code=400, detail=resultado["message"])
    return resultado

@router.patch("/{id_articulo}", response_model=RespuestaGenerica, dependencies=[Depends(es_admin)])
async def api_actualizar_articulo(id_articulo: str, articulo_data: ArticuloUpdate):
    """Actualiza un artículo existente. Requiere permisos de administrador."""
    # .dict(exclude_unset=True) es clave: solo incluye los campos que el cliente envió
    update_data = articulo_data.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No se enviaron datos para actualizar.")
        
    resultado = mod_articulos.actualizar_articulo(id_articulo, **update_data)
    if resultado["status"] != "success":
        # Manejar caso de no encontrado de forma diferente a otros errores
        if "no encontrado" in resultado["message"]:
            raise HTTPException(status_code=404, detail=resultado["message"])
        raise HTTPException(status_code=400, detail=resultado["message"])
    return resultado

@router.delete("/{id_articulo}", response_model=RespuestaGenerica, dependencies=[Depends(es_admin)])
async def api_eliminar_articulo(id_articulo: str):
    """Elimina un artículo. Requiere permisos de administrador."""
    resultado = mod_articulos.eliminar_articulo(id_articulo)
    if resultado["status"] != "success":
        if "no encontrado" in resultado["message"]:
            raise HTTPException(status_code=404, detail=resultado["message"])
        raise HTTPException(status_code=400, detail=resultado["message"])
    return resultado