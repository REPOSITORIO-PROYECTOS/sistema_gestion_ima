from pydantic import BaseModel, Field
from typing import Optional, Dict, List

# === Schemas para las Plantillas de Mapeo (Sin cambios, pero necesarios para la relación) ===
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
        from_attributes = True

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
        from_attributes = True

class ProveedorReadConPlantilla(ProveedorRead):
    """
    Schema para leer un proveedor incluyendo su plantilla de mapeo, si existe.
    """
    plantilla_mapeo: Optional[PlantillaMapeoRead] = None
    class Config:
        from_attributes = True
        
class ArticuloProveedorLink(BaseModel):
    id_articulo: int
    codigo_articulo_proveedor: str

class ProveedorConArticulos(ProveedorRead):
    articulos_asociados: List[ArticuloProveedorLink] = []