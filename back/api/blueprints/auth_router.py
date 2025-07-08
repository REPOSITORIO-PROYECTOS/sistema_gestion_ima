# back/api/auth_router.py
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from back.security import crear_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
# Necesitaremos una función para autenticar al usuario contra la DB
from back.utils.auth import autenticar_usuario
router = APIRouter(
    prefix="/auth",
    tags=["Autenticación"]
)

@router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Endpoint de inicio de sesión.
    Recibe 'username' y 'password' en un formulario, valida al usuario
    y devuelve un token JWT si es correcto.
    """
    # Esta función de negocio validará el usuario y contraseña contra la DB
    user = autenticar_usuario(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nombre de usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Creamos el token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = crear_access_token(
        data={"sub": user['nombre_usuario'], "role": user['nombre_rol']},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}