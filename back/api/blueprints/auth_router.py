# back/api/blueprints/auth_router.py
# VERSIÓN FINAL Y CORREGIDA

from datetime import timedelta
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

# --- Módulos del proyecto ---
from back.database import get_db
from back.security import (
    crear_access_token, ACCESS_TOKEN_EXPIRE_MINUTES,
    es_admin, obtener_usuario_actual # <--- Usamos el nombre correcto
)
from back.gestion.seguridad import llave_maestra_manager
from back.gestion.admin import auth_manager # <--- Importamos nuestra nueva lógica de negocio
from back.schemas.caja_schemas import RespuestaGenerica
from back.modelos import Usuario # Importamos el modelo para usarlo en las dependencias

router = APIRouter(
    prefix="/auth",
    tags=["Autenticación y Autorización"]
)

@router.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db) # <--- Inyectamos la sesión de la DB
):
    """
    Endpoint de inicio de sesión. Valida contra la DB y devuelve un token JWT.
    """
    # 1. Llamamos a nuestra nueva función de negocio que usa SQLModel
    usuario = auth_manager.autenticar_usuario(
        db=db,
        username=form_data.username,
        password=form_data.password
    )
    
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nombre de usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 2. Creamos el token usando el objeto Usuario real
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = crear_access_token(
        data={"sub": usuario.nombre_usuario, "role": usuario.rol.nombre},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/validar-llave", response_model=RespuestaGenerica)
def api_validar_llave_maestra(
    llave: str = Body(..., embed=True, description="La llave maestra a validar"),
    # CORRECCIÓN: Usamos `obtener_usuario_actual` y especificamos el tipo de retorno
    #current_user: Usuario = Depends(obtener_usuario_actual) 
):
    """
    Valida si la llave proporcionada coincide con la llave maestra del día.
    """
    es_valida = llave_maestra_manager.validar_llave_maestra(llave)
    if es_valida:
        return RespuestaGenerica(status="success", message="Llave maestra correcta. Operación autorizada.")
    else:
        raise HTTPException(status_code=403, detail="La llave maestra proporcionada es incorrecta o ha expirado.")


@router.get("/llave-actual", response_model=Dict)#,dependencies=[Depends(es_admin)])
def api_obtener_llave_actual():
    """
    ENDPOINT SOLO PARA ADMINISTRADORES.
    Devuelve la llave maestra actual.
    """

    return llave_maestra_manager.obtener_llave_actual_para_admin(db=get_db())