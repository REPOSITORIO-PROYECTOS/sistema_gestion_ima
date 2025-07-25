# back/schemas/comprobante_schemas.py

from pydantic import BaseModel, Field
from typing import List, Literal, Optional

# --- Definición de Tipos ---
TipoFormato = Literal["pdf", "ticket"]
TipoComprobante = Literal["factura", "remito", "presupuesto", "recibo"]

# --- Estructuras de Datos ---

class EmisorData(BaseModel):
    cuit: str
    razon_social: str
    domicilio: str
    punto_venta: int
    condicion_iva: str # Ej: "Monotributo", "Responsable Inscripto"
    # Las credenciales ahora viajan en cada petición
    afip_certificado: Optional[str] = None
    afip_clave_privada: Optional[str] = None

class ReceptorData(BaseModel):
    nombre_razon_social: str
    cuit_o_dni: str
    domicilio: str
    condicion_iva: str # Ej: "Consumidor Final", "Responsable Inscripto"

class ItemData(BaseModel):
    cantidad: float
    descripcion: str
    precio_unitario: float
    subtotal: float

class TransaccionData(BaseModel):
    items: List[ItemData]
    total: float
    descuento_general: Optional[float] = 0.0
    descuento_especifico: Optional[float] = 0.0
    impuestos: Optional[float] = 0.0
    observaciones: Optional[str] = None
    

# --- El Schema Principal de la Petición ---

class GenerarComprobanteRequest(BaseModel):
    formato: TipoFormato
    tipo: TipoComprobante
    emisor: EmisorData
    receptor: ReceptorData
    transaccion: TransaccionData