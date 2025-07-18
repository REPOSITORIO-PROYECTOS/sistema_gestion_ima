# back/gestion/admin/usuarios_manager.py
# VERSIÓN ADAPTADA PARA ROLES FIJOS

from sqlmodel import Session, select
from typing import List
from back.modelos import Usuario, Rol
from back.security import get_password_hash

def obtener_todos_los_roles(db: Session) -> List[Rol]:
    """Obtiene la lista de todos los roles disponibles en la base de datos."""
    return db.exec(select(Rol)).all()

def crear_usuario(db: Session, nombre_usuario: str, password: str, id_rol: int) -> Usuario:
    """Crea un nuevo usuario y le asigna un rol existente."""
    rol_db = db.get(Rol, id_rol)
    if not rol_db:
        raise ValueError("El rol seleccionado no existe.")
        
    usuario_existente = db.exec(select(Usuario).where(Usuario.nombre_usuario == nombre_usuario)).first()
    if usuario_existente:
        raise ValueError("El nombre de usuario ya está en uso.")
    
    password_hash = get_password_hash(password)
    nuevo_usuario = Usuario(
        nombre_usuario=nombre_usuario,
        password_hash=password_hash,
        id_rol=id_rol
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario

def obtener_todos_los_usuarios(db: Session) -> List[Usuario]:
    """Obtiene una lista de todos los usuarios con su rol."""
    return db.exec(select(Usuario)).all()

def cambiar_rol_de_usuario(db: Session, id_usuario: int, id_nuevo_rol: int) -> Usuario:
    """Cambia el rol de un usuario existente."""
    usuario = db.get(Usuario, id_usuario)
    if not usuario:
        raise ValueError("Usuario no encontrado.")
    
    rol_nuevo = db.get(Rol, id_nuevo_rol)
    if not rol_nuevo:
        raise ValueError("El nuevo rol seleccionado no existe.")
        
    usuario.id_rol = id_nuevo_rol
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario