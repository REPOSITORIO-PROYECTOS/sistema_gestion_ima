# back/api/admin_router.py
from fastapi import APIRouter, HTTPException, Depends, Header, Body
from typing import Optional

# --- Importaciones de Lógica de Negocio ---
from back.gestion import auth as mod_auth
from back.gestion.caja import apertura_cierre as mod_apertura_cierre
from back.security import es_admin

# --- Importaciones de Modelos Pydantic ---
from .caja_router import RespuestaGenerica, CerrarCajaRequest # Reutilizamos los modelos
from pydantic import BaseModel


router = APIRouter(
    prefix="/admin",
    tags=["Administración"],
    dependencies=[Depends(es_admin)] # ¡TODA la sección de admin está protegida!
)

# --- Dependencia para Verificar Token de Administrador ---
# Esta es nuestra "puerta de seguridad" para los endpoints de admin.
async def verificar_token_admin_dependencia(x_admin_token: Optional[str] = Header(None)):
    if not x_admin_token:
        raise HTTPException(status_code=401, detail="Cabecera X-Admin-Token requerida para esta operación.")
    
    # Aquí iría la lógica para validar el token contra la base de datos
    # Por ahora, usamos la lógica de `mod_auth` que pronto migraremos a MySQL
    is_valid = mod_auth.verificar_admin_token_ficticio(x_admin_token) # Usaremos una función ficticia por ahora
    if not is_valid:
        raise HTTPException(status_code=403, detail="Token de Administrador inválido o expirado.")
    return True

# --- Creación del Router ---
router = APIRouter(
    prefix="/admin",
    tags=["Administración"],
    dependencies=[Depends(verificar_token_admin_dependencia)] # ¡Toda la sección requiere token!
)

# --- Endpoints de Administración ---

@router.post("/caja/cerrar", response_model=RespuestaGenerica)
async def api_cerrar_caja(request_data: CerrarCajaRequest):
    """
    Cierra la sesión de caja activa. Requiere token de administrador en la cabecera.
    """
    # La validación del token ya la hizo la dependencia del router.
    # Aquí llamaremos a la función de negocio que migraremos a MySQL.
    
    # Esta es la función que debemos crear/migrar
    resultado = mod_apertura_cierre.cerrar_caja(
        id_sesion=request_data.id_sesion,
        saldo_final_contado=request_data.saldo_final_contado,
        usuario_cierre=request_data.usuario_cierre
    )
    
    if resultado.get("status") == "success":
        return RespuestaGenerica(status="success", message=resultado.get("message"), data={"id_sesion": resultado.get("id_sesion"), "diferencia": resultado.get("diferencia")})
    else:
        raise HTTPException(status_code=400, detail=resultado.get("message", "Error al cerrar caja."))

@router.post("/token/nuevo", response_model=RespuestaGenerica)
async def api_generar_nuevo_token_admin(usuario_solicitante: str = Body(..., embed=True)):
    """
    Genera un nuevo token de administrador. Requiere un token de admin válido en la cabecera.
    """
    # La lógica actual de `mod_auth` de guardar en un archivo se migrará a una tabla en DB.
    # Por ahora, la llamada se mantiene igual.
    nuevo_token = mod_auth.generar_token_ficticio(usuario_generador=usuario_solicitante)
    return RespuestaGenerica(status="success", message=f"Nuevo token de admin generado.", data={"nuevo_token": nuevo_token})