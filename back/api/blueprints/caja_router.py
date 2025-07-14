# back/api/blueprints/caja_router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List

from back.database import get_db
from back.security import obtener_usuario_actual
from back.modelos import Usuario
from back.gestion.caja import apertura_cierre, registro_caja, consultas_caja, movimientos_simples
from back.schemas.caja_schemas import (
    AbrirCajaRequest, CerrarCajaRequest, EstadoCajaResponse,
    RegistrarVentaRequest, ArqueoCajaResponse, RespuestaGenerica,
    MovimientoSimpleRequest
)

router = APIRouter(prefix="/caja", tags=["Caja"], dependencies=[Depends(obtener_usuario_actual)])

@router.get("/estado", response_model=EstadoCajaResponse)
def get_estado_caja_propia(db: Session = Depends(get_db), current_user: Usuario = Depends(obtener_usuario_actual)):
    sesion_abierta = apertura_cierre.obtener_caja_abierta_por_usuario(db, id_usuario=current_user.id)
    if sesion_abierta:
        return EstadoCajaResponse(caja_abierta=True, id_sesion=sesion_abierta.id, fecha_apertura=sesion_abierta.fecha_apertura)
    return EstadoCajaResponse(caja_abierta=False)

@router.post("/abrir", response_model=RespuestaGenerica)
def api_abrir_caja(req: AbrirCajaRequest, db: Session = Depends(get_db), current_user: Usuario = Depends(obtener_usuario_actual)):
    try:
        nueva_sesion = apertura_cierre.abrir_caja(db=db, saldo_inicial=req.saldo_inicial, id_usuario_apertura=current_user.id)
        return RespuestaGenerica(status="success", message=f"Caja abierta. ID Sesión: {nueva_sesion.id}", data={"id_sesion": nueva_sesion.id})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/cerrar", response_model=RespuestaGenerica)
def api_cerrar_caja(req: CerrarCajaRequest, db: Session = Depends(get_db), current_user: Usuario = Depends(obtener_usuario_actual)):
    try:
        resultado = apertura_cierre.cerrar_caja(db=db, id_usuario_cierre=current_user.id, saldo_final_declarado=req.saldo_final_declarado)
        return RespuestaGenerica(status=resultado["status"], message=resultado["message"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/ventas/registrar", response_model=RespuestaGenerica)
def api_registrar_venta(req: RegistrarVentaRequest, db: Session = Depends(get_db), current_user: Usuario = Depends(obtener_usuario_actual)):
    sesion_activa = apertura_cierre.obtener_caja_abierta_por_usuario(db, id_usuario=current_user.id)
    if not sesion_activa:
        raise HTTPException(status_code=400, detail="Operación denegada: El usuario no tiene una caja abierta.")
    try:
        resultado = registro_caja.registrar_venta_sql(
            db=db, id_sesion_caja=sesion_activa.id, articulos_vendidos=[art.model_dump() for art in req.articulos_vendidos],
            id_cliente=req.id_cliente, id_usuario=current_user.id, metodo_pago=req.metodo_pago.upper(), total_venta=req.total_venta
        )
        return RespuestaGenerica(status=resultado["status"], message=resultado["message"], data=resultado)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/ingresos", response_model=RespuestaGenerica)
def api_registrar_ingreso(req: MovimientoSimpleRequest, db: Session = Depends(get_db), current_user: Usuario = Depends(obtener_usuario_actual)):
    sesion_activa = apertura_cierre.obtener_caja_abierta_por_usuario(db, id_usuario=current_user.id)
    if not sesion_activa:
        raise HTTPException(status_code=400, detail="Operación denegada: El usuario no tiene una caja abierta.")
    try:
        mov = movimientos_simples.registrar_movimiento_simple(db, sesion_activa.id, current_user.id, "INGRESO", req.concepto, req.monto)
        return RespuestaGenerica(status="success", message="Ingreso registrado.", data={"id_movimiento": mov.id})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/egresos", response_model=RespuestaGenerica)
def api_registrar_egreso(req: MovimientoSimpleRequest, db: Session = Depends(get_db), current_user: Usuario = Depends(obtener_usuario_actual)):
    sesion_activa = apertura_cierre.obtener_caja_abierta_por_usuario(db, id_usuario=current_user.id)
    if not sesion_activa:
        raise HTTPException(status_code=400, detail="Operación denegada: El usuario no tiene una caja abierta.")
    try:
        monto = -abs(req.monto) # Los egresos son negativos
        mov = movimientos_simples.registrar_movimiento_simple(db, sesion_activa.id, current_user.id, "EGRESO", req.concepto, monto)
        return RespuestaGenerica(status="success", message="Egreso registrado.", data={"id_movimiento": mov.id})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/arqueos", response_model=List[ArqueoCajaResponse], tags=["Caja - Supervisión"])
def get_lista_de_arqueos(db: Session = Depends(get_db)):
    # NOTA: Proteger con una dependencia de seguridad más estricta (ej: rol 'admin').
    return consultas_caja.obtener_arqueos_de_caja(db=db)