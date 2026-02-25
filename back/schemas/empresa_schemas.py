# back/schemas/empresa_schemas.py

from pydantic import BaseModel, Field, validator
from typing import Optional

class EmpresaCreate(BaseModel):
    """Schema para recibir los datos al crear una nueva empresa."""
    nombre_legal: str
    nombre_fantasia: Optional[str] = None
    cuit: str = Field(..., min_length=11, max_length=11)
    link_google_sheets: Optional[str] = None
    admin_username: str
    admin_password: str
    afip_punto_venta_predeterminado: int
    afip_condicion_iva: str
    @validator('cuit')
    def limpiar_cuit(cls, v):
        if v:
            return ''.join(filter(str.isdigit, v))
        return v

class EmpresaResponse(BaseModel):
    """Schema para devolver los datos de una empresa."""
    id: int
    nombre_legal: str
    nombre_fantasia: Optional[str] = None
    cuit: str
    activa: bool
    link_google_sheets: Optional[str] = None
    admin_username: str
    admin_user_id: Optional[int] = None
    
    class Config:
        from_attributes = True

class EmpresaListaResponse(BaseModel):
    """
    Schema SEGURO para devolver lista de empresas.
    Solo devuelve información pública, SIN datos sensibles de usuarios o configuración.
    """
    id: int
    nombre_legal: str
    nombre_fantasia: Optional[str] = None
    cuit: str
    activa: bool
    
    class Config:
        from_attributes = True
