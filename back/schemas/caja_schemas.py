# back/schemas/caja_schemas.py
# VERSIÓN FINAL Y SINCRONIZADA

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

# --- Enum para Tipo de Movimiento ---
class TipoMovimiento(str, Enum):
    VENTA = "VENTA"
    INGRESO = "INGRESO"
    EGRESO = "EGRESO"
    
# --- Schemas Genéricos ---
class RespuestaGenerica(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None

class AbrirCajaRequest(BaseModel):
    saldo_inicial: float = Field(..., ge=0)
   

class CerrarCajaRequest(BaseModel):
    saldo_final_declarado: float = Field(..., ge=0)
    saldo_final_transferencias: float
    saldo_final_bancario: float
    saldo_final_efectivo: float

class ArticuloVendido(BaseModel):
    id_articulo: int
    cantidad: float = Field(..., gt=0)
    precio_unitario: float = Field(..., ge=0)
    descuento_especifico: Optional[float] = 0.0
    descuento_especifico_por: Optional[float] = 0.0

class PagoMultiple(BaseModel):
    """Representa un pago individual en una transacción con múltiples medios de pago."""
    metodo_pago: str = Field(..., description="Efectivo, Transferencia, POS, etc.")
    monto: float = Field(..., gt=0, description="Monto en este método de pago")

class RegistrarVentaRequest(BaseModel):
    id_cliente: Optional[int] = None
    metodo_pago: Optional[str] = None  # Para retrocompatibilidad (si viene un solo método)
    pagos_multiples: Optional[List[PagoMultiple]] = None  # Nueva forma: múltiples pagos
    total_venta: float
    descuento_total: Optional[float] = 0.0
    paga_con: float
    articulos_vendidos: List[ArticuloVendido]
    quiere_factura: bool = False
    tipo_comprobante_solicitado: Optional[str] = None
    pago_separado: Optional[bool] = None
    detalles_pago_separado: Optional[str] = None

class ConsumoMesaFacturarRequest(BaseModel):
    metodo_pago: str
    cobrar_propina: bool = False

class CajaMovimientoResponse(BaseModel):
    id: int
    id_sesion_caja: int # Renombramos para consistencia
    id_venta_asociada: Optional[int] = None # Para saber si viene de una venta
    id_usuario: int
    tipo: str # <-- ESENCIAL: Para saber si es VENTA, INGRESO o EGRESO
    concepto: str
    monto: float
    metodo_pago: Optional[str] = None
    fecha_hora: datetime # <-- ESENCIAL: Para poder ordenar por fecha
    facturado: bool # <-- CLAVE: Para tu filtro de facturación

    class Config:
        from_attributes = True

class MovimientoSimpleRequest(BaseModel):
    concepto: str
    monto: float = Field(..., ge=0)
    metodo_pago: Optional[str] = None


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
    estado: str

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
    saldo_final_declarado: Optional[float] = Field(..., ge=0)
    saldo_final_transferencias: Optional[float] = None
    saldo_final_bancario: Optional[float] = None
    saldo_final_efectivo: Optional[float] = None


class InformeCajasResponse(BaseModel):
    cajas_abiertas: List[CajaAbiertaResponse]
    arqueos_cerrados: List[ArqueoCerradoResponse]
    
    
class ListaMovimientosResponse(BaseModel):
    total: int
    movimientos: List[CajaMovimientoResponse]
    
class _InfoClienteAnidado(BaseModel):
    """
    Sub-schema privado para representar solo los datos del cliente que necesitamos
    dentro de la respuesta del movimiento.
    """
    id: int
    nombre_razon_social: str

class _InfoUsuarioMovimiento(BaseModel):
    """
    Sub-schema privado para representar al usuario que realizó el movimiento.
    """
    nombre_usuario: str
    # nombre_completo no existe en el modelo Usuario actual


class _InfoVentaAnidada(BaseModel):
    """
    Sub-schema privado para anidar la información clave de la venta.
    """
    id: int
    facturada: bool
    descuento_total: float = 0.0
    datos_factura: Optional[Dict[str, Any]] = None
    tipo_comprobante_solicitado: Optional[str] = None
    cliente: Optional[_InfoClienteAnidado] = None

class MovimientoContableResponse(BaseModel):
    """
    El schema principal de respuesta para cada fila del 'Libro Mayor de Caja'.
    Representa un movimiento (ingreso, egreso o venta) con toda la información
    relevante para el frontend.
    """
    # --- Datos del Movimiento (siempre presentes) ---
    id: int
    timestamp: datetime # Usamos 'timestamp' para coincidir con tu modelo 'CajaMovimiento'
    tipo: str
    concepto: str
    monto: float
    metodo_pago: Optional[str] = None # Hacemos opcional para cubrir todos los casos
    usuario: Optional[_InfoUsuarioMovimiento] = None # Quién hizo el movimiento

    # --- Datos Anidados de la Venta (solo si el movimiento es de tipo 'VENTA') ---
    venta: Optional[_InfoVentaAnidada] = None

    class Config:
        from_attributes = True # Para Pydantic v2 (reemplaza a orm_mode = True)

class CajaAbiertaInfo(BaseModel):
    id_sesion: int
    fecha_apertura: datetime
    usuario_apertura: str
    saldo_inicial: float
    estado: str

# --- SCHEMA PARA UN ARQUEO CERRADO INDIVIDUAL ---
class ArqueoCerradoInfo(BaseModel):
    id_sesion: int
    fecha_apertura: datetime
    fecha_cierre: Optional[datetime]
    usuario_apertura: str
    usuario_cierre: str
    saldo_inicial: float
    saldo_final_declarado: Optional[float]
    saldo_final_calculado: Optional[float]
    saldo_final_efectivo: Optional[float]
    saldo_final_transferencia: Optional[float]
    saldo_final_bancario: Optional[float]
    diferencia: Optional[float]
    estado: str

# --- SCHEMA PRINCIPAL PARA LA RESPUESTA DEL ENDPOINT DE ARQUEOS ---
# Este es el schema que tu router importará y usará como `response_model`.
class InformeArqueosResponse(BaseModel):
    cajas_abiertas: List[CajaAbiertaInfo]
    arqueos_cerrados: List[ArqueoCerradoInfo]