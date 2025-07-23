# back/gestion/caja/apertura_cierre.py
# VERSIÓN CORREGIDA CON TRACE DE REGISTRO

from datetime import datetime
from sqlmodel import Session, select, func
from sqlalchemy import case
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
    print("\n--- [TRACE: ABRIR CAJA] ---")
    print(f"1. Solicitud de apertura para usuario: '{usuario_apertura.nombre_usuario}', Saldo Inicial: {saldo_inicial}")

    if obtener_caja_abierta_por_usuario(db, usuario_apertura):
        raise ValueError(f"El usuario '{usuario_apertura.nombre_usuario}' ya tiene una caja abierta.")

    nueva_sesion = CajaSesion(
        saldo_inicial=saldo_inicial,
        id_usuario_apertura=usuario_apertura.id,
        estado="ABIERTA"
    )

    try:
        db.add(nueva_sesion)
        print("2. Intentando registrar la nueva sesión de caja...")
        db.commit()
        db.refresh(nueva_sesion)
        print(f"   -> ÉXITO. Sesión de Caja registrada con ID: {nueva_sesion.id}")
    except Exception as e:
        print(f"   -> ERROR de BD al registrar la sesión: {e}")
        db.rollback()
        raise

    movimiento_apertura = CajaMovimiento(
        tipo="APERTURA",
        concepto="Saldo inicial de caja",
        monto=saldo_inicial,
        metodo_pago="N/A",
        id_caja_sesion=nueva_sesion.id,
        id_usuario=usuario_apertura.id
    )

    try:
        db.add(movimiento_apertura)
        print(f"3. Intentando registrar el movimiento de APERTURA para la sesión {nueva_sesion.id}...")
        db.commit()
        db.refresh(movimiento_apertura)
        print(f"   -> ÉXITO. Movimiento registrado con ID: {movimiento_apertura.id}")
    except Exception as e:
        print(f"   -> ERROR de BD al registrar el movimiento: {e}")
        db.rollback()
        raise
    
    print("--- [FIN TRACE: ABRIR CAJA] ---\n")
    return nueva_sesion

def cerrar_caja(db: Session, usuario_cierre: Usuario, saldo_final_declarado: float) -> CajaSesion:
    """Cierra la sesión de caja abierta del usuario que realiza la acción usando ORM."""
    print("\n--- [TRACE: CERRAR CAJA] ---")
    print(f"1. Solicitud de cierre para usuario: '{usuario_cierre.nombre_usuario}', Saldo Declarado: {saldo_final_declarado}")

    sesion_a_cerrar = obtener_caja_abierta_por_usuario(db, usuario_cierre)
    if not sesion_a_cerrar:
        raise ValueError(f"El usuario '{usuario_cierre.nombre_usuario}' no tiene ninguna caja abierta para cerrar.")
    
    print(f"2. Sesión Abierta encontrada. ID: {sesion_a_cerrar.id}, Saldo Inicial: {sesion_a_cerrar.saldo_inicial}")

    # Lógica de cálculo corregida para sumar/restar según el tipo de movimiento
    suma_condicional = func.sum(
        case(
            (CajaMovimiento.tipo.in_(["EGRESO"]), -CajaMovimiento.monto),
            else_=CajaMovimiento.monto
        )
    )
    consulta_movimientos = (
        select(suma_condicional)
        .where(CajaMovimiento.id_caja_sesion == sesion_a_cerrar.id)
        .where(CajaMovimiento.tipo.not_in(["APERTURA"]))
    )
    suma_movimientos = db.exec(consulta_movimientos).first() or 0.0
    print(f"3. Suma NETA de movimientos (Ingresos - Egresos): {suma_movimientos}")

    saldo_final_calculado = sesion_a_cerrar.saldo_inicial + suma_movimientos
    diferencia = saldo_final_declarado - saldo_final_calculado
    print(f"4. Saldo Final CALCULADO: {saldo_final_calculado} | Diferencia: {diferencia}")

    sesion_a_cerrar.estado = "CERRADA"
    sesion_a_cerrar.fecha_cierre = datetime.utcnow()
    sesion_a_cerrar.id_usuario_cierre = usuario_cierre.id
    sesion_a_cerrar.saldo_final_declarado = saldo_final_declarado
    sesion_a_cerrar.saldo_final_calculado = round(saldo_final_calculado, 2)
    sesion_a_cerrar.diferencia = round(diferencia, 2)
    
    try:
        db.add(sesion_a_cerrar)
        print(f"5. Intentando actualizar Sesión ID {sesion_a_cerrar.id} a estado 'CERRADA'...")
        db.commit()
        db.refresh(sesion_a_cerrar)
        print(f"   -> ÉXITO. La sesión ha sido cerrada y registrada en la base de datos.")
    except Exception as e:
        print(f"   -> ERROR de BD al actualizar la sesión: {e}")
        db.rollback()
        raise

    print("--- [FIN TRACE: CERRAR CAJA] ---\n")
    return sesion_a_cerrar