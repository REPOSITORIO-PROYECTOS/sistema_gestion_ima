# back/security.py
# VERSIÓN REFORMULADA PARA DESBLOQUEAR EL DESARROLLO

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session

from back import config
from back.modelos import Usuario, Rol # Importamos los modelos de la DB
# Importamos get_db para la futura conexión a la base de datos
from back.database import get_db

# --- Configuración (sin cambios) ---
SECRET_KEY = config.SECRET_KEY_SEC
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 210
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# --- Funciones de Contraseñas y Tokens (sin cambios) ---
def verificar_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def crear_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ===================================================================
# === DEPENDENCIAS DE SEGURIDAD (LA LÓGICA "PUENTE") ===
# ===================================================================

# CAMBIO 1: Renombramos la función y ajustamos lo que devuelve
def obtener_usuario_actual(token: str = Depends(oauth2_scheme)) -> Usuario:
    """
    Función de seguridad temporal. Valida el token y devuelve un objeto Usuario
    SIMULADO con los datos del token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas, token expirado o permisos insuficientes",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role_name: str = payload.get("role") # Obtenemos el rol del token
        if username is None or role_name is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # --- LA PARTE SIMULADA ---
    # En lugar de consultar la DB, creamos un objeto Usuario "falso" en memoria.
    # Esto es suficiente para que los routers obtengan `current_user.id` y `current_user.rol.nombre`.
    # Asignamos IDs ficticios.
    rol_ficticio = Rol(id=1, nombre=role_name)
    usuario_ficticio = Usuario(
        id=1, # !!! ID FIJO TEMPORAL !!!
        nombre_usuario=username,
        rol=rol_ficticio,
        id_rol=rol_ficticio.id,
        activo=True,
        password_hash="" # No es necesario aquí
    )
    
    return usuario_ficticio

def es_rol(roles_requeridos: List[str]):
    """

    Factoría de dependencias que crea un "guardián" de roles.
    Funciona con el usuario (simulado o real) que devuelve `obtener_usuario_actual`.
    """
    def chequear_rol(current_user: Usuario = Depends(obtener_usuario_actual)) -> Usuario:
        # Ahora comparamos con el nombre del rol del objeto Usuario
        if current_user.rol.nombre not in roles_requeridos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado. Se requiere uno de los siguientes roles: {', '.join(roles_requeridos)}.",
            )
        return current_user
    return chequear_rol

# --- Guardianes listos para usar (sin cambios) ---
es_cajero = es_rol(["Cajero", "Admin"])
es_admin = es_rol(["Admin"])