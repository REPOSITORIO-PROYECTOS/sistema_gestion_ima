# back/api/blueprints/articulos_router.py
# VERSIÓN FINAL ADAPTADA A LOS NUEVOS SCHEMAS Y MANTENIENDO RUTAS ORIGINALES

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlmodel import Session
from typing import List

# --- Módulos del Proyecto ---
from back.database import get_db
from back.security import es_admin, obtener_usuario_actual
from back.modelos import Usuario
import back.gestion.stock.articulos as articulos_manager
# --- ¡IMPORTACIONES CORREGIDAS SEGÚN SU NUEVO ARCHIVO! ---
from back.schemas.articulo_schemas import (
    ArticuloCreate, 
    ArticuloUpdate, 
    ArticuloResponse, # Lo mantenemos si alguna parte antigua aún lo usa
    ArticuloReadConCodigos, 
    CodigoBarrasCreate
)
from back.schemas.articulo_schemas import ArticuloRead
from back.schemas.caja_schemas import RespuestaGenerica

router = APIRouter(
    prefix="/articulos", 
    tags=["Artículos y Stock"]
)

# ===================================================================
# === ENDPOINTS DE LECTURA (GET) - Rutas mantenidas
# ===================================================================

@router.get("/obtener_todos", response_model=List[ArticuloReadConCodigos])
def api_get_all_articulos(
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
    pagina: int = Query(1, ge=1), 
    limite: int = Query(100, ge=1, le=200)
):
    """Obtiene una lista paginada de todos los artículos de la empresa del usuario."""
    skip = (pagina - 1) * limite
    lista_articulos = articulos_manager.obtener_todos_los_articulos(
        db=db, 
        id_empresa_actual=current_user.id_empresa, 
        skip=skip, 
        limit=limite
    )

    # --- INICIO DEL BLOQUE DE DEPURACIÓN ---
    # Este bloque intentará validar los datos antes de que FastAPI lo haga,
    # para que podamos capturar y registrar cualquier error de Pydantic.
    try:
        # Validamos manualmente cada artículo contra el schema de respuesta.
        # Esto simula lo que FastAPI hace internamente.
        for articulo in lista_articulos:
            ArticuloReadConCodigos.model_validate(articulo)
        
        # Si todos los artículos son válidos, los retornamos normalmente.
        return lista_articulos

    except ValidationError as e:
        # ¡AQUÍ ATRAPAMOS AL CULPABLE!
        print("!!!!!!!!!!!!!! ERROR DE VALIDACIÓN DE PYDANTIC DETECTADO !!!!!!!!!!!!!!")
        # Imprimimos el error en un formato JSON muy detallado en los logs del servidor.
        print(e.json(indent=2))
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        
        # Lanzamos una excepción HTTP 500 para que el proceso no se cierre.
        # Esto estabilizará la aplicación y evitará el bucle de reinicios.
        raise HTTPException(
            status_code=500, 
            detail="Error de validación en el servidor al procesar la lista de artículos. Revisar logs."
        )

@router.get("/obtener/{id_articulo}", response_model=ArticuloReadConCodigos)
def api_get_articulo(
    id_articulo: int,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    """Obtiene un artículo específico por su ID, verificando que pertenezca a la empresa del usuario."""
    try:
        articulo_db = articulos_manager.obtener_articulo_por_id(db, current_user.id_empresa, id_articulo)
        if not articulo_db:
            raise HTTPException(status_code=404, detail=f"Artículo con ID {id_articulo} no encontrado en su empresa.")
        return articulo_db
    except ValidationError as e:
        print("!!!!!!!!!!!!!! ERROR DE VALIDACIÓN DE PYDANTIC (GET ARTICULO) !!!!!!!!!!!!!!")
        print(e.json(indent=2))
        raise HTTPException(status_code=500, detail="Error de validación interna al obtener el artículo.")

# ===================================================================
# === ENDPOINTS DE ESCRITURA (CREATE, UPDATE, DELETE) - Rutas mantenidas
# ===================================================================

@router.post("/crear", response_model=ArticuloResponse, status_code=201, dependencies=[Depends(es_admin)])
def api_create_articulo(
    req: ArticuloCreate,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    """Crea un nuevo artículo para la empresa del usuario."""
    try:
        nuevo_articulo = articulos_manager.crear_articulo(db, current_user.id_empresa, req)
        return nuevo_articulo
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.patch("/actualizar/{id_articulo}", response_model=ArticuloResponse, dependencies=[Depends(es_admin)])
def api_update_articulo(
    id_articulo: int,
    req: ArticuloUpdate,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    """Actualiza un artículo existente de la empresa del usuario."""
    articulo_actualizado = articulos_manager.actualizar_articulo(db, current_user.id_empresa, id_articulo, req)
    if not articulo_actualizado:
        raise HTTPException(status_code=404, detail=f"Artículo con ID {id_articulo} no encontrado en su empresa.")
    return articulo_actualizado

@router.delete("/eliminar/{id_articulo}", response_model=RespuestaGenerica, dependencies=[Depends(es_admin)])
def api_delete_articulo(
    id_articulo: int,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    """Marca un artículo de la empresa del usuario como inactivo (eliminación lógica)."""
    articulo_eliminado = articulos_manager.eliminar_articulo(db, current_user.id_empresa, id_articulo)
    if not articulo_eliminado:
        raise HTTPException(status_code=404, detail=f"Artículo con ID {id_articulo} no encontrado en su empresa.")
    return RespuestaGenerica(status="success", message=f"Artículo '{articulo_eliminado.descripcion}' marcado como inactivo.")

# ===================================================================
# === NUEVOS ENDPOINTS PARA GESTIÓN DE CÓDIGOS DE BARRAS
# ===================================================================

@router.post("/codigos/anadir", status_code=201, summary="Añadir un nuevo código de barras", dependencies=[Depends(es_admin)])
def api_anadir_codigo(
    req: CodigoBarrasCreate,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    """Añade un nuevo código de barras a un artículo existente en la empresa del usuario."""
    # Verificamos que el artículo al que se le añade el código pertenezca a la empresa
    articulo = articulos_manager.obtener_articulo_por_id(db, current_user.id_empresa, req.id_articulo)
    if not articulo:
        raise HTTPException(status_code=404, detail=f"Artículo con ID {req.id_articulo} no encontrado en su empresa.")
    
    try:
        articulos_manager.anadir_codigo_a_articulo(db, req.id_articulo, req.codigo)
        return {"status": "success", "message": f"Código '{req.codigo}' añadido con éxito."}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.delete("/codigos/eliminar/{codigo}", response_model=RespuestaGenerica, summary="Eliminar un código de barras", dependencies=[Depends(es_admin)])
def api_eliminar_codigo(
    codigo: str,
    # No es necesario current_user aquí si la lógica del manager no lo requiere,
    # pero la protección de rol ya se ha ejecutado.
    db: Session = Depends(get_db)
):
    """
    Elimina un código de barras del sistema.
    (Nota: Esta operación no verifica la pertenencia a la empresa, ya que los códigos son únicos globalmente).
    """
    eliminado = articulos_manager.eliminar_codigo_de_articulo(db, codigo)
    if not eliminado:
        raise HTTPException(status_code=404, detail=f"Código '{codigo}' no encontrado.")
    return RespuestaGenerica(status="success", message=f"Código '{codigo}' eliminado.")


@router.get("/codigos/buscar/{codigo}", response_model=ArticuloReadConCodigos, summary="Obtener artículo por código de barras")
def api_buscar_articulo_por_codigo(
    codigo: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    """
    Busca un artículo por su código de barras.
    """
    id_empresa = current_user.id_empresa
    articulo = articulos_manager.buscar_articulo_por_codigo(db,id_empresa, codigo)
    if not articulo:
        raise HTTPException(status_code=404, detail=f"Artículo con código '{codigo}' no encontrado.")
    return articulo