# back/schemas/caja_schemas.py
# VERSIÓN FINAL Y SINCRONIZADA

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Schemas Genéricos ---
class RespuestaGenerica(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None

class AbrirCajaRequest(BaseModel):
    saldo_inicial: float = Field(..., ge=0)
   

class CerrarCajaRequest(BaseModel):
    saldo_final_declarado: float = Field(..., ge=0)

class ArticuloVendido(BaseModel):
    id_articulo: int
    cantidad: float = Field(..., gt=0)
    precio_unitario: float = Field(..., ge=0)

class RegistrarVentaRequest(BaseModel):
    id_cliente: Optional[int] = None
    metodo_pago: str
    total_venta: float
    articulos_vendidos: List[ArticuloVendido]
    quiere_factura: bool = False
    tipo_comprobante_solicitado: Optional[str] = None

class MovimientoSimpleRequest(BaseModel):
    concepto: str
    monto: float = Field(..., gt=0)


class EstadoCajaResponse(BaseModel):
    caja_abierta: bool
    id_sesion: Optional[int] = None
    fecha_apertura: Optional[datetime] = None

class CajaSesionResponse(BaseModel):
    id: int
    fecha_apertura: datetime
    saldo_inicial: float
    fecha_cierre: Optional[datetime] = None
    saldo_final_declarado: Optional[float] = None
    saldo_final_calculado: Optional[float] = None
    diferencia: Optional[float] = None
    estado: str
    id_usuario_apertura: int
    id_usuario_cierre: Optional[int] = None

    class Config:
        from_attributes = True # Permite crear este schema desde un objeto SQLModel

class ArqueoCajaResponse(BaseModel):
    # Este schema ya estaba bien para su propósito.
    id_sesion: int
    fecha_apertura: datetime
    fecha_cierre: datetime | None
    usuario_apertura: str
    saldo_inicial: float
    saldo_final_declarado: float | None
    saldo_final_calculado: float | None
    diferencia: float | None
    
    
class CajaAbiertaResponse(BaseModel):
    id_sesion: int
    fecha_apertura: datetime
    usuario_apertura: str
    saldo_inicial: float
    estadi: str

class ArqueoCerradoResponse(BaseModel):
    id_sesion: int
    fecha_apertura: datetime
    fecha_cierre: datetime | None
    usuario_apertura: str
    usuario_cierre: str | None
    saldo_inicial: float
    saldo_final_declarado: float | None
    saldo_final_calculado: float | None
    diferencia: float | None
    estado: str

class InformeCajasResponse(BaseModel):
    cajas_abiertas: List[CajaAbiertaResponse]
    arqueos_cerrados: List[ArqueoCerradoResponse]