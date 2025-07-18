# back/security.py
# VERSIÓN FINAL COMPLETA, CORREGIDA Y CON RASTREO

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

# --- Módulos del proyecto ---
from back import config
from back.database import get_db
from back.modelos import Usuario

# --- Configuración de Seguridad ---
SECRET_KEY = config.SECRET_KEY_SEC
ALGORITHM = "HS256"
# Usamos getattr para tener un valor por defecto si no está en config.py
ACCESS_TOKEN_EXPIRE_MINUTES = getattr(config, 'ACCESS_TOKEN_EXPIRE_MINUTES', 210)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# --- Funciones de Contraseñas y Tokens (Estándar) ---
def verificar_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña en texto plano contra su hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Genera el hash de una contraseña."""
    return pwd_context.hash(password)

def crear_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crea un nuevo token JWT."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ===================================================================
# === DEPENDENCIAS DE SEGURIDAD (NÚCLEO DEL SISTEMA) ===
# ===================================================================

def obtener_usuario_actual(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) -> Usuario:
    """
    Función central de seguridad. Valida el token y devuelve el objeto Usuario
    completo desde la base de datos con su rol actualizado en tiempo real.
    """
    print("\n--- [RASTREO DE SEGURIDAD] ---")
    print(f"1. Iniciando 'obtener_usuario_actual'.")
    
    # CORRECCIÓN: Definición completa de la excepción
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas, token expirado o permisos insuficientes.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        print(f"2. Token decodificado. Username extraído: '{username}'")
        if username is None:
            print("   -> ERROR: 'sub' (username) no encontrado en el payload del token.")
            raise credentials_exception
    except JWTError as e:
        print(f"   -> ERROR: El token JWT es inválido o ha expirado. Error: {e}")
        raise credentials_exception
    
    print(f"3. Buscando al usuario '{username}' en la base de datos (con carga de rol)...")
    
    # Consulta optimizada para cargar el usuario y su rol en una sola vez
    consulta = (
        select(Usuario)
        .where(Usuario.nombre_usuario == username)
        .options(selectinload(Usuario.rol))
    )
    usuario = db.exec(consulta).first()
    
    if usuario is None:
        print(f"   -> ERROR: Usuario '{username}' NO ENCONTRADO en la base de datos.")
        raise credentials_exception
    else:
        print(f"4. Usuario encontrado en la DB. ID: {usuario.id}, Nombre: {usuario.nombre_usuario}, Activo: {usuario.activo}")

    if not usuario.activo:
        print(f"   -> ERROR: El usuario '{username}' (ID: {usuario.id}) no está activo.")
        raise credentials_exception
    
    if hasattr(usuario, 'rol') and usuario.rol:
        print(f"5. Rol del usuario cargado correctamente: '{usuario.rol.nombre}' (ID: {usuario.rol.id})")
    else:
        print(f"   -> ¡ADVERTENCIA CRÍTICA! El usuario '{username}' (ID: {usuario.id}) NO TIENE UN ROL ASIGNADO O LA RELACIÓN FALLÓ.")
        raise credentials_exception # Un usuario sin rol no debería poder operar
        
    print("6. Autenticación exitosa. Devolviendo objeto Usuario completo.")
    print("--- [FIN DEL RASTREO] ---\n")
    return usuario

def es_rol(roles_requeridos: List[str]):
    """
    Factoría de dependencias que crea un "guardián" de roles.
    """
    def chequear_rol(current_user: Usuario = Depends(obtener_usuario_actual)) -> Usuario:
        print("\n--- [RASTREO DE ROL] ---")
        print(f"A. Verificando si el usuario '{current_user.nombre_usuario}' tiene uno de los roles: {roles_requeridos}")
        
        user_rol = current_user.rol.nombre if hasattr(current_user, 'rol') and current_user.rol else "SIN ROL"
        print(f"B. Rol actual del usuario: '{user_rol}'")
        
        if user_rol not in roles_requeridos:
            print(f"   -> ¡ACCESO DENEGADO! El rol '{user_rol}' no está en la lista de roles permitidos.")
            print("--- [FIN DEL RASTREO DE ROL] ---\n")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado. Se requiere uno de los siguientes roles: {', '.join(roles_requeridos)}.",
            )
            
        print("C. ¡ACCESO PERMITIDO! El rol es correcto.")
        print("--- [FIN DEL RASTREO DE ROL] ---\n")
        return current_user
    return es_rol

# --- Guardianes listos para usar en los routers ---
es_cajero = es_rol(["Cajero", "Admin", "Gerente", "Soporte"])
es_admin = es_rol(["Admin", "Soporte"])
es_gerente = es_rol(["Gerente", "Admin", "Soporte"])