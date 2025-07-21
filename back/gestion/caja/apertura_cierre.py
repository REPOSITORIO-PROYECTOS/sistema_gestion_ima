# back/gestion/caja/apertura_cierre.py 
from datetime import datetime
from sqlmodel import Session, select, func
from typing import Optional

from back.modelos import Usuario, CajaSesion, CajaMovimiento

def obtener_caja_abierta_por_usuario(db: Session, usuario: Usuario) -> Optional[CajaSesion]:
    """Verifica si un usuario específico tiene una caja abierta usando ORM."""
    statement = select(CajaSesion).where(
        CajaSesion.id_usuario_apertura == usuario.id,
        CajaSesion.estado == "ABIERTA"
    )
    return db.exec(statement).first()

def abrir_caja(db: Session, usuario_apertura: Usuario, saldo_inicial: float) -> CajaSesion:
    """Abre una nueva sesión de caja para un usuario usando ORM."""
    if obtener_caja_abierta_por_usuario(db, usuario_apertura):
        raise ValueError(f"El usuario '{usuario_apertura.nombre_usuario}' ya tiene una caja abierta.")

    nueva_sesion = CajaSesion(
        saldo_inicial=saldo_inicial,
        id_usuario_apertura=usuario_apertura.id,
        estado="ABIERTA"
    )
    db.add(nueva_sesion)
    db.commit()
    db.refresh(nueva_sesion)

    movimiento_apertura = CajaMovimiento(
        tipo="APERTURA",
        concepto="Saldo inicial de caja",
        monto=saldo_inicial,
        metodo_pago="N/A",
        id_caja_sesion=nueva_sesion.id,
        id_usuario=usuario_apertura.id
    )
    db.add(movimiento_apertura)
    db.commit()
    db.refresh(nueva_sesion)
    
    return nueva_sesion

def cerrar_caja(db: Session, usuario_cierre: Usuario, saldo_final_declarado: float) -> CajaSesion:
    """Cierra la sesión de caja abierta del usuario que realiza la acción usando ORM."""
    sesion_a_cerrar = obtener_caja_abierta_por_usuario(db, usuario_cierre)
    if not sesion_a_cerrar:
        raise ValueError(f"El usuario '{usuario_cierre.nombre_usuario}' no tiene ninguna caja abierta para cerrar.")

    suma_movimientos = db.exec(
        select(func.sum(CajaMovimiento.monto))
        .where(CajaMovimiento.id_caja_sesion == sesion_a_cerrar.id)
        .where(CajaMovimiento.tipo != "APERTURA")
    ).first() or 0.0

    saldo_final_calculado = sesion_a_cerrar.saldo_inicial + suma_movimientos
    diferencia = saldo_final_declarado - saldo_final_calculado

    sesion_a_cerrar.estado = "CERRADA"
    sesion_a_cerrar.fecha_cierre = datetime.utcnow()
    sesion_a_cerrar.id_usuario_cierre = usuario_cierre.id
    sesion_a_cerrar.saldo_final_declarado = saldo_final_declarado
    sesion_a_cerrar.saldo_final_calculado = round(saldo_final_calculado, 2)
    sesion_a_cerrar.diferencia = round(diferencia, 2)
    
    db.add(sesion_a_cerrar)
    db.commit()
    db.refresh(sesion_a_cerrar)
    return sesion_a_cerrar