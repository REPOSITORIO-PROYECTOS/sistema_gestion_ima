# back/security.py

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, select

# --- Módulos del proyecto ---
from back import config
from back.database import get_db
from back.modelos import Usuario

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
# === DEPENDENCIAS DE SEGURIDAD (CONEXIÓN A DB ACTIVADA) ===
# ===================================================================

def obtener_usuario_actual(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db) # <-- Inyectamos la sesión de la base de datos
) -> Usuario:
    """
    Función central de seguridad.
    1. Valida el token JWT para obtener el nombre de usuario.
    2. Busca a ese usuario en la base de datos SQL.
    3. Devuelve el objeto Usuario COMPLETO con su rol actualizado en tiempo real.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas, token expirado o permisos insuficientes",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # --- CONEXIÓN A LA BASE DE DATOS (LA LÓGICA REAL) ---
    # Buscamos en la DB en CADA petición para tener los datos más actuales.
    usuario = db.exec(select(Usuario).where(Usuario.nombre_usuario == username)).first()
    
    # Verificamos que el usuario exista en la BD y que esté activo
    if usuario is None or not usuario.activo:
        raise credentials_exception
        
    return usuario

def es_rol(roles_requeridos: List[str]):
    """
    Factoría de dependencias que crea un "guardián" de roles.
    Verifica que el rol del usuario actual (obtenido de la DB) esté en la
    lista de roles permitidos.
    """
    def chequear_rol(current_user: Usuario = Depends(obtener_usuario_actual)) -> Usuario:
        # Aquí la magia: comparamos con el rol REAL de la base de datos
        if not hasattr(current_user, 'rol') or current_user.rol.nombre not in roles_requeridos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado. Se requiere uno de los siguientes roles: {', '.join(roles_requeridos)}.",
            )
        return current_user
    return chequear_rol

# --- Guardianes listos para usar en los routers ---
# Son legibles y encapsulan la lógica de qué roles son válidos.

# Permite usuarios con rol 'Cajero' o 'Admin'
es_cajero = es_rol(["Cajero", "Admin", "Gerente", "Soporte"])

# Permite únicamente usuarios con rol 'Admin'
es_admin = es_rol(["Admin", "Soporte"])

# Permite usuarios con rol 'Gerente' o 'Admin'
es_gerente = es_rol(["Gerente", "Admin", "Soporte"])