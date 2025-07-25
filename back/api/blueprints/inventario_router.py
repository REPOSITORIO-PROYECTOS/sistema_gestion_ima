# back/api/blueprints/inventario_router.py

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import Session
from typing import List

from back.db.session import obtener_sesion
from back.security import es_gerente
from back.modelos import Usuario
import back.gestion.stock.articulos as articulos_manager
from back.schemas.articulo_schemas import ArticuloRead # Asumo que ya tienes este schema
# Importamos los nuevos managers y schemas
import back.gestion.stock.actualizacion_manager as actualizacion_manager
from back.schemas.inventario_schemas import PlantillaCreate, PlantillaRead, ResultadoActualizacion

router = APIRouter(
    prefix="/inventario",
    tags=["Inventario - Actualización de Precios"],
    dependencies=[Depends(es_gerente)]
)

# --- Endpoints para Gestión de Plantillas ---

@router.post("/proveedores/{proveedor_id}/crear-plantilla", response_model=PlantillaRead)
def crear_o_actualizar_plantilla_proveedor(
    proveedor_id: int,
    plantilla_data: PlantillaCreate,
    db: Session = Depends(obtener_sesion)
):
    """
    Crea o actualiza la plantilla de mapeo de columnas para un proveedor específico.
    """
    try:
        plantilla = actualizacion_manager.crear_o_actualizar_plantilla(db, proveedor_id, plantilla_data)
        return plantilla
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    

@router.get("/proveedores/{proveedor_id}/plantilla", response_model=PlantillaRead)
def obtener_plantilla_de_proveedor(
    proveedor_id: int,
    db: Session = Depends(obtener_sesion)
):
    """
    Obtiene la plantilla de importación guardada para un proveedor.
    """
    plantilla = actualizacion_manager.obtener_plantilla_por_proveedor(db, proveedor_id)
    if not plantilla:
        raise HTTPException(status_code=404, detail="No se encontró una plantilla para este proveedor.")
    return plantilla

# --- Endpoint para Procesar el Archivo ---

@router.post("/proveedores/{proveedor_id}/actualizar-precios", response_model=ResultadoActualizacion)
async def procesar_lista_de_precios(
    proveedor_id: int,
    archivo: UploadFile = File(...),
    db: Session = Depends(obtener_sesion)
):
    """
    Sube una lista de precios en formato Excel para un proveedor.
    El sistema utilizará la plantilla guardada para procesar el archivo,
    actualizar los precios de costo y devolver un informe del resultado.
    """
    if not archivo.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Formato de archivo no válido. Se requiere un archivo Excel (.xlsx, .xls).")
    
    try:
        resultado = actualizacion_manager.procesar_archivo_precios(db, proveedor_id, archivo)
        return resultado
    except ValueError as e:
        # Errores de negocio (plantilla no encontrada, columnas incorrectas, etc.)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Errores inesperados
        raise HTTPException(status_code=500, detail=f"Ocurrió un error inesperado al procesar el archivo: {e}")
    
@router.get("/buscar-por-codigo/{codigo_barras}", response_model=ArticuloRead)
def buscar_articulo_por_codigo(
    codigo_barras: str,
    db: Session = Depends(obtener_sesion)
):
    """
    Endpoint de alto rendimiento para ser usado por escáneres de códigos de barras.
    Recibe un código y devuelve los datos del artículo correspondiente.
    """
    articulo = articulos_manager.obtener_articulo_por_codigo_barras(db=db, codigo_barras=codigo_barras)
    
    if not articulo:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró un artículo activo con el código de barras '{codigo_barras}'."
        )
        
    return articulo

@router.post("/articulos/{articulo_id}/codigos")
def anadir_codigo_a_articulo_endpoint(
    articulo_id: int,
    codigo: str, # Simplificado para el ejemplo
    db: Session = Depends(obtener_sesion)
):
    try:
        nuevo_codigo = articulos_manager.anadir_codigo_a_articulo(db, articulo_id, codigo)
        return {"mensaje": "Código añadido exitosamente", "codigo": nuevo_codigo.codigo}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/articulos/codigos/{codigo_a_borrar}", status_code=204)
def eliminar_codigo_de_articulo_endpoint(
    codigo_a_borrar: str,
    db: Session = Depends(obtener_sesion)
):
    exito = articulos_manager.eliminar_codigo_de_articulo(db, codigo_a_borrar)
    if not exito:
        raise HTTPException(status_code=404, detail="Código de barras no encontrado.")