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
from back.schemas.configuracion_schemas import ConfiguracionResponse, ConfiguracionUpdate

router = APIRouter(prefix="/configuracion", tags=["Configuración de Empresa"])

def verificar_permiso_admin(usuario: Usuario):
    """
    Función de seguridad reutilizable que asegura que solo un 'Admin'
    pueda acceder a los endpoints de configuración de su propia empresa.
    """
    if usuario.rol.nombre != "Admin":
        raise HTTPException(status_code=403, detail="Permiso denegado. Se requiere rol de Administrador.")

# Definimos la ruta base para los archivos estáticos
STATIC_DIR = Path("back/static/logos_empresas")
STATIC_DIR.mkdir(parents=True, exist_ok=True) # Asegura que el directorio exista

@router.get("/mi-empresa", response_model=ConfiguracionResponse)
def obtener_mi_configuracion(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    """Obtiene la configuración completa de la empresa del usuario autenticado."""
    config = configuracion_manager.obtener_configuracion_empresa(db, current_user.id_empresa)
    return config


@router.post("/upload-logo", response_model=RespuestaGenerica)
async def subir_logo_empresa(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual),
    archivo: UploadFile = File(...)
):
    """Sube o reemplaza el logo de la empresa."""
    
    # Generamos un nombre de archivo único para evitar colisiones
    file_extension = Path(archivo.filename).suffix
    file_name = f"logo_empresa_{current_user.id_empresa}{file_extension}"
    file_path = STATIC_DIR / file_name
    
    # Guardamos el archivo en el disco
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(archivo.file, buffer)
        
    # Guardamos la ruta PÚBLICA en la base de datos
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
    
    # Generamos un nombre de archivo único para evitar colisiones
    file_extension = Path(archivo.filename).suffix
    file_name = f"icono_empresa_{current_user.id_empresa}{file_extension}"
    file_path = STATIC_DIR / file_name
    
    # Guardamos el archivo en el disco
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(archivo.file, buffer)
        
    # Guardamos la ruta PÚBLICA en la base de datos
    public_path = f"/static/logos_empresas/{file_name}"
    configuracion_manager.actualizar_ruta_archivo(db, current_user.id_empresa, "icono", public_path)
    
    return RespuestaGenerica(status="ok", message=f"Icono subido correctamente. Ruta: {public_path}")

@router.patch(
    "/mi-empresa", # <-- RUTA CORREGIDA: Genérica y segura
    response_model=ConfiguracionResponse,
    dependencies=[Depends(verificar_permiso_admin)] # <-- SEGURIDAD AÑADIDA
)
def actualizar_mi_configuracion(
    data: ConfiguracionUpdate, # <-- El frontend envía aquí {"recargo_transferencia": 12.5}
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual) # <-- SEGURIDAD AÑADIDA
):
    """
    Actualiza parcialmente la configuración de la propia empresa del usuario.
    Sirve para cambiar el nombre, el color, o los recargos por transferencia.
    """
    try:
        # La función del manager es llamada de forma segura con el id_empresa del usuario
        config_actualizada = configuracion_manager.actualizar_configuracion_parcial(
            db=db,
            id_empresa=current_user.id_empresa,
            data=data
        )
        return config_actualizada
    except ValueError as e:
        # MANEJO DE ERRORES AÑADIDO
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {e}")