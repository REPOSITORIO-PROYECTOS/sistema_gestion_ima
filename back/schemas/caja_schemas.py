# back/schemas/caja_schemas.py

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Schemas Genéricos ---
# Para evitar duplicación, podrías tener un 'base_schemas.py' para esta clase
class RespuestaGenerica(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None

# --- Schemas de Petición (Request) ---
class AbrirCajaRequest(BaseModel):
    saldo_inicial: float = Field(..., ge=0)

class CerrarCajaRequest(BaseModel):
    saldo_final_declarado: float = Field(..., ge=0)

class ArticuloVendido(BaseModel):
    id_articulo: int # Coincide con el ID de nuestra tabla Articulo
    cantidad: float = Field(..., gt=0)
    precio_unitario: float = Field(..., ge=0)

class RegistrarVentaRequest(BaseModel):
    id_cliente: Optional[int] = None # Coincide con el ID de nuestra tabla Tercero
    metodo_pago: str
    total_venta: float
    articulos_vendidos: List[ArticuloVendido]
    quiere_factura: bool = False
    tipo_comprobante_solicitado: Optional[str] = None

class MovimientoSimpleRequest(BaseModel):
    concepto: str
    monto: float = Field(..., gt=0)

# --- Schemas de Respuesta (Response) ---
class EstadoCajaResponse(BaseModel):
    caja_abierta: bool
    id_sesion: Optional[int] = None
    fecha_apertura: Optional[datetime] = None

class ArqueoCajaResponse(BaseModel):
    id_sesion: int
    fecha_apertura: datetime
    fecha_cierre: datetime | None
    usuario_apertura: str
    saldo_inicial: float
    saldo_final_declarado: float | None
    saldo_final_calculado: float | None
    diferencia: float | None