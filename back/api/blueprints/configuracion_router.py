# /back/api/blueprints/configuracion_router.py

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import Session
import shutil # Para manejar archivos
from pathlib import Path

# Dependencias y modelos
from back.database import get_db
from back.security import obtener_usuario_actual
from back.modelos import Usuario
from back.schemas.caja_schemas import RespuestaGenerica

# Lógica de negocio y Schemas
from back.gestion import configuracion_manager
from back.schemas.configuracion_schemas import ConfiguracionResponse, ConfiguracionUpdate, RecargoData, RecargoUpdate, ColorResponse, ColorUpdateRequest, ConfiguracionUpdate 
from pydantic import BaseModel

router = APIRouter(prefix="/configuracion", tags=["Configuración de Empresa"])

# Ruta absoluta al directorio static del backend (independiente del cwd de uvicorn/PM2).
_BACK_DIR = Path(__file__).resolve().parents[2]
STATIC_DIR = _BACK_DIR / "static" / "logos_empresas"
# Compatibilidad: uploads viejos con Path("back/static/...") cuando cwd era back/
STATIC_DIR_LEGACY = _BACK_DIR / "back" / "static" / "logos_empresas"
STATIC_DIR.mkdir(parents=True, exist_ok=True)


def _resolver_archivo_logo(ruta: str | None) -> Path | None:
    """Busca el archivo de logo en disco (ruta actual o legacy)."""
    if not ruta or "logos_empresas" not in ruta:
        return None
    nombre = Path(ruta).name
    for base in (STATIC_DIR, STATIC_DIR_LEGACY):
        archivo = base / nombre
        if archivo.is_file():
            return archivo
    return None


def _configuracion_respuesta(config) -> ConfiguracionResponse:
    """Arma la respuesta y evita rutas de logo huérfanas en BD (archivo no en disco)."""
    respuesta = ConfiguracionResponse.model_validate(config)
    ruta = respuesta.ruta_logo
    if ruta and "logos_empresas" in ruta:
        if _resolver_archivo_logo(ruta) is None:
            respuesta = respuesta.model_copy(update={"ruta_logo": None})
    return respuesta


def verificar_permiso_admin(usuario: Usuario):
    """
    Función de seguridad reutilizable que asegura que solo un 'Admin'
    pueda acceder a los endpoints de configuración de su propia empresa.
    """
    if usuario.rol.nombre != "Admin":
        raise HTTPException(status_code=403, detail="Permiso denegado. Se requiere rol de Administrador.")


@router.get("/mi-empresa", response_model=ConfiguracionResponse)
def obtener_mi_configuracion(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    """Obtiene la configuración completa de la empresa del usuario autenticado."""
    
    # --- VERIFICACIÓN DE SEGURIDAD AÑADIDA ---
    if not current_user.id_empresa:
        raise HTTPException(
            status_code=404, # Usamos 404 porque la "configuración de su empresa" no se encuentra
            detail="El usuario actual no está asociado a ninguna empresa."
        )
    
    # Esta línea ahora es segura porque sabemos que current_user.id_empresa no es None
    config = configuracion_manager.obtener_configuracion_empresa(db, current_user.id_empresa)
    if not config:
        raise HTTPException(
            status_code=404,
            detail="No se encontró un registro de configuración para la empresa de este usuario."
        )
    return _configuracion_respuesta(config)

@router.post("/upload-logo", response_model=RespuestaGenerica)
async def subir_logo_empresa(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual),
    archivo: UploadFile = File(...)
):
    """Sube o reemplaza el logo de la empresa."""
    verificar_permiso_admin(current_user)

    if not current_user.id_empresa:
        raise HTTPException(status_code=404, detail="El usuario no está asociado a una empresa.")

    file_extension = Path(archivo.filename or "").suffix.lower() or ".png"
    if file_extension not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise HTTPException(status_code=400, detail="Formato no permitido. Use .png, .jpg, .jpeg o .webp.")

    file_name = f"logo_empresa_{current_user.id_empresa}{file_extension}"
    file_path = STATIC_DIR / file_name

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(archivo.file, buffer)

    public_path = f"/static/logos_empresas/{file_name}"
    configuracion_manager.actualizar_ruta_archivo(db, current_user.id_empresa, "logo", public_path)

    return RespuestaGenerica(status="ok", message=f"Logo subido correctamente. Ruta: {public_path}")

@router.post("/upload-icono", response_model=RespuestaGenerica)
async def subir_icono_empresa(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual),
    archivo: UploadFile = File(...)
):
    """Sube o reemplaza el icono de la empresa."""
    verificar_permiso_admin(current_user)

    if not current_user.id_empresa:
        raise HTTPException(status_code=404, detail="El usuario no está asociado a una empresa.")

    file_extension = Path(archivo.filename or "").suffix.lower() or ".png"
    if file_extension not in {".png", ".jpg", ".jpeg", ".webp", ".ico"}:
        raise HTTPException(status_code=400, detail="Formato no permitido para icono.")

    file_name = f"icono_empresa_{current_user.id_empresa}{file_extension}"
    file_path = STATIC_DIR / file_name

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(archivo.file, buffer)

    public_path = f"/static/logos_empresas/{file_name}"
    configuracion_manager.actualizar_ruta_archivo(db, current_user.id_empresa, "icono", public_path)

    return RespuestaGenerica(status="ok", message=f"Icono subido correctamente. Ruta: {public_path}")

@router.patch(
    "/mi-empresa/color",
    response_model=ColorResponse,
    summary="Actualiza el color principal de la empresa del usuario"
)
def actualizar_color_de_mi_empresa(
    req: ColorUpdateRequest, # El cuerpo de la petición: {"color_principal": "#FFFFFF"}
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    """
    Actualiza el color principal configurado para la empresa del usuario autenticado.
    """
    # Verificamos que el usuario pertenezca a una empresa
    if not current_user.id_empresa:
        raise HTTPException(
            status_code=404,
            detail="El usuario actual no está asociado a ninguna empresa."
        )
    
    # Verificamos que el usuario tenga permiso para cambiar la configuración
    verificar_permiso_admin(current_user)
        
    try:
        # Llamamos a nuestra nueva función específica del manager
        config_actualizada = configuracion_manager.actualizar_color_principal_empresa(
            db=db, 
            id_empresa=current_user.id_empresa,
            nuevo_color=req.color_principal
        )
        
        # Devolvemos el dato actualizado en el formato correcto
        return ColorResponse(color_principal=config_actualizada.color_principal)
        
    except ValueError as e:
        # Captura el error si el manager no encuentra la configuración
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Captura cualquier otro error inesperado
        raise HTTPException(status_code=500, detail=f"Error interno: {e}")

@router.patch("/mi-empresa", response_model=ConfiguracionResponse)
def actualizar_mi_configuracion(
    data: ConfiguracionUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    """Actualiza parcialmente la configuración de la propia empresa del usuario."""
    verificar_permiso_admin(current_user) # Reutilizamos tu función de verificación de rol

    # --- VERIFICACIÓN DE SEGURIDAD AÑADIDA ---
    if not current_user.id_empresa:
        raise HTTPException(status_code=404, detail="El usuario actual no está asociado a ninguna empresa.")

    # Modo especial solo lo habilita super-admin desde el panel de empresas
    update_data = data.model_dump(exclude_unset=True)
    update_data.pop("modo_especial_habilitado", None)
    data = ConfiguracionUpdate(**update_data)

    try:
        config_actualizada = configuracion_manager.actualizar_configuracion_parcial(
            db=db,
            id_empresa=current_user.id_empresa,
            data=data
        )
        return _configuracion_respuesta(config_actualizada)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {e}")

 
class LinkUpdate(BaseModel):
    link: str | None


@router.get("/mi-empresa/link/{num}")
def get_link_mi_empresa(
    num: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    """Devuelve uno de los tres links configurados para la empresa (1,2 o 3)."""
    if not current_user.id_empresa:
        raise HTTPException(status_code=404, detail="El usuario actual no está asociado a ninguna empresa.")

    if num not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="Número de link inválido. Debe ser 1, 2 o 3.")

    config = configuracion_manager.obtener_configuracion_empresa(db, current_user.id_empresa)
    mapping = {1: config.link_visual_1, 2: config.link_visual_2, 3: config.link_visual_3}
    return {"link": mapping[num]}


@router.patch("/mi-empresa/link/{num}")
def patch_link_mi_empresa(
    num: int,
    payload: LinkUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    """Actualiza uno de los tres links visuales (requiere rol Admin)."""
    verificar_permiso_admin(current_user)

    if not current_user.id_empresa:
        raise HTTPException(status_code=404, detail="El usuario actual no está asociado a ninguna empresa.")

    if num not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="Número de link inválido. Debe ser 1, 2 o 3.")

    # Llamamos al manager para guardar solo el link correspondiente
    if num == 1:
        config_actualizada = configuracion_manager.guardar_links_empresa(db, current_user.id_empresa, link1=payload.link)
    elif num == 2:
        config_actualizada = configuracion_manager.guardar_links_empresa(db, current_user.id_empresa, link2=payload.link)
    else:
        config_actualizada = configuracion_manager.guardar_links_empresa(db, current_user.id_empresa, link3=payload.link)

    return {"link": (payload.link)}
    
@router.get("/mi-empresa/recargo/transferencia", response_model=RecargoData)
def get_recargo_transferencia(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    """Obtiene el recargo por transferencia de la empresa del usuario autenticado."""
    # --- VERIFICACIÓN DE SEGURIDAD AÑADIDA ---
    if not current_user.id_empresa:
        raise HTTPException(status_code=404, detail="El usuario actual no está asociado a ninguna empresa.")

    try:
        return configuracion_manager.obtener_recargo_por_tipo(db, current_user.id_empresa, "transferencia")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.patch(
    "/mi-empresa/recargo/transferencia",
    response_model=RecargoData,
    summary="Actualiza el recargo por Transferencia"
)
def patch_recargo_transferencia(
    data: RecargoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    """Actualiza el recargo por transferencia de la empresa del usuario autenticado."""
    try:
        return configuracion_manager.actualizar_recargo_por_tipo(db, current_user.id_empresa, "transferencia", data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get(
    "/mi-empresa/recargo/banco",
    response_model=RecargoData,
    summary="Obtiene el recargo actual por Pago Bancario"
)
def get_recargo_banco(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    """Obtiene el recargo por pago bancario de la empresa del usuario autenticado."""
    try:
        return configuracion_manager.obtener_recargo_por_tipo(db, current_user.id_empresa, "banco")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.patch(
    "/mi-empresa/recargo/banco",
    response_model=RecargoData,
    summary="Actualiza el recargo por Pago Bancario"
)
def patch_recargo_banco(
    data: RecargoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    """Actualiza el recargo por pago bancario de la empresa del usuario autenticado."""
    try:
        return configuracion_manager.actualizar_recargo_por_tipo(db, current_user.id_empresa, "banco", data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
   
