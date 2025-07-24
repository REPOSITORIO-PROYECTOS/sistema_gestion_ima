# back/gestion/caja/consultas_caja.py
# VERSIÓN CORREGIDA Y UNIFICADA

import logging
from sqlmodel import Session, select
from typing import List, Dict, Any

# Importamos los modelos necesarios, creando alias para evitar conflictos en el JOIN
from back.modelos import CajaSesion
from back.modelos import Usuario as UsuarioApertura
from back.modelos import Usuario as UsuarioCierre

def obtener_arqueos_de_caja(db: Session) -> Dict[str, List[Dict[str, Any]]]:
    """
    Obtiene un informe completo con dos listas: una de cajas cerradas (arqueos)
    y otra de cajas actualmente abiertas. Mantiene el nombre original de la función.
    """
    logging.info("Solicitando informe unificado de cajas (abiertas y cerradas).")
    
    informe_final = {
        "cajas_abiertas": [],
        "arqueos_cerrados": []
    }

    try:
        # --- CONSULTA 1: OBTENER ARQUEOS DE CAJAS CERRADAS ---
        consulta_cerradas = (
            select(CajaSesion, UsuarioApertura.nombre_usuario, UsuarioCierre.nombre_usuario)
            .join(UsuarioApertura, CajaSesion.id_usuario_apertura == UsuarioApertura.id)
            .join(UsuarioCierre, CajaSesion.id_usuario_cierre == UsuarioCierre.id, isouter=True)
            .where(CajaSesion.estado == "CERRADA")
            .order_by(CajaSesion.fecha_cierre.desc())
        )
        resultados_cerradas = db.exec(consulta_cerradas).all()
        
        for sesion, nombre_usuario_apertura, nombre_usuario_cierre in resultados_cerradas:
            informe_final["arqueos_cerrados"].append({
                "id_sesion": sesion.id,
                "fecha_apertura": sesion.fecha_apertura,
                "fecha_cierre": sesion.fecha_cierre,
                "usuario_apertura": nombre_usuario_apertura,
                "usuario_cierre": nombre_usuario_cierre,
                "saldo_inicial": sesion.saldo_inicial,
                "saldo_final_declarado": sesion.saldo_final_declarado,
                "saldo_final_calculado": sesion.saldo_final_calculado,
                "diferencia": sesion.diferencia
            })

        # --- CONSULTA 2: OBTENER CAJAS ACTUALMENTE ABIERTAS ---
        consulta_abiertas = (
            select(CajaSesion, UsuarioApertura.nombre_usuario)
            .join(UsuarioApertura, CajaSesion.id_usuario_apertura == UsuarioApertura.id)
            .where(CajaSesion.estado == "ABIERTA")
            .order_by(CajaSesion.fecha_apertura.asc())
        )
        resultados_abiertas = db.exec(consulta_abiertas).all()

        for sesion, nombre_usuario_apertura in resultados_abiertas:
            informe_final["cajas_abiertas"].append({
                "id_sesion": sesion.id,
                "fecha_apertura": sesion.fecha_apertura,
                "usuario_apertura": nombre_usuario_apertura,
                "saldo_inicial": sesion.saldo_inicial
            })
            
        return informe_final

    except Exception as e:
        logging.error(f"Error al generar el informe de cajas: {e}")
        return informe_final