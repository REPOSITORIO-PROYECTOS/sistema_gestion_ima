# back/schemas/configuracion_schemas.py

from pydantic import BaseModel, Field
from typing import Optional

class ConfiguracionUpdate(BaseModel):
    """
    Schema para actualizar la configuración. Todos los campos son opcionales
    para permitir actualizaciones parciales.
    """
    nombre_negocio: Optional[str] = None
    color_principal: Optional[str] = Field(None, example="#3F51B5") # Valida que sea un color hex
    afip_condicion_iva: Optional[str] = None
    afip_punto_venta_predeterminado: Optional[int] = None
    direccion_negocio: Optional[str] = None
    telefono_negocio: Optional[str] = None
    mail_negocio: Optional[str] = None
    link_google_sheets: Optional[str] = None
    cuit: Optional[int]

class ConfiguracionResponse(BaseModel):
    """Schema completo para devolver la configuración de una empresa."""
    id_empresa: int
    nombre_negocio: Optional[str]
    color_principal: str
    ruta_logo: Optional[str]
    ruta_icono: Optional[str]
    afip_condicion_iva: Optional[str]
    afip_punto_venta_predeterminado: Optional[int]
    direccion_negocio: Optional[str]
    telefono_negocio: Optional[str]
    mail_negocio: Optional[str]
    link_google_sheets: Optional[str]
    cuit: Optional[int]
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