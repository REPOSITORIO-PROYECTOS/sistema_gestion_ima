# back/api/schemas.py (añadir estas clases)

from pydantic import BaseModel, Field
from typing import Dict, List, Optional
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


class AbrirCajaRequest(BaseModel):
    saldo_inicial: float = Field(..., gt=-0.00001)
    usuario: str

class SesionInfo(BaseModel):
    id_sesion: int
    usuario_apertura: Optional[str] = None
    fecha_apertura: Optional[str] = None
    saldo_inicial: Optional[float] = None

class EstadoCajaResponse(BaseModel):
    status: str
    caja_abierta: bool
    sesion_info: Optional[SesionInfo] = None
    message: Optional[str] = None

class ArticuloVendido(BaseModel):
    id_articulo: str
    nombre: Optional[str] = None
    cantidad: int = Field(..., gt=0)
    precio_unitario: float = Field(..., ge=0)
    subtotal: float

class RegistrarVentaRequest(BaseModel):
    id_sesion_caja: int
    id_cliente: int 
    id_usuario: int
    articulos_vendidos: List[ArticuloVendido]
    metodo_pago: str
    total_venta: float
    quiere_factura: bool
    tipo_comprobante_solicitado: str
class MovimientoCajaRequest(BaseModel):
    id_sesion_caja: int
    concepto: str # Renombrado de 'descripcion' para coincidir con el backend
    monto: float = Field(..., gt=0)
    usuario: str

class CerrarCajaRequest(BaseModel):
    id_sesion: int
    saldo_final_contado: float = Field(..., ge=0)
    usuario_cierre: str
    # token_admin: str # El token se manejará por dependencia, no en el cuerpo
