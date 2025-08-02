# /sistema_gestion_ima/back/schemas/venta_ciclo_de_vida_schemas.py

from pydantic import BaseModel, Field
from typing import List, Optional

# ===================================================================
# === SCHEMAS BASE (Reutilizables)
# ===================================================================

class VentaItemBase(BaseModel):
    """Define una línea de producto dentro de una venta."""
    id_articulo: int
    cantidad: float = Field(..., gt=0) # La cantidad debe ser mayor que cero
    precio_unitario: float = Field(..., ge=0) # El precio no puede ser negativo

class PagoBase(BaseModel):
    """Define una forma de pago para una venta."""
    metodo: str # Ej: "Efectivo", "Transferencia", "Tarjeta de Débito"
    monto: float = Field(..., gt=0) # El monto del pago debe ser positivo

# ===================================================================
# === SCHEMAS PARA PAYLOADS DE ENTRADA (Lo que envía el Frontend)
# ===================================================================

class VentaCreatePayload(BaseModel):
    """
    Payload para crear un comprobante inicial que no mueve stock ni caja.
    Típicamente, un 'Presupuesto'.
    """
    id_cliente: Optional[int] = None
    items: List[VentaItemBase]

class VentaDirectaPayload(BaseModel):
    """
    Payload para una venta completa desde la caja (Punto de Venta).
    Debe contener toda la información para crear la venta, descontar stock y registrar el pago.
    """
    id_cliente: Optional[int] = None
    tipo_comprobante: str # Ej: "Comprobante Interno", "Ticket Fiscal"
    id_caja_sesion: int
    items: List[VentaItemBase]
    pagos: List[PagoBase]

class TransicionPayload(BaseModel):
    """
    Payload para evolucionar un comprobante de un tipo a otro.
    Ej: de 'Presupuesto' a 'Remito', o de 'Remito' a 'Factura'.
    """
    nuevo_tipo: str
    id_caja_sesion: Optional[int] = None
    pagos: Optional[List[PagoBase]] = None

# ===================================================================
# === SCHEMAS DE SALIDA (Lo que la API devuelve al Frontend)
# ===================================================================

class VentaDetalleResponse(VentaItemBase):
    """Schema para mostrar una línea de producto en la respuesta."""
    id: int # El ID del registro VentaDetalle en la base de datos

    class Config:
        from_attributes = True # Permite que Pydantic lea desde un objeto ORM (SQLModel)

class VentaResponse(BaseModel):
    """
    Respuesta estandarizada y completa para cualquier operación de venta.
    Esta es la estructura que el frontend recibirá siempre.
    """
    id: int
    tipo_comprobante: str
    total: float
    activo: bool
    id_cliente: Optional[int]
    id_usuario: int
    id_caja_sesion: Optional[int]
    items: List[VentaDetalleResponse]

    class Config:
        from_attributes = True # Permite que Pydantic lea desde un objeto ORM (SQLModel)   