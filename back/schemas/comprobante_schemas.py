# back/schemas/comprobante_schemas.py

from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict, Any

# --- Definición de Tipos ---
TipoFormato = Literal["pdf", "ticket"]
TipoComprobante = Literal["factura", "remito", "presupuesto", "recibo"]

# --- Estructuras de Datos ---

class EmisorData(BaseModel):
    """
    Contiene los DATOS PÚBLICOS del emisor. 
    Los secretos (certificado, clave) se obtienen de la bóveda y NO viajan aquí.
    """
    cuit: str
    # Los siguientes campos ahora son requeridos, ya que la BBDD los provee.
    razon_social: Optional[str] = None # Hacemos opcionales por si la BDD no los tiene
    domicilio: Optional[str] = None
    punto_venta: int
    condicion_iva: Optional[str] = None

class ReceptorData(BaseModel):
    nombre_razon_social: Optional[str] = None # Hacemos opcional para "Consumidor Final" genérico
    cuit_o_dni: Optional[str] = None
    domicilio: Optional[str] = None
    condicion_iva: Optional[str] = None

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
    datos_factura_previa: Optional[Dict[str, Any]] = None

# --- El Schema Principal de la Petición ---

class GenerarComprobanteRequest(BaseModel):
    formato: TipoFormato
    tipo: TipoComprobante
    emisor: EmisorData
    receptor: ReceptorData
    transaccion: TransaccionData
    
class FacturarLoteRequest(BaseModel):
    # Una lista de IDs de CajaMovimiento (de tipo VENTA) que se quieren facturar.
    ids_movimientos: List[int] = Field(..., min_length=1)
    
    # El ID del cliente al que se le va a facturar.
    # Si es None o no se envía, se asume "Consumidor Final".
    id_cliente_final: Optional[int] = None

class FacturarLoteResponse(BaseModel):
    status: str
    mensaje: str
    datos_factura: Dict[str, Any] # La respuesta de AFIP (CAE, nro, etc.)
    ids_procesados: List[int]