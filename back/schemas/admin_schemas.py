# back/schemas/admin_schemas.py
# VERSIÓN FINAL Y COMPLETA

from pydantic import BaseModel, Field
from typing import Optional

# --- Schemas de Roles ---
class RolResponse(BaseModel):
    id: int
    nombre: str

    class Config:
        from_attributes = True

# --- Schemas de Usuarios ---

class UsuarioResponse(BaseModel):
    id: int
    nombre_usuario: str
    activo: bool  # <-- Incluimos el estado para que el frontend lo pueda mostrar
    rol: RolResponse

    class Config:
        from_attributes = True

class UsuarioCreate(BaseModel):
    nombre_usuario: str
    password: str = Field(min_length=8)
    id_rol: int

class CambiarRolUsuarioRequest(BaseModel):
    id_rol: int