# back/api/blueprints/caja_router.py
# VERSIÓN FINAL, COMPLETA Y SINCRONIZADA

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List

# --- Módulos del proyecto ---
from back.database import get_db
from back.security import obtener_usuario_actual, es_cajero
from back.modelos import Usuario
# Importamos toda la lógica de negocio de la caja
from back.gestion.caja import apertura_cierre, registro_caja, consultas_caja
# Importamos los schemas corregidos
from back.schemas.caja_schemas import (
    AbrirCajaRequest, CerrarCajaRequest, EstadoCajaResponse,
    RegistrarVentaRequest, ArqueoCajaResponse, RespuestaGenerica,
    MovimientoSimpleRequest, CajaSesionResponse # <-- ¡Importamos el nuevo schema!
)

router = APIRouter(
    prefix="/caja",
    tags=["Caja"],
    #dependencies=[Depends(es_cajero)]
)

# =================================================================
# === ENDPOINTS DE GESTIÓN DE SESIÓN DE CAJA ===
# =================================================================

@router.get("/estado", response_model=EstadoCajaResponse)
def get_estado_caja_propia(db: Session = Depends(get_db), current_user: Usuario = Depends(obtener_usuario_actual)):
    """Verifica si el usuario autenticado tiene una caja abierta."""
    # CORRECCIÓN: Pasamos el objeto 'current_user' completo a la lógica de negocio.
    sesion_abierta = apertura_cierre.obtener_caja_abierta_por_usuario(db, current_user)
    if sesion_abierta:
        return EstadoCajaResponse(caja_abierta=True, id_sesion=sesion_abierta.id, fecha_apertura=sesion_abierta.fecha_apertura)
    return EstadoCajaResponse(caja_abierta=False)

@router.post("/abrir", response_model=CajaSesionResponse)
def api_abrir_caja(req: AbrirCajaRequest, db: Session = Depends(get_db), current_user: Usuario = Depends(obtener_usuario_actual)):
    """Abre una nueva sesión de caja para el usuario autenticado."""
    try:
        # CORRECCIÓN: Pasamos el 'current_user' y usamos el response_model correcto.
        return apertura_cierre.abrir_caja(db=db, usuario_apertura=current_user, saldo_inicial=req.saldo_inicial)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) # 409 Conflict

@router.post("/cerrar", response_model=CajaSesionResponse)
def api_cerrar_caja(req: CerrarCajaRequest, db: Session = Depends(get_db), current_user: Usuario = Depends(obtener_usuario_actual)):
    """Cierra la sesión de caja abierta del usuario autenticado."""
    try:
        # CORRECCIÓN: Pasamos 'current_user' y el response_model ahora coincide con lo que devuelve la función.
        # Esto soluciona el error 422.
        return apertura_cierre.cerrar_caja(db=db, usuario_cierre=current_user, saldo_final_declarado=req.saldo_final_declarado)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) # 404 Not Found

# =================================================================
# === ENDPOINTS DE OPERACIONES DENTRO DE LA CAJA ===
# =================================================================
# NOTA: Estos endpoints todavía usan lógica heredada. Se mantienen para no romper la funcionalidad.

@router.post("/ventas/registrar", response_model=RespuestaGenerica)
def api_registrar_venta(req: RegistrarVentaRequest, db: Session = Depends(get_db), current_user: Usuario = Depends(obtener_usuario_actual)):
    """Registra una nueva venta en la sesión de caja activa del usuario."""
    sesion_activa = apertura_cierre.obtener_caja_abierta_por_usuario(db, current_user)
    if not sesion_activa:
        raise HTTPException(status_code=400, detail="Operación denegada: El usuario no tiene una caja abierta.")
    try:
        resultado = registro_caja.registrar_venta_sql(
            db=db, id_sesion_caja=sesion_activa.id, articulos_vendidos=[art.model_dump() for art in req.articulos_vendidos],
            id_cliente=req.id_cliente, id_usuario=current_user.id, metodo_pago=req.metodo_pago.upper(), total_venta=req.total_venta
        )
        return RespuestaGenerica(status="success", message="Venta registrada con éxito", data=resultado)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/ingresos", response_model=RespuestaGenerica)
def api_registrar_ingreso(req: MovimientoSimpleRequest, db: Session = Depends(get_db), current_user: Usuario = Depends(obtener_usuario_actual)):
    """Registra un ingreso de efectivo en la caja."""
    sesion_activa = apertura_cierre.obtener_caja_abierta_por_usuario(db, current_user)
    if not sesion_activa:
        raise HTTPException(status_code=400, detail="Operación denegada: El usuario no tiene una caja abierta.")
    
    resultado = registro_caja.registrar_ingreso_egreso(
        id_sesion_caja=sesion_activa.id, concepto=req.concepto, monto=req.monto,
        tipo="INGRESO", usuario=current_user.nombre_usuario
    )
    if resultado.get("status") == "success":
        return RespuestaGenerica(status="success", message=resultado.get("message"), data={"id_movimiento": resultado.get("id_movimiento")})
    else:
        raise HTTPException(status_code=400, detail=resultado.get("message", "Error al registrar ingreso."))

@router.post("/egresos", response_model=RespuestaGenerica)
def api_registrar_egreso(req: MovimientoSimpleRequest, db: Session = Depends(get_db), current_user: Usuario = Depends(obtener_usuario_actual)):
    """Registra un egreso de efectivo de la caja."""
    sesion_activa = apertura_cierre.obtener_caja_abierta_por_usuario(db, current_user)
    if not sesion_activa:
        raise HTTPException(status_code=400, detail="Operación denegada: El usuario no tiene una caja abierta.")

    resultado = registro_caja.registrar_ingreso_egreso(
        id_sesion_caja=sesion_activa.id, concepto=req.concepto, monto=req.monto,
        tipo="EGRESO", usuario=current_user.nombre_usuario
    )
    if resultado.get("status") == "success":
        return RespuestaGenerica(status="success", message=resultado.get("message"), data={"id_movimiento": resultado.get("id_movimiento")})
    else:
        raise HTTPException(status_code=400, detail=resultado.get("message", "Error al registrar egreso."))

# =================================================================
# === ENDPOINT DE SUPERVISIÓN ===
# =================================================================

@router.get("/arqueos", response_model=List[ArqueoCajaResponse], tags=["Caja - Supervisión"])
def get_lista_de_arqueos(db: Session = Depends(get_db)):
    """Obtiene una lista de todos los cierres de caja (arqueos)."""
    return consultas_caja.obtener_arqueos_de_caja(db=db)