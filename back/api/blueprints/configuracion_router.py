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
from back.schemas.configuracion_schemas import ConfiguracionRead, ConfiguracionUpdate

router = APIRouter(prefix="/configuracion", tags=["Configuración de Empresa"])

# Definimos la ruta base para los archivos estáticos
STATIC_DIR = Path("back/static/logos_empresas")
STATIC_DIR.mkdir(parents=True, exist_ok=True) # Asegura que el directorio exista

@router.get("/mi-empresa", response_model=ConfiguracionRead)
def obtener_mi_configuracion(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    """Obtiene la configuración completa de la empresa del usuario autenticado."""
    config = configuracion_manager.obtener_configuracion_empresa(db, current_user.id_empresa)
    return config

@router.patch("/mi-empresa", response_model=ConfiguracionRead)
def actualizar_mi_configuracion(
    req: ConfiguracionUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    """Actualiza los datos de configuración de la empresa del usuario."""
    config_actualizada = configuracion_manager.actualizar_configuracion_empresa(db, current_user.id_empresa, req)
    return config_actualizada

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

# Podrías crear un endpoint similar para `/upload-icono` si lo necesitas