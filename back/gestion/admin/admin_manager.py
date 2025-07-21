# back/gestion/admin/admin_manager.py
# VERSIÓN UNIFICADA Y FINAL

from sqlmodel import Session, select
from typing import Optional, List
from sqlalchemy.orm import selectinload

# --- Módulos del Proyecto ---
from back.modelos import Usuario, Rol
from back.security import get_password_hash
from back.schemas.admin_schemas import UsuarioCreate # Usamos el schema que nos pasaste

# ===================================================================
# === LÓGICA DE GESTIÓN DE USUARIOS
# ===================================================================

def crear_usuario(db: Session, usuario_data: UsuarioCreate) -> Usuario:
    """
    Crea un nuevo usuario, hasheando su contraseña y validando los datos.
    Usa el schema UsuarioCreate para recibir los datos.
    """
    if db.exec(select(Usuario).where(Usuario.nombre_usuario == usuario_data.nombre_usuario)).first():
        raise ValueError(f"El nombre de usuario '{usuario_data.nombre_usuario}' ya está en uso.")

    rol_db = db.get(Rol, usuario_data.id_rol)
    if not rol_db:
        raise ValueError(f"El rol con ID {usuario_data.id_rol} no es válido.")

    password_hasheada = get_password_hash(usuario_data.password)
    
    nuevo_usuario = Usuario(
        nombre_usuario=usuario_data.nombre_usuario,
        password_hash=password_hasheada,
        id_rol=usuario_data.id_rol
    )
    
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario

def desactivar_usuario(db: Session, usuario_id_a_desactivar: int, admin_actual: Usuario) -> Optional[Usuario]:
    """Realiza una "eliminación lógica" de un usuario marcándolo como inactivo."""
    if admin_actual.id == usuario_id_a_desactivar:
        raise ValueError("Acción no permitida: no puedes desactivar tu propia cuenta.")

    usuario_a_desactivar = db.get(Usuario, usuario_id_a_desactivar)
    if not usuario_a_desactivar:
        return None

    usuario_a_desactivar.activo = False
    db.add(usuario_a_desactivar)
    db.commit()
    db.refresh(usuario_a_desactivar)
    return usuario_a_desactivar


def obtener_todos_los_usuarios(db: Session) -> List[Usuario]:
    """Obtiene una lista de todos los usuarios del sistema con su rol precargado."""
    return db.exec(select(Usuario).options(selectinload(Usuario.rol))).all()

def obtener_todos_los_roles(db: Session) -> List[Rol]:
    """Obtiene una lista de todos los roles disponibles."""
    return db.exec(select(Rol)).all()