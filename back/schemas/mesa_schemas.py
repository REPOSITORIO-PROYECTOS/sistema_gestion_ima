# back/schemas/mesa_schemas.py

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# ===================================================================
# === SCHEMAS PARA MESAS
# ===================================================================

class MesaBase(BaseModel):
    numero: int = Field(..., description="Número de la mesa")
    capacidad: int = Field(default=4, ge=1, description="Capacidad de personas")
    estado: str = Field(default="LIBRE", description="Estado: LIBRE, OCUPADA, RESERVADA")
    activo: bool = Field(default=True, description="Si la mesa está activa")

class MesaCreate(MesaBase):
    pass

class MesaUpdate(BaseModel):
    numero: Optional[int] = None
    capacidad: Optional[int] = None
    estado: Optional[str] = None
    activo: Optional[bool] = None

class MesaRead(MesaBase):
    id: int
    id_empresa: int

    class Config:
        from_attributes = True

# ===================================================================
# === SCHEMAS PARA CONSUMO EN MESAS
# ===================================================================

class ConsumoMesaDetalleBase(BaseModel):
    cantidad: float = Field(..., gt=0)
    precio_unitario: float
    descuento_aplicado: float = Field(default=0.0)
    id_articulo: int

class ConsumoMesaDetalleCreate(ConsumoMesaDetalleBase):
    pass

class ConsumoMesaDetalleRead(ConsumoMesaDetalleBase):
    id: int
    id_consumo_mesa: int

    class Config:
        from_attributes = True

class ConsumoMesaBase(BaseModel):
    total: float = Field(default=0.0)
    estado: str = Field(default="ABIERTO", description="Estado: ABIERTO, CERRADO, FACTURADO")

class ConsumoMesaCreate(ConsumoMesaBase):
    id_mesa: int

class ConsumoMesaUpdate(BaseModel):
    total: Optional[float] = None
    estado: Optional[str] = None
    timestamp_cierre: Optional[datetime] = None

class ConsumoMesaRead(ConsumoMesaBase):
    id: int
    timestamp_inicio: datetime
    timestamp_cierre: Optional[datetime]
    id_mesa: int
    id_usuario: int
    id_empresa: int
    detalles: List[ConsumoMesaDetalleRead] = []

    class Config:
        from_attributes = True

# ===================================================================
# === SCHEMAS PARA IMPRESIÓN DE TICKETS
# ===================================================================

class TicketMesaRequest(BaseModel):
    id_consumo_mesa: int
    formato: str = Field(default="ticket", description="Formato: ticket, comprobante")

class TicketResponse(BaseModel):
    ticket_html: str
    ticket_texto: str