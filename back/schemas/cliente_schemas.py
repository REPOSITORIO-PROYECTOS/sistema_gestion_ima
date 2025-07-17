# back/schemas/cliente_schemas.py
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional

CONDICIONES_IVA_VALIDAS = ["IVA Responsable Inscripto", "IVA Sujeto Exento", "Consumidor Final", "Responsable Monotributo", "IVA no Alcanzado"]

class ClienteBase(BaseModel):
    id: int = Field(primary_key=True)
    codigo_interno: Optional[str] = Field(index=True)
    es_cliente: bool = Field(default=False)
    es_proveedor: bool = Field(default=False)
    nombre_razon_social: str = Field(index=True)
    nombre_fantasia: Optional[str]
    cuit: Optional[str]
    identificacion_fiscal: Optional[str] = Field(index=True)
    condicion_iva: str
    direccion: Optional[str]
    localidad: Optional[str]
    provincia: Optional[str]
    pais: Optional[str]
    telefono: Optional[str]
    email: Optional[str]
    limite_credito: float = Field(default=0.0)
    activo: bool = Field(default=True)
    fecha_alta: datetime = Field(default_factory=datetime.utcnow)
    notas: Optional[str]
    
    @validator('condicion_iva')
    def validar_condicion_iva(cls, v):
        if v not in CONDICIONES_IVA_VALIDAS:
            raise ValueError(f"Condición de IVA no válida. Opciones: {', '.join(CONDICIONES_IVA_VALIDAS)}")
        return v

class ClienteCreate(ClienteBase):
    @validator('identificacion_fiscal', always=True)
    def validar_identificacion_fiscal(cls, v, values):
        if values.get('condicion_iva') != 'Consumidor Final' and not v:
            raise ValueError("El CUIT/CUIL es obligatorio para clientes que no son 'Consumidor Final'.")
        return v

class ClienteUpdate(BaseModel):
    nombre_razon_social: Optional[str] = None
    condicion_iva: Optional[str] = None
    identificacion_fiscal: Optional[str] = None
    nombre_fantasia: Optional[str] = None
    direccion: Optional[str] = None
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    activo: Optional[bool] = None

class ClienteResponse(ClienteBase):
    id: int
    activo: bool
    class Config:
        from_attributes = True