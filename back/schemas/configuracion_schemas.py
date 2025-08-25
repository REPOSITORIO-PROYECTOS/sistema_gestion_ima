# back/schemas/configuracion_schemas.py

from pydantic import BaseModel, Field
from typing import Optional, Dict
from enum import Enum

class CondicionIVAEnum(str, Enum):
    RESPONSABLE_INSCRIPTO = "RESPONSABLE_INSCRIPTO"
    EXENTO = "EXENTO"
    CONSUMIDOR_FINAL = "CONSUMIDOR_FINAL"
    MONOTRIBUTO = "MONOTRIBUTO"
    NO_CATEGORIZADO = "NO_CATEGORIZADO"
    
class FormatoComprobanteEnum(str, Enum):
    ticket = "ticket"
    pdf = "pdf"
    
class ConfiguracionUpdate(BaseModel):
    """
    Schema para actualizar la configuración. Todos los campos son opcionales
    para permitir actualizaciones parciales.
    """
    nombre_negocio: Optional[str] = None
    color_principal: Optional[str] = None # Valida que sea un color hex
    afip_condicion_iva: Optional[CondicionIVAEnum] = None
    afip_punto_venta_predeterminado: Optional[int] = None
    direccion_negocio: Optional[str] = None
    telefono_negocio: Optional[str] = None
    mail_negocio: Optional[str] = None
    link_google_sheets: Optional[str] = None
    cuit: Optional[int] = None
    formato_comprobante_predeterminado: Optional[FormatoComprobanteEnum] = None
    aclaraciones_legales: Optional[Dict[str, str]] = None

class ConfiguracionResponse(BaseModel):
    """Schema completo para devolver la configuración de una empresa."""
    id_empresa: int
    nombre_negocio: Optional[str]
    color_principal: str
    ruta_logo: Optional[str]
    ruta_icono: Optional[str]
    afip_condicion_iva: Optional[CondicionIVAEnum] = None
    afip_punto_venta_predeterminado: Optional[int]
    direccion_negocio: Optional[str]
    telefono_negocio: Optional[str]
    mail_negocio: Optional[str]
    link_google_sheets: Optional[str]
    cuit: Optional[int]
    aclaraciones_legales: Optional[Dict[str, str]]

    class Config:
        from_attributes = True
        
class RecargoData(BaseModel):
    """Schema para devolver la información de un recargo."""
    porcentaje: float
    concepto: str

class RecargoUpdate(BaseModel):
    """Schema para recibir la actualización de un recargo."""
    porcentaje: float = Field(..., ge=0) # El porcentaje debe ser 0 o mayor
    concepto: Optional[str] = None # Hacemos el concepto opcional
    
class ColorUpdateRequest(BaseModel):
    color_principal: str

class ColorResponse(BaseModel):
    color_principal: str

