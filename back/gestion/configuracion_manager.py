# back/gestion/configuracion_manager.py

# /back/gestion/configuracion_manager.py

from sqlmodel import Session
from fastapi import HTTPException

from back.modelos import ConfiguracionEmpresa
from back.schemas.configuracion_schemas import ConfiguracionUpdate

def obtener_configuracion_empresa(db: Session, id_empresa: int) -> ConfiguracionEmpresa:
    """
    Obtiene la configuración de una empresa. Si no existe, crea una por defecto y la devuelve.
    Esto asegura que el frontend siempre reciba un objeto de configuración válido.
    """
    config = db.get(ConfiguracionEmpresa, id_empresa)
    
    if not config:
        # No existe configuración, creamos una con valores por defecto
        config = ConfiguracionEmpresa(id_empresa=id_empresa)
        db.add(config)
        db.commit()
        db.refresh(config)
        
    return config

def actualizar_configuracion_empresa(db: Session, id_empresa: int, data_update: ConfiguracionUpdate) -> ConfiguracionEmpresa:
    """Actualiza la configuración de una empresa con los datos proporcionados."""
    
    config_db = obtener_configuracion_empresa(db, id_empresa) # Usamos la función anterior para asegurar que exista

    # Obtenemos los datos del schema de Pydantic que no son None
    update_data = data_update.model_dump(exclude_unset=True)

    # Iteramos y actualizamos solo los campos enviados
    for key, value in update_data.items():
        setattr(config_db, key, value)
        
    db.add(config_db)
    db.commit()
    db.refresh(config_db)
    
    return config_db

def actualizar_ruta_archivo(db: Session, id_empresa: int, tipo: str, ruta: str) -> ConfiguracionEmpresa:
    """Actualiza la ruta del logo o del icono de la empresa."""
    
    config_db = obtener_configuracion_empresa(db, id_empresa)
    
    if tipo == "logo":
        config_db.ruta_logo = ruta
    elif tipo == "icono":
        config_db.ruta_icono = ruta
    else:
        raise HTTPException(status_code=400, detail="Tipo de archivo no válido. Debe ser 'logo' o 'icono'.")
        
    db.add(config_db)
    db.commit()
    db.refresh(config_db)
    
    return config_db


RAZONES_DE_EGRESO_COMUNES = [
    "Pago a proveedor menor",
    "Pago de delivery / mensajería",
    "Compra de artículos de limpieza",
    "Compra de insumos de oficina",
    "Adelanto de sueldo",
    "Retiro de socio",
    "Otros gastos"
]

def obtener_razones_de_egreso():
    """Devuelve la lista de razones de egreso predefinidas."""
    return RAZONES_DE_EGRESO_COMUNES