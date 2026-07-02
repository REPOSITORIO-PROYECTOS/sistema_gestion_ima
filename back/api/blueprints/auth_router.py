# back/api/blueprints/auth_router.py

from datetime import timedelta
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, Request, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

# --- Módulos del proyecto ---
from back.database import get_db
from back.security import crear_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
# Importamos los managers de negocio
from back.gestion.admin import auth_manager
from back.gestion.seguridad import llave_maestra_manager
from back.gestion.seguridad.login_rate_limiter import (
    check_login_allowed,
    register_login_failure,
    register_login_success,
)
# Importamos schemas y modelos necesarios
from back.schemas.caja_schemas import RespuestaGenerica

router = APIRouter(
    prefix="/auth",
    tags=["Autenticación y Autorización"]
)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


@router.post("/token",)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Endpoint de inicio de sesión. Valida contra la DB y devuelve un token JWT.
    """
    client_ip = _client_ip(request)
    rate = check_login_allowed(client_ip, form_data.username)
    if not rate.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos de login. Espere antes de volver a intentar.",
            headers={"Retry-After": str(rate.retry_after_seconds)},
        )

    usuario = auth_manager.autenticar_usuario(
        db=db,
        username=form_data.username,
        password=form_data.password,
    )

    if not usuario:
        register_login_failure(client_ip, form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nombre de usuario o contraseña incorrectos, o el usuario no tiene permisos para acceder.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    register_login_success(client_ip, form_data.username)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = crear_access_token(
        data={"sub": usuario.nombre_usuario},
        expires_delta=access_token_expires,
    )

    return {"access_token": access_token, "token_type": "bearer"}

# --- LOS OTROS ENDPOINTS PERMANECEN IGUAL ---

@router.post("/validar-llave", response_model=RespuestaGenerica)
def api_validar_llave_maestra(
    db: Session = Depends(get_db),
    llave: str = Body(..., embed=True, description="La llave maestra a validar")
):
    es_valida = llave_maestra_manager.validar_llave_maestra(llave, db)
    if es_valida:
        return RespuestaGenerica(status="success", message="Llave maestra correcta. Operación autorizada.")
    else:
        raise HTTPException(status_code=403, detail="La llave maestra proporcionada es incorrecta o ha expirado.")


@router.get("/llave-actual", response_model=Dict)
def api_obtener_llave_actual(db: Session = Depends(get_db)):
    return llave_maestra_manager.obtener_llave_actual_para_admin(db)