# /back/api/blueprints/importaciones_router.py

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import Session

# Dependencias y modelos
from back.database import get_db
from back.security import obtener_usuario_actual
from back.modelos import Usuario
from back.schemas.caja_schemas import RespuestaGenerica

# Lógica de negocio (Managers)
from back.gestion.stock import importacion_manager

# Schemas específicos
from back.schemas.importacion_schemas import ImportacionPreviewResponse, ConfirmacionImportacionRequest

router = APIRouter(prefix="/importaciones", tags=["Importación de Precios"])

@router.post("/preview/{id_proveedor}", response_model=ImportacionPreviewResponse)
async def previsualizar_importacion_de_precios(
    id_proveedor: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual),
    archivo: UploadFile = File(...)
):
    """
    Sube un archivo Excel de lista de precios de un proveedor.
    El sistema lo procesa usando la plantilla de mapeo configurada y devuelve
    una pre-visualización de los cambios de precios sin aplicar nada en la base de datos.
    """
    # Validamos que el proveedor pertenezca a la empresa.
    proveedor = db.get(importacion_manager.Tercero, id_proveedor)
    if not proveedor or proveedor.id_empresa != current_user.id_empresa:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado en esta empresa.")
        
    # Leemos el contenido del archivo en bytes.
    contenido_archivo = await archivo.read()

    try:
        # Llamamos al manager que hace todo el trabajo pesado.
        preview_response = importacion_manager.generar_previsualizacion_desde_archivo(
            db=db,
            id_proveedor=id_proveedor,
            id_empresa=current_user.id_empresa,
            archivo_bytes=contenido_archivo
        )
        return preview_response
    except ValueError as e:
        # Capturamos errores de lógica (ej: plantilla no encontrada, columnas faltantes)
        # y los convertimos en un error 400 Bad Request para el cliente.
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/confirmar", response_model=RespuestaGenerica)
def confirmar_importacion_de_precios(
    req: ConfirmacionImportacionRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    """
    Recibe la lista de artículos con sus nuevos precios (la que generó el endpoint
    de preview y que el usuario confirmó en el frontend) y los aplica
    definitivamente en la base de datos.
    """
    try:
        resultado = importacion_manager.aplicar_actualizacion_de_precios(
            db=db,
            id_empresa=current_user.id_empresa,
            confirmacion_data=req
        )
        return RespuestaGenerica(status=resultado["status"], message=resultado["message"])
    except Exception as e:
        # Captura de error genérica para problemas inesperados durante la transacción.
        raise HTTPException(status_code=500, detail=f"Ocurrió un error inesperado al actualizar los precios: {e}")