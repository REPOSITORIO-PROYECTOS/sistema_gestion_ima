# back/gestion/caja/consultas_caja.py
import logging
from sqlmodel import Session, select
from typing import List
from back.modelos import CajaSesion, Usuario

def obtener_arqueos_de_caja(db: Session) -> List[dict]:
    """
    Obtiene un listado de todas las cajas cerradas con sus resultados de arqueo.
    """
    logging.info("Solicitando listado de arqueos de caja desde SQL.")
    try:
        consulta = (
            select(CajaSesion, Usuario.nombre_usuario)
            .join(Usuario, CajaSesion.id_usuario_apertura == Usuario.id)
            .where(CajaSesion.estado == "CERRADA")
            .order_by(CajaSesion.fecha_cierre.desc())
        )
        resultados = db.exec(consulta).all()
        
        arqueos = []
        for sesion, nombre_usuario in resultados:
            arqueos.append({
                "id_sesion": sesion.id, "fecha_apertura": sesion.fecha_apertura,
                "fecha_cierre": sesion.fecha_cierre, "usuario_apertura": nombre_usuario,
                "saldo_inicial": sesion.saldo_inicial,
                "saldo_final_declarado": sesion.saldo_final_declarado,
                "saldo_final_calculado": sesion.saldo_final_calculado,
                "diferencia": sesion.diferencia
            })
        return arqueos
    except Exception as e:
        logging.error(f"Error al obtener los arqueos de caja desde SQL: {e}")
        return []