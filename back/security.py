# back/security.py
# VERSIÓN FINAL CON CORRECCIÓN DE LÓGICA EN `obtener_usuario_actual`

import logging
import os
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from back.schemas.caja_schemas import AbrirCajaRequest # Necesitamos importar el schema
from back.modelos import LlaveMaestra # Asumimos que este modelo existe

# --- Módulos del proyecto ---
from back import config
from back.database import get_db # Asegúrate que la ruta de importación sea la correcta
from back.modelos import Usuario, Rol

logger = logging.getLogger(__name__)
_DEBUG_AUTH = os.getenv("APP_ENV", "production").strip().lower() in ("dev", "development", "local")


def _auth_debug(msg: str, *args: object) -> None:
    if _DEBUG_AUTH:
        logger.debug(msg, *args)

# --- Configuración de Seguridad ---
SECRET_KEY = config.SECRET_KEY_SEC
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = config.ACCESS_TOKEN_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# --- Funciones de Contraseñas y Tokens (Estándar) ---
def verificar_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def crear_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Credenciales inválidas, token expirado o permisos insuficientes.",
    headers={"WWW-Authenticate": "Bearer"},
)


def decodificar_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise CREDENTIALS_EXCEPTION from exc


# ===================================================================
# === DEPENDENCIAS DE SEGURIDAD (NÚCLEO DEL SISTEMA) ===
# ===================================================================


def obtener_id_empresa_desde_token(token: str = Depends(oauth2_scheme)) -> int:
    """
    Auth liviana para endpoints de alto volumen (p. ej. poll del escáner).
    Solo decodifica JWT — sin sesión MySQL. Requiere claim id_empresa (login nuevo).
    """
    payload = decodificar_token(token)
    raw_id = payload.get("id_empresa")
    if raw_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sin id_empresa. Cierre sesión e ingrese nuevamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return int(raw_id)
    except (TypeError, ValueError) as exc:
        raise CREDENTIALS_EXCEPTION from exc


def obtener_usuario_actual(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) -> Usuario:
    """
    Función central de seguridad. Valida el token y devuelve el objeto Usuario
    completo desde la base de datos con su rol actualizado en tiempo real.
    """
    _auth_debug("obtener_usuario_actual: iniciando validación")

    payload = decodificar_token(token)
    username: str | None = payload.get("sub")
    _auth_debug("Token decodificado para username=%r", username)
    if username is None:
        raise CREDENTIALS_EXCEPTION

    consulta = select(Usuario).where(Usuario.nombre_usuario == username).options(selectinload(Usuario.rol))
    usuario = db.exec(consulta).first()

    if usuario is None:
        _auth_debug("Usuario %r no encontrado en DB", username)
        raise CREDENTIALS_EXCEPTION

    if not usuario.activo:
        _auth_debug("Usuario %r (id=%s) inactivo", username, usuario.id)
        raise CREDENTIALS_EXCEPTION

    if not usuario.rol:
        logger.warning("Usuario %r (id=%s) sin rol asignado", username, usuario.id)
        raise CREDENTIALS_EXCEPTION

    _auth_debug(
        "Auth OK: user=%r id=%s rol=%r",
        usuario.nombre_usuario,
        usuario.id,
        usuario.rol.nombre,
    )
    return usuario

def verificar_llave_maestra_apertura(
    req: AbrirCajaRequest, # Recibe el cuerpo de la petición
    db: Session = Depends(get_db)
):
    """
    Dependencia de seguridad que valida la llave maestra para operaciones críticas.
    """
    _auth_debug("Verificando llave maestra de apertura de caja")

    llave_valida = db.exec(select(LlaveMaestra)).first()

    if not llave_valida:
        logger.error("No hay llave maestra configurada en la base de datos")
        raise HTTPException(status_code=500, detail="Error de configuración del sistema: Llave Maestra no encontrada.")

    if req.llave_maestra != llave_valida.llave:
        raise HTTPException(status_code=403, detail="La llave maestra proporcionada es incorrecta.")

def es_rol(roles_requeridos: List[str]):
    """
    Factoría de dependencias que crea un "guardián" de roles.
    """
    def chequear_rol(current_user: Usuario = Depends(obtener_usuario_actual)) -> Usuario:
        user_rol = current_user.rol.nombre
        _auth_debug(
            "Chequeo rol user=%r rol=%r requeridos=%s",
            current_user.nombre_usuario,
            user_rol,
            roles_requeridos,
        )

        if user_rol not in roles_requeridos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado. Se requiere uno de los siguientes roles: {', '.join(roles_requeridos)}.",
            )

        return current_user
    
    return chequear_rol

# --- Guardianes listos para usar en los routers ---
es_cajero = es_rol(["Cajero", "Vendedora", "Admin", "Gerente", "Encargada", "Soporte", "Mozo"])
es_admin = es_rol(["Admin", "Soporte"])
es_admin_o_gerente = es_rol(["Admin", "Gerente", "Soporte"])
es_gerente = es_rol(["Gerente", "Encargada", "Admin", "Soporte"])
es_supervisor_caja = es_rol(["Gerente", "Admin", "Encargada", "Soporte"])