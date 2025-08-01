# /back/schemas/proveedor_schemas.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, List

# === Schemas para Tercero (Proveedor) ===
class ProveedorBase(BaseModel):
    nombre_razon_social: str
    nombre_fantasia: Optional[str] = None
    cuit: Optional[str] = None
    condicion_iva: str
    email: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    notas: Optional[str] = None

class ProveedorCreate(ProveedorBase):
    pass # Hereda todos los campos

class ProveedorRead(ProveedorBase):
    id: int
    activo: bool

    class Config:
        orm_mode = True

# === Schemas para la Asociación Artículo-Proveedor ===
class ArticuloProveedorLink(BaseModel):
    id_articulo: int
    codigo_articulo_proveedor: str

class ProveedorConArticulos(ProveedorRead):
    articulos_asociados: List[ArticuloProveedorLink] = []

# === Schemas para las Plantillas de Mapeo ===
class PlantillaMapeoBase(BaseModel):
    nombre_plantilla: str
    mapeo_columnas: Dict[str, str] = Field(
        ..., 
        example={"CODIGO_PROV": "codigo_articulo_proveedor", "PRECIO_COSTO": "precio_costo"}
    )
    nombre_hoja_excel: Optional[str] = None
    fila_inicio: int = 2

class PlantillaMapeoCreate(PlantillaMapeoBase):
    id_proveedor: int

class PlantillaMapeoRead(PlantillaMapeoBase):
    id: int
    id_proveedor: int
    
    class Config:
        orm_mode = True