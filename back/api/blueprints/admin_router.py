# back/api/blueprints/admin_router.py
# VERSIÓN REFACTORIZADA Y FINAL

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List

# --- Módulos del Proyecto ---
from back.database import get_db
from back.security import es_admin, obtener_usuario_actual
from back.modelos import Usuario
# ¡LA IMPORTACIÓN CLAVE! Ahora solo importamos el manager unificado.
import back.gestion.admin.admin_manager as admin_manager
from back.schemas.admin_schemas import * # Importamos todos los schemas de admin
from back.schemas.caja_schemas import RespuestaGenerica

router = APIRouter(
    prefix="/admin",
    tags=["Panel de Administración"],
    #dependencies=[Depends(es_admin)] # ¡Protegemos todo el router!
)

# ===================================================================
# === GESTIÓN DE USUARIOS Y ROLES
# ===================================================================

@router.post("/usuarios/crear", response_model=UsuarioResponse, status_code=201, summary="Crear un nuevo usuario")
def api_crear_usuario(req: UsuarioCreate, db: Session = Depends(get_db)):
    """Crea un nuevo usuario y le asigna un rol."""
    try:
        # Llamamos a la función correcta en nuestro manager unificado
        return admin_manager.crear_usuario(db, req)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) # 409 Conflict

@router.get("/usuarios/listar", response_model=List[UsuarioResponse], summary="Obtener lista de usuarios")
def api_obtener_usuarios(db: Session = Depends(get_db)):
    """Obtiene una lista de todos los usuarios con su información de rol."""
    return admin_manager.obtener_todos_los_usuarios(db)

@router.patch("/usuarios/{id_usuario}/rol", response_model=UsuarioResponse, summary="Cambiar el rol de un usuario")
def api_cambiar_rol_usuario(id_usuario: int, req: CambiarRolUsuarioRequest, db: Session = Depends(get_db)):
    """Cambia el rol de un usuario existente."""
    try:
        usuario_actualizado = admin_manager.cambiar_rol_de_usuario(db, id_usuario, req.id_rol)
        if not usuario_actualizado:
             raise ValueError("Usuario o rol no encontrado.")
        return usuario_actualizado
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) # 404 Not Found

@router.delete("/usuarios/{usuario_id}/desactivar", response_model=RespuestaGenerica, summary="Desactivar un usuario")
def api_desactivar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    admin_actual: Usuario = Depends(obtener_usuario_actual)
):
    """Desactiva a un usuario en el sistema (eliminación lógica)."""
    try:
        usuario_desactivado = admin_manager.desactivar_usuario(db, usuario_id, admin_actual)
        if not usuario_desactivado:
            raise HTTPException(status_code=404, detail=f"Usuario con ID {usuario_id} no encontrado.")
        return RespuestaGenerica(status="success", message=f"Usuario '{usuario_desactivado.nombre_usuario}' ha sido desactivado.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/roles", response_model=List[RolResponse], summary="Obtener lista de roles")
def api_obtener_roles(db: Session = Depends(get_db)):
    """Devuelve la lista de todos los roles disponibles en el sistema."""
    return admin_manager.obtener_todos_los_roles(db)