# back/gestion/configuracion_manager.py

import os
import shutil
from fastapi import UploadFile, HTTPException, status
from sqlmodel import Session
from back.modelos import ConfiguracionEmpresa, Empresa
from back.schemas.configuracion_schemas import ConfiguracionUpdate, RecargoData, RecargoUpdate

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

def guardar_links_empresa(db: Session, id_empresa: int, link1: str | None = None, link2: str | None = None, link3: str | None = None) -> ConfiguracionEmpresa:
    """Guarda o actualiza los tres links visuales de la empresa."""
    config_db = obtener_configuracion_por_id_empresa(db, id_empresa)

    if link1 is not None:
        config_db.link_visual_1 = link1
    if link2 is not None:
        config_db.link_visual_2 = link2
    if link3 is not None:
        config_db.link_visual_3 = link3

    db.add(config_db)
    db.commit()
    db.refresh(config_db)
    return config_db

def actualizar_configuracion_parcial(db: Session, id_empresa: int, data: ConfiguracionUpdate) -> ConfiguracionEmpresa:
    """
    Actualiza solo los campos de la configuración que vienen en la petición.
    También puede actualizar nombre_legal y nombre_fantasia en la tabla Empresa.
    """
    config_db = obtener_configuracion_por_id_empresa(db, id_empresa)
    
    campos_empresa = {'nombre_legal', 'nombre_fantasia'}
    update_data = data.model_dump(exclude_unset=True)
    
    campos_a_actualizar_empresa = {k: v for k, v in update_data.items() if k in campos_empresa}
    if campos_a_actualizar_empresa:
        empresa = db.get(Empresa, id_empresa)
        if empresa:
            for key, value in campos_a_actualizar_empresa.items():
                setattr(empresa, key, value)
            db.add(empresa)
    
    campos_config = {k: v for k, v in update_data.items() if k not in campos_empresa}
    for key, value in campos_config.items():
        setattr(config_db, key, value)
    
    db.add(config_db)
    db.commit()
    db.refresh(config_db)
    return config_db

def obtener_recargo_por_tipo(db: Session, id_empresa: int, tipo: str) -> RecargoData:
    """Obtiene el porcentaje y concepto de un tipo de recargo específico."""
    config_db = obtener_configuracion_por_id_empresa(db, id_empresa)
    
    if tipo == "transferencia":
        return RecargoData(
            porcentaje=config_db.recargo_transferencia,
            concepto=config_db.concepto_recargo_transferencia,
            habilitado=bool(getattr(config_db, "recargo_transferencia_habilitado", False)),
        )
    elif tipo == "banco":
        return RecargoData(
            porcentaje=config_db.recargo_banco,
            concepto=config_db.concepto_recargo_banco,
            habilitado=bool(getattr(config_db, "recargo_banco_habilitado", False)),
        )
    else:
        raise ValueError("Tipo de recargo no válido. Debe ser 'transferencia' o 'banco'.")

def actualizar_recargo_por_tipo(db: Session, id_empresa: int, tipo: str, data: RecargoUpdate) -> RecargoData:
    """Actualiza el porcentaje y/o concepto de un tipo de recargo específico."""
    config_db = obtener_configuracion_por_id_empresa(db, id_empresa)

    if tipo == "transferencia":
        if data.porcentaje is not None:
            config_db.recargo_transferencia = data.porcentaje
        if data.concepto is not None:
            config_db.concepto_recargo_transferencia = data.concepto
        if data.habilitado is not None:
            config_db.recargo_transferencia_habilitado = data.habilitado
    elif tipo == "banco":
        if data.porcentaje is not None:
            config_db.recargo_banco = data.porcentaje
        if data.concepto is not None:
            config_db.concepto_recargo_banco = data.concepto
        if data.habilitado is not None:
            config_db.recargo_banco_habilitado = data.habilitado
    else:
        raise ValueError("Tipo de recargo no válido. Debe ser 'transferencia' o 'banco'.")
        
    db.add(config_db)
    db.commit()
    db.refresh(config_db)
    
    return obtener_recargo_por_tipo(db, id_empresa, tipo)

def actualizar_ruta_archivo(db: Session, id_empresa: int, tipo_archivo: str, ruta_publica: str) -> ConfiguracionEmpresa:
    """Actualiza la ruta del logo o del icono de la empresa en la base de datos."""
    config_db = obtener_configuracion_empresa(db, id_empresa)

    if tipo_archivo == "logo":
        config_db.ruta_logo = ruta_publica
    elif tipo_archivo == "icono":
        config_db.ruta_icono = ruta_publica
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El tipo de archivo '{tipo_archivo}' no es válido. Debe ser 'logo' o 'icono'."
        )

    db.add(config_db)
    db.commit()
    db.refresh(config_db)
    return config_db

def obtener_configuracion_empresa(db: Session, id_empresa: int) -> ConfiguracionEmpresa:
    """
    Obtiene la configuración de una empresa. Si no existe, la crea con valores por defecto.
    """
    config = db.get(ConfiguracionEmpresa, id_empresa)
    if not config:
        empresa = db.get(Empresa, id_empresa)
        cuit_val = empresa.cuit if empresa and getattr(empresa, "cuit", None) else ""
        nombre_val = None
        if empresa:
            nombre_val = empresa.nombre_fantasia or empresa.nombre_legal
        config = ConfiguracionEmpresa(
            id_empresa=id_empresa,
            cuit=cuit_val,
            nombre_negocio=nombre_val
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config

def es_modo_especial_habilitado(db: Session, id_empresa: int) -> bool:
    """Indica si la empresa opera en modo especial (sin sincronización con Google Sheets)."""
    config = db.get(ConfiguracionEmpresa, id_empresa)
    return bool(config and getattr(config, "modo_especial_habilitado", False))

def actualizar_color_principal_empresa(db: Session, id_empresa: int, nuevo_color: str) -> ConfiguracionEmpresa:
    """Actualiza específicamente el color principal de la configuración de una empresa."""
    config_db = obtener_configuracion_por_id_empresa(db, id_empresa)
    config_db.color_principal = nuevo_color
    
    try:
        db.add(config_db)
        db.commit()
        db.refresh(config_db)
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Error de base de datos al actualizar el color: {e}")
        
    return config_db
