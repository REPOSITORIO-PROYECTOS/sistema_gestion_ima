# back/schemas/boleta_schemas.py
# VERSIÓN ADAPTADA PARA FUNCIONAR SIN CAMBIOS EN LA BASE DE DATOS

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class BoletaItemSchema(BaseModel):
    cantidad: float
    descripcion: str
    precio_unitario: float
    subtotal: float

class BoletaClienteSchema(BaseModel):
    nombre_razon_social: str
    identificacion_fiscal: Optional[str]
    condicion_iva: str
    direccion: Optional[str]

class BoletaResponse(BaseModel):
    """
    Representa un "Comprobante de Venta" o "Remito".
    No es válido como factura fiscal.
    """
    id_venta: int
    fecha_emision: datetime
    
    # Datos de la empresa (vendedor)
    vendedor_razon_social: str
    vendedor_cuit: str
    vendedor_direccion: str
    
    # Datos del cliente
    cliente: BoletaClienteSchema
    
    # Items de la venta
    items: List[BoletaItemSchema]
    total_final: float