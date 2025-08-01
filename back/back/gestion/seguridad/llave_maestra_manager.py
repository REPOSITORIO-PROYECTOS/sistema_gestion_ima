# back/gestion/seguridad/llave_maestra_manager.py

import datetime
from sqlmodel import Session, select
from back.modelos import LlaveMaestra
from back.utils.generador_llaves import generar_nueva_llave

def obtener_o_crear_llave_maestra(db: Session) -> LlaveMaestra:
    """
    Obtiene la llave maestra de la BD. Si no existe o ha expirado,
    crea una nueva y la guarda, asegurando que siempre haya una única llave válida.
    """
    ahora = datetime.datetime.utcnow()
    
    # 1. Intentar obtener la llave existente de la base de datos
    statement = select(LlaveMaestra).limit(1)
    llave_obj = db.exec(statement).first()

    # 2. Si no hay ninguna llave en la BD o si la que hay ya expiró
    if not llave_obj or ahora >= llave_obj.fecha_expiracion:
        nueva_llave_str = generar_nueva_llave()
        # La nueva llave será válida por 24 horas
        nueva_fecha_expiracion = ahora + datetime.timedelta(hours=24)
        
        if llave_obj:
            # Si existía pero expiró, actualizamos la fila existente
            print(f"🔄 LLAVE MAESTRA EXPIRADA. Generando una nueva...")
            llave_obj.llave = nueva_llave_str
            llave_obj.fecha_creacion = ahora
            llave_obj.fecha_expiracion = nueva_fecha_expiracion
        else:
            # Si no existía, creamos una nueva fila
            print(f"🔑 PRIMERA LLAVE MAESTRA. Generando una nueva...")
            llave_obj = LlaveMaestra(
                llave=nueva_llave_str,
                fecha_expiracion=nueva_fecha_expiracion
            )
            db.add(llave_obj)
        
        # Guardar los cambios en la base de datos
        db.commit()
        db.refresh(llave_obj)
        print(f"✅ NUEVA LLAVE MAESTRA GUARDADA: '{llave_obj.llave}' (Válida hasta {llave_obj.fecha_expiracion.isoformat()}Z)")

    return llave_obj


# --- Funciones públicas que usará la API ---

def validar_llave_maestra(llave_proporcionada: str, db: Session) -> bool:
    """
    Compara una llave proporcionada con la llave maestra persistida en la BD.
    """
    if not llave_proporcionada or not isinstance(llave_proporcionada, str):
        return False
        
    llave_obj_actual = obtener_o_crear_llave_maestra(db)
    # Comparación segura que no distingue mayúsculas/minúsculas y quita espacios
    return llave_proporcionada.lower().strip() == llave_obj_actual.llave.lower().strip()

def obtener_llave_actual_para_admin(db: Session) -> dict:
    """
    Función segura para que un admin pueda consultar la llave actual desde la BD.
    """
    llave_obj = obtener_o_crear_llave_maestra(db)
    return {
        "llave_maestra": llave_obj.llave,
        "expira_en": llave_obj.fecha_expiracion.isoformat() + "Z"
    }