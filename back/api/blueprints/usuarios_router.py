# back/api/blueprints/usuarios_router.py

from fastapi import APIRouter, Depends
from back.security import obtener_usuario_actual # Importamos nuestro guardián principal
from back.modelos import Usuario
from back.schemas.usuario_schemas import UsuarioResponse # Importamos el nuevo schema

router = APIRouter(
    prefix="/users",
    tags=["Usuarios"]
)

@router.get("/me", response_model=UsuarioResponse)
def read_users_me(current_user: Usuario = Depends(obtener_usuario_actual)):
    """
    Endpoint para obtener la información del usuario actualmente autenticado.
    
    El frontend debe llamar a este endpoint inmediatamente después de un login exitoso
    para obtener los datos del usuario, incluyendo su rol.
    """
    # La dependencia `obtener_usuario_actual` ya hizo todo el trabajo:
    # 1. Validó el token.
    # 2. Buscó al usuario en la base de datos.
    # 3. Nos devuelve el objeto `Usuario` completo.
    # Simplemente lo retornamos. FastAPI y Pydantic se encargarán de convertirlo
    # al formato JSON definido en `UsuarioResponse`.
    return current_user