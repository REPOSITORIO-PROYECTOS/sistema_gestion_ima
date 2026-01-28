# back/schemas/usuario_schemas.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class RolResponse(BaseModel):
    id: int
    nombre: str

class UsuarioResponse(BaseModel):
    """Define los datos del usuario que son seguros para enviar al frontend."""
    id: int
    nombre_usuario: str
    activo: bool
    rol: RolResponse # Anidamos el schema del rol para obtener sus datos
    id_empresa: int
    configuracion: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True
        
class CambiarPasswordRequest(BaseModel):
    password_actual: str
    password_nueva: str = Field(min_length=8)

class CambiarNombreUsuarioRequest(BaseModel):
    nuevo_nombre_usuario: str = Field(min_length=3)

class UsuarioConfiguracionUpdate(BaseModel):
    configuracion: Dict[str, Any]
