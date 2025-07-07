# back/api/schemas.py (añadir estas clases)

from pydantic import BaseModel
from typing import Optional
from typing import Any 
class Articulo(BaseModel):
    id_articulo: str
    descripcion: str
    precio_venta: float
    stock: int
    costo_ultimo: Optional[float] = None
    categoria: Optional[str] = None
    
    class Config:
        from_attributes = True # Permite que Pydantic lea datos desde objetos de DB

class ArticuloCreate(BaseModel):
    id_articulo: str
    descripcion: str
    precio_venta: float
    stock_inicial: Optional[int] = 0
    costo_ultimo: Optional[float] = 0.0
    categoria: Optional[str] = None

class ArticuloUpdate(BaseModel):
    # Todos los campos son opcionales para la actualización
    descripcion: Optional[str] = None
    precio_venta: Optional[float] = None
    costo_ultimo: Optional[float] = None
    categoria: Optional[str] = None

class RespuestaGenerica(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None