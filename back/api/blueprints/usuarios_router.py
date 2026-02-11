# back/api/blueprints/usuarios_router.py

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel import Session
from typing import Dict, Any

# --- Módulos del Proyecto ---
from back.database import get_db
from back.security import obtener_usuario_actual
from back.modelos import Usuario
# Importamos los nuevos schemas y la lógica del manager
from back.schemas.usuario_schemas import UsuarioResponse, CambiarPasswordRequest, CambiarNombreUsuarioRequest, UsuarioConfiguracionUpdate
import back.gestion.admin.admin_manager as admin_manager

router = APIRouter(
    prefix="/users",
    tags=["Usuarios"]
)

@router.get("/me", response_model=UsuarioResponse)
def read_users_me(current_user: Usuario = Depends(obtener_usuario_actual)):
    """
    Endpoint para obtener la información del usuario actualmente autenticado.
    
    El frontend debe llamar a este endpoint inmediatamente después de un login exitoso
    para obtener los datos del usuario, incluyendo su rol.
    """
    print (f"Usuario actual: {current_user.nombre_usuario} (ID: {current_user.id})")
    return current_user


@router.patch("/me/password", response_model=UsuarioResponse, summary="Cambiar la contraseña del usuario actual")
def api_cambiar_password_propia(
    req: CambiarPasswordRequest,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    """
    Permite al usuario autenticado cambiar su propia contraseña,
    verificando primero la contraseña actual.
    """
    try:
        usuario_actualizado = admin_manager.modificar_password_propia(
            db=db,
            usuario_actual=current_user,
            password_actual=req.password_actual,
            password_nueva=req.password_nueva
        )
        return usuario_actualizado
    except ValueError as e:
        # Usamos 400 para un Bad Request (contraseña incorrecta)
        raise HTTPException(status_code=400, detail=str(e))

# --- NUEVO ENDPOINT: CAMBIAR NOMBRE DE USUARIO ---
@router.patch("/me/username", response_model=UsuarioResponse, summary="Cambiar el nombre de usuario actual")
def api_cambiar_nombre_usuario_propio(
    req: CambiarNombreUsuarioRequest,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    """
    Permite al usuario autenticado cambiar su propio nombre de usuario,
    verificando que el nuevo nombre no esté en uso.
    """
    try:
        usuario_actualizado = admin_manager.modificar_nombre_usuario(
            db=db,
            id_usuario=current_user.id,
            nuevo_nombre=req.nuevo_nombre_usuario
        )
        return usuario_actualizado
    except ValueError as e:
        # Usamos 409 para un Conflicto (nombre de usuario ya existe)
        raise HTTPException(status_code=409, detail=str(e))

@router.patch("/me/config", response_model=UsuarioResponse, summary="Actualizar configuración del usuario (JSON)")
def api_actualizar_configuracion_usuario(
    req: UsuarioConfiguracionUpdate,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    """
    Guarda o actualiza la configuración JSON del usuario (ej. enlaces personalizados).
    """
    try:
        # Actualizamos el campo JSON directamente
        current_user.configuracion = req.configuracion
        db.add(current_user)
        db.commit()
        db.refresh(current_user)
        return current_user
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al guardar configuración: {str(e)}")


@router.get("/me/config", summary="Obtener configuración del usuario actual")
def api_obtener_configuracion_usuario(
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    """
    Obtiene la configuración JSON del usuario autenticado (ej. enlaces personalizados).
    Devuelve directamente el objeto configuracion o un dict vacío si no existe.
    """
    return current_user.configuracion or {}
