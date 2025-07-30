# back/gestion/configuracion_manager.py

import os
import shutil
from fastapi import UploadFile
from sqlmodel import Session
from back.modelos import ConfiguracionEmpresa, Usuario
from back.schemas.configuracion_schemas import ConfiguracionUpdate

# Creamos una carpeta 'static/uploads' en la raíz del proyecto si no existe
UPLOADS_DIR = os.path.join("static", "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

def obtener_configuracion_por_id_empresa(db: Session, id_empresa: int) -> ConfiguracionEmpresa:
    """
    Obtiene la configuración de una empresa. Si no existe, la crea al vuelo.
    """
    config = db.get(ConfiguracionEmpresa, id_empresa)
    if not config:
        raise ValueError(f"No se encontró una configuración para la empresa con ID {id_empresa}. Esto no debería ocurrir si la empresa fue creada correctamente.")
    return config

def actualizar_configuracion_parcial(db: Session, id_empresa: int, data: ConfiguracionUpdate) -> ConfiguracionEmpresa:
    """
    Actualiza solo los campos de la configuración que vienen en la petición.
    """
    config_db = obtener_configuracion_por_id_empresa(db, id_empresa)
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(config_db, key, value)
        
    db.add(config_db)
    db.commit()
    db.refresh(config_db)
    return config_db

def guardar_archivo_configuracion(db: Session, id_empresa: int, file: UploadFile, tipo_archivo: str) -> ConfiguracionEmpresa:
    """
    Guarda un archivo (logo o ícono) en el disco y actualiza la ruta en la DB.
    """
    if tipo_archivo not in ["logo", "icono"]:
        raise ValueError("El tipo de archivo debe ser 'logo' o 'icono'.")

    config_db = obtener_configuracion_por_id_empresa(db, id_empresa)
    
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"{tipo_archivo}_empresa_{id_empresa}{file_extension}"
    
    file_path = os.path.join(UPLOADS_DIR, filename)
    # La ruta que guardamos en la DB es relativa para que el frontend pueda usarla
    relative_path = f"/{file_path.replace(os.path.sep, '/')}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    if tipo_archivo == 'logo':
        config_db.ruta_logo = relative_path
    elif tipo_archivo == 'icono':
        config_db.ruta_icono = relative_path
        
    db.add(config_db)
    db.commit()
    db.refresh(config_db)
    return config_db