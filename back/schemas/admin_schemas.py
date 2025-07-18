# back/schemas/admin_schemas.py
# VERSIÓN ADAPTADA PARA ROLES FIJOS

from pydantic import BaseModel

# --- Roles (Solo para respuesta) ---
class RolResponse(BaseModel):
    id: int
    nombre: str
    class Config: from_attributes = True

# --- Usuarios ---
class UsuarioBase(BaseModel):
    nombre_usuario: str
class UsuarioCreate(UsuarioBase):
    password: str
    id_rol: int
class UsuarioResponse(UsuarioBase):
    id: int
    activo: bool
    # Anidamos el RolResponse para ver la info del rol
    rol: RolResponse
    class Config: from_attributes = True
class CambiarRolUsuarioRequest(BaseModel):
    id_rol: int