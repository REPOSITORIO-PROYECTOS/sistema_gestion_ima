# back/api/blueprints/admin_router.py
# VERSIÓN FINAL, SEGURA Y ESTANDARIZADA

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List

# --- Módulos del Proyecto ---
from back.database import get_db
from back.security import es_admin,es_cajero, obtener_usuario_actual
from back.modelos import Usuario
import back.gestion.admin.admin_manager as admin_manager
from back.schemas.admin_schemas import *
from back.schemas.caja_schemas import RespuestaGenerica

router = APIRouter(
    prefix="/admin",
    tags=["Panel de Administración"],
    dependencies=[Depends(es_admin)] # <-- ¡SEGURIDAD ACTIVADA!
)

# ===================================================================
# === GESTIÓN DE USUARIOS
# ===================================================================

@router.post("/usuarios/crear", response_model=UsuarioResponse, status_code=201, summary="Crear un nuevo usuario")
def api_crear_usuario(req: UsuarioCreate, db: Session = Depends(get_db)):
    """Crea un nuevo usuario y le asigna un rol."""
    try:
        return admin_manager.crear_usuario(db, req)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.get("/usuarios/listar", response_model=List[UsuarioResponse], summary="Obtener lista de todos los usuarios")
def api_obtener_usuarios(db: Session = Depends(get_db),current_user: Usuario = Depends(obtener_usuario_actual)):
    """Obtiene una lista de todos los usuarios con su información de rol y estado."""
    id_empresa = current_user.id_empresa
    return admin_manager.obtener_todos_los_usuarios(id_empresa,db)

@router.get("/usuarios/{usuario_id}", response_model=UsuarioResponse, summary="Obtener un usuario por ID")
def api_obtener_usuario_por_id(usuario_id: int, db: Session = Depends(get_db)):
    """Obtiene la información detallada de un solo usuario, incluyendo su estado."""
    usuario = admin_manager.obtener_usuario_por_id(db, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail=f"Usuario con ID {usuario_id} no encontrado.")
    return usuario

@router.patch("/usuarios/{usuario_id}/rol", response_model=UsuarioResponse, summary="Cambiar el rol de un usuario")
def api_cambiar_rol_usuario(usuario_id: int, req: CambiarRolUsuarioRequest, db: Session = Depends(get_db)):
    """Cambia el rol de un usuario existente."""
    try:
        return admin_manager.cambiar_rol_de_usuario(db, usuario_id, req.id_rol)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.patch("/usuarios/{usuario_id}/activar", response_model=RespuestaGenerica, summary="Activar un usuario")
def api_activar_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """Reactiva a un usuario que fue desactivado previamente."""
    try:
        usuario_activado = admin_manager.activar_usuario(db, usuario_id)
        return RespuestaGenerica(status="success", message=f"Usuario '{usuario_activado.nombre_usuario}' ha sido activado.")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# Usamos DELETE, la ruta estándar para eliminar/desactivar un recurso
@router.delete("/usuarios/{usuario_id}/desactivar", response_model=RespuestaGenerica, summary="Desactivar un usuario")
def api_desactivar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    admin_actual: Usuario = Depends(obtener_usuario_actual)
):
    """Desactiva a un usuario (eliminación lógica)."""
    try:
        usuario_desactivado = admin_manager.desactivar_usuario(db, usuario_id, admin_actual)
        return RespuestaGenerica(status="success", message=f"Usuario '{usuario_desactivado.nombre_usuario}' ha sido desactivado.")
    except ValueError as e:
        # Usamos 400 para un Bad Request (intentar desactivarse a sí mismo)
        # y 404 para un usuario no encontrado.
        if "no puedes desactivar tu propia cuenta" in str(e):
             raise HTTPException(status_code=400, detail=str(e))
        else:
             raise HTTPException(status_code=404, detail=str(e))

# ===================================================================
# === GESTIÓN DE ROLES
# ===================================================================

@router.get("/roles", response_model=List[RolResponse], summary="Obtener lista de roles")
def api_obtener_roles(db: Session = Depends(get_db)):
    """Devuelve la lista de todos los roles disponibles en el sistema."""
    return admin_manager.obtener_todos_los_roles(db)

@router.patch("/usuarios/{usuario_id}/password", response_model=UsuarioResponse, summary="Actualizar contraseña de un usuario")
def api_actualizar_password_usuario(usuario_id: int, req: CambiarPasswordUsuarioRequest, db: Session = Depends(get_db)):
    """Actualiza la contraseña de un usuario (requiere privilegios de Admin)."""
    try:
        usuario = admin_manager.actualizar_password_usuario(db, usuario_id, req.nueva_password)
        return usuario
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
