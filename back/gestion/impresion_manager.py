from typing import Optional
from sqlmodel import Session, select
from datetime import datetime
from back.modelos import ImpresionSesion, Usuario

def obtener_sesion_abierta(db: Session, id_empresa: int) -> Optional[ImpresionSesion]:
    stmt = select(ImpresionSesion).where(ImpresionSesion.id_empresa == id_empresa, ImpresionSesion.estado == "ABIERTA")
    return db.exec(stmt).first()

def abrir_sesion_impresion(db: Session, usuario: Usuario) -> ImpresionSesion:
    sesion = obtener_sesion_abierta(db, usuario.id_empresa)
    if sesion:
        return sesion
    sesion = ImpresionSesion(
        id_usuario=usuario.id,
        id_empresa=usuario.id_empresa,
        estado="ABIERTA"
    )
    db.add(sesion)
    db.commit()
    db.refresh(sesion)
    return sesion

def cerrar_sesion_impresion(db: Session, usuario: Usuario) -> Optional[ImpresionSesion]:
    sesion = obtener_sesion_abierta(db, usuario.id_empresa)
    if not sesion:
        return None
    sesion.estado = "CERRADA"
    sesion.timestamp_cierre = datetime.utcnow()
    db.commit()
    db.refresh(sesion)
    return sesion
