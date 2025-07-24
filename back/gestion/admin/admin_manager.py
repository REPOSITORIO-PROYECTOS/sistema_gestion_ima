# back/gestion/admin/admin_manager.py
# VERSIÓN FINAL, COMPLETA Y SEGURA

from sqlmodel import Session, select
from typing import Optional, List
from sqlalchemy.orm import selectinload

# --- Módulos del Proyecto ---
from back.modelos import Usuario, Rol
from back.security import get_password_hash
from back.schemas.admin_schemas import UsuarioCreate

# ===================================================================
# === LÓGICA DE GESTIÓN DE USUARIOS
# ===================================================================

def crear_usuario(db: Session, usuario_data: UsuarioCreate) -> Usuario:
    """
    Crea un nuevo usuario, hasheando su contraseña y validando el rol por ID.
    """
    # 1. Verificar si el nombre de usuario ya existe
    if db.exec(select(Usuario).where(Usuario.nombre_usuario == usuario_data.nombre_usuario)).first():
        raise ValueError(f"El nombre de usuario '{usuario_data.nombre_usuario}' ya está en uso.")

    # 2. Verificar si el rol con el ID proporcionado existe
    rol_db = db.get(Rol, usuario_data.id_rol)
    if not rol_db:
        raise ValueError(f"El rol con ID {usuario_data.id_rol} no es válido o no existe.")

    # 3. Hashear la contraseña
    password_hasheada = get_password_hash(usuario_data.password)
    
    # 4. Crear la nueva instancia de Usuario
    nuevo_usuario = Usuario(
        nombre_usuario=usuario_data.nombre_usuario,
        password_hash=password_hasheada,
        id_rol=usuario_data.id_rol # Usamos directamente el ID recibido
    )
    
    # 5. Guardar en la base de datos
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    
    return nuevo_usuario

def obtener_usuario_por_id(db: Session, usuario_id: int) -> Optional[Usuario]:
    """Obtiene un único usuario por su ID, precargando su rol."""
    return db.get(Usuario, usuario_id, options=[selectinload(Usuario.rol)])

def cambiar_rol_de_usuario(db: Session, id_usuario: int, id_rol_nuevo: int) -> Usuario:
    """Encuentra un usuario por su ID y le asigna un nuevo rol."""
    usuario_a_actualizar = db.get(Usuario, id_usuario)
    if not usuario_a_actualizar:
        raise ValueError(f"Usuario con ID {id_usuario} no encontrado.")

    rol_nuevo = db.get(Rol, id_rol_nuevo)
    if not rol_nuevo:
        raise ValueError(f"Rol con ID {id_rol_nuevo} no encontrado.")

    usuario_a_actualizar.id_rol = id_rol_nuevo
    db.add(usuario_a_actualizar)
    db.commit()
    db.refresh(usuario_a_actualizar)
    return usuario_a_actualizar

def desactivar_usuario(db: Session, usuario_id_a_desactivar: int, admin_actual: Usuario) -> Usuario:
    """Realiza una "eliminación lógica" segura de un usuario."""
    if admin_actual.id == usuario_id_a_desactivar:
        raise ValueError("Acción no permitida: no puedes desactivar tu propia cuenta.")

    usuario_a_desactivar = db.get(Usuario, usuario_id_a_desactivar)
    if not usuario_a_desactivar:
        raise ValueError(f"Usuario con ID {usuario_id_a_desactivar} no encontrado.")

    usuario_a_desactivar.activo = False
    db.add(usuario_a_desactivar)
    db.commit()
    db.refresh(usuario_a_desactivar)
    return usuario_a_desactivar

def activar_usuario(db: Session, usuario_id_a_activar: int) -> Usuario:
    """Reactiva a un usuario que fue desactivado previamente."""
    usuario_a_activar = db.get(Usuario, usuario_id_a_activar)
    if not usuario_a_activar:
        raise ValueError(f"Usuario con ID {usuario_id_a_activar} no encontrado.")

    usuario_a_activar.activo = True
    db.add(usuario_a_activar)
    db.commit()
    db.refresh(usuario_a_activar)
    return usuario_a_activar

def obtener_todos_los_usuarios(db: Session) -> List[Usuario]:
    """Obtiene una lista de todos los usuarios del sistema con su rol precargado."""
    return db.exec(select(Usuario).options(selectinload(Usuario.rol))).all()

def obtener_todos_los_roles(db: Session) -> List[Rol]:
    """Obtiene una lista de todos los roles disponibles."""
    return db.exec(select(Rol)).all()