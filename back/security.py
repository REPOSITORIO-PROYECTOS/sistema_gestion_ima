# back/security.py
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from back import config

# --- Configuración de Seguridad ---
# Estos valores deberían ir en tu .env y cargarse desde config.py
SECRET_KEY = config.SECRET_KEY_SEC # ¡CAMBIAR ESTO Y PONERLO EN .ENV!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 210 # Un token de acceso durará 210 minutos

# Contexto para hashear contraseñas. Usamos bcrypt, que es muy seguro.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Esquema de seguridad para que FastAPI sepa cómo esperar el token
# "tokenUrl" es el endpoint donde el usuario enviará su usuario/contraseña para obtener un token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# --- Funciones de Contraseñas ---
def verificar_password(plain_password, hashed_password):
    """Verifica una contraseña en texto plano contra su hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Genera el hash de una contraseña."""
    return pwd_context.hash(password)

# --- Funciones de Tokens JWT ---
def crear_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Crea un nuevo token JWT."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Dependencias "Perro Guardián" ---
# Esta es la función principal que protegerá nuestros endpoints
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Decodifica el token, valida sus credenciales y devuelve el usuario.
    Esta es la dependencia básica, protege contra usuarios no autenticados.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        # Aquí iría una llamada a la base de datos para obtener el usuario completo
        # from .gestion.auth import get_user_by_username
        # user = get_user_by_username(username)
        # if user is None or not user.esta_activo:
        #     raise credentials_exception
        
        # Por ahora, devolvemos un diccionario simple con los datos del token
        user_data = {"username": username, "role": payload.get("role")}
        return user_data

    except JWTError:
        raise credentials_exception

# --- Dependencias de Roles ---
# Estas dependencias dependen de la anterior, creando una cadena de seguridad.

def es_cajero(current_user: dict = Depends(get_current_user)):
    """
    Verifica que el usuario actual tenga el rol 'cajero' o 'admin'.
    Un admin puede hacer todo lo que hace un cajero.
    """
    if current_user.get("role") not in ["cajero", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operación no permitida. Se requiere rol de Cajero o Administrador."
        )
    return current_user

def es_admin(current_user: dict = Depends(get_current_user)):
    """
    Verifica que el usuario actual tenga el rol 'admin'.
    Máxima seguridad.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operación no permitida. Se requiere rol de Administrador."
        )
    return current_user