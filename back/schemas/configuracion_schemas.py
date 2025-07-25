# /back/schemas/configuracion_schemas.py

from pydantic import BaseModel, Field
from typing import Optional

class ConfiguracionUpdate(BaseModel):
    # Todos los campos son opcionales para permitir actualizaciones parciales (PATCH)
    link_google_sheets: Optional[str] = None
    nombre_negocio: Optional[str] = None
    color_principal: Optional[str] = Field(default=None, example="#3F51B5")
    
    afip_condicion_iva: Optional[str] = None
    afip_punto_venta_predeterminado: Optional[int] = None
    
    direccion_negocio: Optional[str] = None
    telefono_negocio: Optional[str] = None
    mail_negocio: Optional[str] = None

class ConfiguracionRead(BaseModel):
    # Este schema representa la configuración completa que se enviará al frontend
    id_empresa: int
    link_google_sheets: Optional[str]
    nombre_negocio: Optional[str]
    color_principal: str
    ruta_logo: Optional[str]
    ruta_icono: Optional[str]
    afip_condicion_iva: Optional[str]
    afip_punto_venta_predeterminado: Optional[int]
    direccion_negocio: Optional[str]
    telefono_negocio: Optional[str]
    mail_negocio: Optional[str]

    class Config:
        orm_mode = True