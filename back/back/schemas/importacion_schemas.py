# /back/schemas/importacion_schemas.py

from pydantic import BaseModel
from typing import List, Optional

class ArticuloPreview(BaseModel):
    id_articulo: int
    codigo_interno: Optional[str]
    descripcion: str
    
    costo_actual: float
    costo_nuevo: float
    
    precio_venta_actual: float
    precio_venta_nuevo: float

class ImportacionPreviewResponse(BaseModel):
    articulos_a_actualizar: List[ArticuloPreview]
    articulos_no_encontrados: List[str] # Lista de códigos de proveedor que no se encontraron
    resumen: str # Ej: "Se encontraron 50 artículos para actualizar y 5 no fueron encontrados."

class ConfirmacionImportacionRequest(BaseModel):
    # El frontend envía de vuelta la lista de artículos que el usuario realmente quiere actualizar
    articulos_a_actualizar: List[ArticuloPreview]