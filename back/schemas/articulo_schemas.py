# back/schemas/articulo_schemas.py

from pydantic import BaseModel, Field
from typing import Optional, Any, List

class ArticuloBase(BaseModel):
    """Schema base con los campos comunes de un artículo."""
    descripcion: str
    precio_venta: float
    venta_negocio : float
    costo_ultimo: Optional[float] = 0.0
    categoria: Optional[str] = None
    # El ID de artículo del sistema viejo lo manejaremos en un campo específico si es necesario
    # id_articulo_legacy: Optional[str] = None

class ArticuloCreate(ArticuloBase):
    """Schema para crear un nuevo artículo."""
    stock_inicial: float = Field(default=0.0, ge=0) # Usamos float para consistencia con el modelo de DB

class ArticuloUpdate(BaseModel):
    """Schema para actualizar un artículo. Todos los campos son opcionales."""
    descripcion: Optional[str] = None
    precio_venta: Optional[float] = None
    costo_ultimo: Optional[float] = None
    categoria: Optional[str] = None

class ArticuloResponse(ArticuloBase):
    """Schema para devolver un artículo en una respuesta de la API."""
    id: int # El ID autoincremental de nuestra nueva base de datos
    stock_actual: float
    activo: bool

    class Config:
        from_attributes = True # Permite que Pydantic lea datos desde objetos de DB
        
class ArticuloCodigoRead(BaseModel):
    codigo: str

    class Config:
        from_attributes = True
        
class ArticuloRead(ArticuloBase):
    """Schema para devolver un artículo en una respuesta. NO incluye los códigos."""
    id: int
    codigo_interno: Optional[str]
    stock_actual: float
    activo: bool

    class Config:
        from_attributes = True 

class ArticuloReadConCodigos(ArticuloRead):
    """
    ¡EL SCHEMA CLAVE PARA LA NUEVA FUNCIONALIDAD!
    Hereda todo de ArticuloRead y le AÑADE el campo que nos faltaba.
    """
    codigos: List[ArticuloCodigoRead] = []
    
class CodigoBarrasCreate(BaseModel):
    id_articulo: int
    codigo: str


