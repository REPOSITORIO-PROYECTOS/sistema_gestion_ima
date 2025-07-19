# back/schemas/inventario_schemas.py

from pydantic import BaseModel, Field
from typing import Dict, List

# --- Schemas para la gestión de Plantillas de Proveedor ---

class PlantillaBase(BaseModel):
    nombre_plantilla: str = Field(..., example="Lista de Precios Estándar")
    # El mapeo: clave es nuestro campo, valor es la letra de la columna en el Excel.
    mapeo_columnas: Dict[str, str] = Field(..., example={"codigo_proveedor": "B", "precio_costo": "F"})

class PlantillaCreate(PlantillaBase):
    pass

class PlantillaRead(PlantillaBase):
    id: int
    id_proveedor: int

# --- Schema para el resultado del procesamiento del archivo ---

class ResultadoActualizacion(BaseModel):
    mensaje: str
    articulos_actualizados: int
    articulos_no_encontrados: List[str]
    variacion_promedio_porcentaje: float