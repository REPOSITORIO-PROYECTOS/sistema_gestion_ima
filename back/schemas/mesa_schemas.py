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
    id_articulo: int
    cantidad: float
    precio_unitario: float
    descuento_aplicado: Optional[float] = 0.0
    observacion: Optional[str] = None

class ConsumoMesaDetalleCreate(ConsumoMesaDetalleBase):
    pass

class ConsumoMesaDetalleRead(ConsumoMesaDetalleBase):
    id: int
    id_consumo_mesa: int
    impreso: bool = False

    class Config:
        from_attributes = True

# Schemas para Comandas Populated
class CategoriaSimple(BaseModel):
    nombre: str
    class Config:
        from_attributes = True

class ArticuloSimple(BaseModel):
    id: int
    descripcion: str
    categoria: Optional[CategoriaSimple] = None
    class Config:
        from_attributes = True

class ConsumoSimple(BaseModel):
    id: int
    id_mesa: int
    mesa: Optional[MesaRead] = None
    class Config:
        from_attributes = True

class ConsumoMesaDetallePopulated(ConsumoMesaDetalleRead):
    articulo: Optional[ArticuloSimple] = None
    consumo: Optional[ConsumoSimple] = None

class ConsumoMesaBase(BaseModel):
    total: float = Field(default=0.0)
    propina: float = Field(default=0.0)
    porcentaje_propina: float = Field(default=0.0)
    estado: str = Field(default="ABIERTO", description="Estado: ABIERTO, CERRADO, FACTURADO")

class ConsumoMesaCierreRequest(BaseModel):
    porcentaje_propina: float = Field(default=0.0, ge=0.0, description="Porcentaje de propina sugerido")

class ConsumoMesaFacturarRequest(BaseModel):
    metodo_pago: str = Field(default="Efectivo")
    cobrar_propina: bool = Field(default=True)



class ConsumoMesaCreate(ConsumoMesaBase):
    id_mesa: int

class ConsumoMesaUpdate(BaseModel):
    total: Optional[float] = None
    propina: Optional[float] = None
    porcentaje_propina: Optional[float] = None
    estado: Optional[str] = None
    timestamp_cierre: Optional[datetime] = None

class ConsumoMesaRead(ConsumoMesaBase):
    id: int
    timestamp_inicio: datetime
    timestamp_cierre: Optional[datetime]
    id_mesa: int
    id_usuario: int
    id_empresa: int
    detalles: List[ConsumoMesaDetallePopulated] = []

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

class MarcarImpresoRequest(BaseModel):
    ids_detalles: List[int]

class UnirMesasRequest(BaseModel):
    source_mesa_ids: List[int] = Field(alias="source_mes-ids")
    target_mesa_id: int = Field(alias="target_mes-id")

class ComandaPdfRequest(BaseModel):
    ids_detalles: Optional[List[int]] = None
    id_consumo_mesa: Optional[int] = None
    only_pendientes: Optional[bool] = False
