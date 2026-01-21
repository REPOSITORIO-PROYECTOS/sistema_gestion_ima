from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class OrdenRead(BaseModel):
    id: int
    timestamp: datetime
    tipo: str
    estado: str
    total: float
    id_consumo_mesa: Optional[int] = None
    id_venta: Optional[int] = None
    numero_comprobante: Optional[str] = None
    id_usuario: int
    id_empresa: int

    class Config:
        from_attributes = True

class AuditLogRead(BaseModel):
    id: int
    timestamp: datetime
    accion: str
    entidad: str
    entidad_id: Optional[int] = None
    exito: bool
    detalles: Optional[Dict[str, Any]] = None
    id_usuario: int
    id_empresa: int

    class Config:
        from_attributes = True

class ReporteOrdenesRequest(BaseModel):
    desde: Optional[datetime] = None
    hasta: Optional[datetime] = None
    estado: Optional[str] = None
    tipo: Optional[str] = None

class ReporteOrdenesResponse(BaseModel):
    total_ordenes: int
    total_monto: float
    por_estado: Dict[str, int] = Field(default_factory=dict)
    por_tipo: Dict[str, int] = Field(default_factory=dict)
