# back/gestion/admin/auth_manager.py

from sqlmodel import Session, select
from back.modelos import Usuario
from back.security import verificar_password

def autenticar_usuario(db: Session, username: str, password: str) -> Usuario | None:
    """
    Autentica a un usuario contra la base de datos usando SQLModel.
    Devuelve el objeto Usuario completo si es válido, o None si no lo es.
    """
    # 1. Busca al usuario en la base de datos
    usuario = db.exec(select(Usuario).where(Usuario.nombre_usuario == username)).first()
    
    # 2. Si no existe o la contraseña no coincide, devuelve None
    if not usuario or not verificar_password(password, usuario.password_hash):
        return None
        
    # 3. Si todo es correcto, devuelve el objeto Usuario
    return usuario