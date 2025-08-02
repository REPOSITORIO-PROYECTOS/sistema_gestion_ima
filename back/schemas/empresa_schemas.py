# back/schemas/empresa_schemas.py

from pydantic import BaseModel, Field, validator
from typing import Optional

class EmpresaCreate(BaseModel):
    """Schema para recibir los datos al crear una nueva empresa."""
    nombre_legal: str
    nombre_fantasia: Optional[str] = None
    cuit: str = Field(..., min_length=11, max_length=11)
    id_google_sheets: Optional[str] = None

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
    id_google_sheets: Optional[str] = None

    class Config:
        from_attributes = True