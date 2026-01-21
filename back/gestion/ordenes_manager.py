from typing import List, Optional, Dict
from datetime import datetime
from sqlmodel import Session, select
from back.modelos import Orden, AuditLog, ConsumoMesa, Venta, Usuario

def registrar_orden_por_consumo(db: Session, consumo: ConsumoMesa, usuario: Usuario) -> Orden:
    orden = Orden(
        tipo="MESA",
        estado="ABIERTA",
        total=consumo.total,
        id_consumo_mesa=consumo.id,
        id_usuario=usuario.id,
        id_empresa=usuario.id_empresa
    )
    db.add(orden)
    db.add(AuditLog(
        accion="CREAR_ORDEN",
        entidad="ConsumoMesa",
        entidad_id=consumo.id,
        exito=True,
        detalles={"total": consumo.total},
        id_usuario=usuario.id,
        id_empresa=usuario.id_empresa
    ))
    db.commit()
    db.refresh(orden)
    return orden

def actualizar_orden_con_venta(db: Session, consumo: ConsumoMesa, venta: Venta, usuario: Usuario) -> Optional[Orden]:
    stmt = select(Orden).where(Orden.id_consumo_mesa == consumo.id, Orden.id_empresa == usuario.id_empresa)
    orden = db.exec(stmt).first()
    if not orden:
        return None
    orden.estado = "FACTURADA"
    orden.id_venta = venta.id
    orden.numero_comprobante = str(venta.id)
    orden.total = venta.total
    db.add(AuditLog(
        accion="FACTURAR_ORDEN",
        entidad="Venta",
        entidad_id=venta.id,
        exito=True,
        detalles={"metodo_pago": getattr(venta, "tipo_comprobante_solicitado", None)},
        id_usuario=usuario.id,
        id_empresa=usuario.id_empresa
    ))
    db.commit()
    db.refresh(orden)
    return orden

def obtener_ordenes(db: Session, id_empresa: int) -> List[Orden]:
    stmt = select(Orden).where(Orden.id_empresa == id_empresa)
    return db.exec(stmt).all()

def obtener_orden_por_id(db: Session, id_orden: int, id_empresa: int) -> Optional[Orden]:
    stmt = select(Orden).where(Orden.id == id_orden, Orden.id_empresa == id_empresa)
    return db.exec(stmt).first()

def generar_reporte_ordenes(db: Session, id_empresa: int, desde: Optional[datetime], hasta: Optional[datetime], estado: Optional[str], tipo: Optional[str]) -> Dict:
    stmt = select(Orden).where(Orden.id_empresa == id_empresa)
    if desde:
        stmt = stmt.where(Orden.timestamp >= desde)
    if hasta:
        stmt = stmt.where(Orden.timestamp <= hasta)
    if estado:
        stmt = stmt.where(Orden.estado == estado)
    if tipo:
        stmt = stmt.where(Orden.tipo == tipo)
    ordenes = db.exec(stmt).all()
    total_ordenes = len(ordenes)
    total_monto = sum(o.total for o in ordenes)
    por_estado: Dict[str, int] = {}
    por_tipo: Dict[str, int] = {}
    for o in ordenes:
        por_estado[o.estado] = por_estado.get(o.estado, 0) + 1
        por_tipo[o.tipo] = por_tipo.get(o.tipo, 0) + 1
    return {
        "total_ordenes": total_ordenes,
        "total_monto": total_monto,
        "por_estado": por_estado,
        "por_tipo": por_tipo
    }
