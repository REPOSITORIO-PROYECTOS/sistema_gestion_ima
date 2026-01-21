from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlmodel import Session
from typing import List, Optional
from back.database import get_db
from back.security import obtener_usuario_actual
from back.modelos import Usuario, AuditLog
from back.schemas.orden_schemas import OrdenRead, AuditLogRead, ReporteOrdenesRequest, ReporteOrdenesResponse
from back.gestion.ordenes_manager import obtener_ordenes, obtener_orden_por_id, generar_reporte_ordenes
from sqlmodel import select

router = APIRouter(prefix="/ordenes", tags=["Ordenes"])

@router.get("", response_model=List[OrdenRead])
def api_listar_ordenes(
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    return obtener_ordenes(db, current_user.id_empresa)

@router.get("/{orden_id}", response_model=OrdenRead)
def api_obtener_orden(
    orden_id: int,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    orden = obtener_orden_por_id(db, orden_id, current_user.id_empresa)
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return orden

@router.post("/reportes/generar", response_model=ReporteOrdenesResponse)
def api_generar_reporte(
    req: ReporteOrdenesRequest,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    data = generar_reporte_ordenes(db, current_user.id_empresa, req.desde, req.hasta, req.estado, req.tipo)
    return ReporteOrdenesResponse(**data)

@router.get("/auditoria", response_model=List[AuditLogRead])
def api_listar_auditoria(
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
    accion: Optional[str] = Query(default=None),
    entidad: Optional[str] = Query(default=None)
):
    stmt = select(AuditLog).where(AuditLog.id_empresa == current_user.id_empresa)
    if accion:
        stmt = stmt.where(AuditLog.accion == accion)
    if entidad:
        stmt = stmt.where(AuditLog.entidad == entidad)
    return db.exec(stmt).all()
