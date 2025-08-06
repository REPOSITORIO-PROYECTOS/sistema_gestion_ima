# back/gestion/configuracion_manager.py

import os
import shutil
from fastapi import UploadFile, HTTPException, status
from sqlmodel import Session
from back.modelos import ConfiguracionEmpresa, Usuario
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

def actualizar_configuracion_parcial(db: Session, id_empresa: int, data: ConfiguracionUpdate) -> ConfiguracionEmpresa:
    config_db = obtener_configuracion_por_id_empresa(db, id_empresa)
    update_data = data.model_dump(exclude_unset=True) # Solo los campos que envía el frontend
    for key, value in update_data.items():
        setattr(config_db, key, value) # Actualiza el campo dinámicamente
    db.add(config_db)
    db.commit()
    db.refresh(config_db)
    return config_db

def obtener_recargo_por_tipo(db: Session, id_empresa: int, tipo: str) -> RecargoData:
    """
    Obtiene el porcentaje y concepto de un tipo de recargo específico
    ('transferencia' o 'banco') para una empresa.
    """
    config_db = obtener_configuracion_por_id_empresa(db, id_empresa)
    
    if tipo == "transferencia":
        return RecargoData(
            porcentaje=config_db.recargo_transferencia,
            concepto=config_db.concepto_recargo_transferencia
        )
    elif tipo == "banco":
        return RecargoData(
            porcentaje=config_db.recargo_banco,
            concepto=config_db.concepto_recargo_banco
        )
    else:
        raise ValueError("Tipo de recargo no válido. Debe ser 'transferencia' o 'banco'.")

def actualizar_recargo_por_tipo(db: Session, id_empresa: int, tipo: str, data: RecargoUpdate) -> RecargoData:
    """
    Actualiza el porcentaje y/o concepto de un tipo de recargo específico
    para una empresa.
    """
    config_db = obtener_configuracion_por_id_empresa(db, id_empresa)

    if tipo == "transferencia":
        config_db.recargo_transferencia = data.porcentaje
        if data.concepto is not None:
            config_db.concepto_recargo_transferencia = data.concepto
    elif tipo == "banco":
        config_db.recargo_banco = data.porcentaje
        if data.concepto is not None:
            config_db.concepto_recargo_banco = data.concepto
    else:
        raise ValueError("Tipo de recargo no válido. Debe ser 'transferencia' o 'banco'.")
        
    db.add(config_db)
    db.commit()
    db.refresh(config_db)
    
    # Devolvemos los datos actualizados usando la otra función para no repetir código
    return obtener_recargo_por_tipo(db, id_empresa, tipo)

def actualizar_ruta_archivo(db: Session, id_empresa: int, tipo_archivo: str, ruta_publica: str) -> ConfiguracionEmpresa:
    """
    Actualiza la ruta del logo o del icono de la empresa en la base de datos.
    
    Args:
        db: La sesión de la base de datos.
        id_empresa: El ID de la empresa a modificar.
        tipo_archivo: Una cadena, debe ser "logo" o "icono".
        ruta_publica: La ruta donde el archivo es accesible públicamente (ej: /static/logos/nombre_archivo.png).
    """
    print(f"Actualizando ruta para '{tipo_archivo}' de la empresa {id_empresa} a: {ruta_publica}")
    
    # Usamos nuestra función auxiliar para asegurarnos de que la configuración exista.
    config_db = obtener_configuracion_empresa(db, id_empresa)

    if tipo_archivo == "logo":
        config_db.ruta_logo = ruta_publica
    elif tipo_archivo == "icono":
        config_db.ruta_icono = ruta_publica
    else:
        # Es importante validar para no intentar modificar campos que no existen.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El tipo de archivo '{tipo_archivo}' no es válido. Debe ser 'logo' o 'icono'."
        )

    db.add(config_db)
    db.commit()
    db.refresh(config_db)

    print(f"Ruta actualizada correctamente en la base de datos.")
    return config_db

def obtener_configuracion_empresa(db: Session, id_empresa: int) -> ConfiguracionEmpresa:
    """
    Obtiene la configuración de una empresa. Si no existe, la crea con valores por defecto.
    Esto asegura que siempre podamos trabajar con un objeto de configuración.
    """
    config = db.get(ConfiguracionEmpresa, id_empresa)
    if not config:
        print(f"No se encontró configuración para la empresa ID {id_empresa}. Creando una nueva.")
        config = ConfiguracionEmpresa(id_empresa=id_empresa)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config

def actualizar_color_principal_empresa(db: Session, id_empresa: int, nuevo_color: str) -> ConfiguracionEmpresa:
    """
    Actualiza específicamente el color principal de la configuración de una empresa.
    Es llamada por el endpoint PATCH /mi-empresa/color.
    """
    print(f"\n--- [TRACE: ACTUALIZAR COLOR] ---")
    print(f"Solicitud para actualizar color de Empresa ID: {id_empresa} a '{nuevo_color}'")

    # 1. Obtenemos el registro de configuración existente usando tu función.
    #    'obtener_configuracion_por_id_empresa' ya maneja el caso de que no exista.
    config_db = obtener_configuracion_por_id_empresa(db, id_empresa)
    
    # 2. Actualizamos únicamente el campo del color en el objeto.
    config_db.color_principal = nuevo_color
    
    # 3. Guardamos los cambios en la base de datos.
    try:
        db.add(config_db)
        db.commit()
        db.refresh(config_db)
        print("   -> ÉXITO. Color actualizado en la base de datos.")
    except Exception as e:
        print(f"   -> ERROR de BD al actualizar el color: {e}")
        db.rollback()
        # Relanzamos la excepción para que el router pueda manejarla
        raise RuntimeError(f"Error de base de datos al actualizar el color: {e}")
        
    print("--- [FIN TRACE] ---\n")
    return config_db