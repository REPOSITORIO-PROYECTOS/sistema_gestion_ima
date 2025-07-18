# back/schemas/usuario_schemas.py

from pydantic import BaseModel

class RolResponse(BaseModel):
    id: int
    nombre: str

class UsuarioResponse(BaseModel):
    """Define los datos del usuario que son seguros para enviar al frontend."""
    id: int
    nombre_usuario: str
    activo: bool
    rol: RolResponse # Anidamos el schema del rol para obtener sus datos

    class Config:
        from_attributes = True