# back/api/blueprints/caja_router.py

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session
from typing import List, Dict, Any, Optional

# --- Módulos del Proyecto ---
from back.database import get_db
from back.security import es_cajero, obtener_usuario_actual
from back.modelos import Usuario, Tercero, Venta, CajaMovimiento

# Especialistas de la capa de gestión
from back.gestion.caja import apertura_cierre, registro_caja, consultas_caja
from back.gestion.facturacion_afip import generar_factura_para_venta

# Schemas necesarios para este router
from back.schemas.caja_schemas import (
    AbrirCajaRequest, CerrarCajaRequest, EstadoCajaResponse,
    RegistrarVentaRequest, InformeCajasResponse, RespuestaGenerica,
    MovimientoSimpleRequest, TipoMovimiento
)
from back.schemas.comprobante_schemas import TransaccionData, ReceptorData, ItemData

router = APIRouter(
    prefix="/caja",
    tags=["Caja"],
)

# =================================================================
# === ENDPOINTS DE GESTIÓN DE SESIÓN DE CAJA (SIN CAMBIOS) ===
# =================================================================

@router.get("/estado", response_model=EstadoCajaResponse)
def get_estado_caja_propia(db: Session = Depends(get_db), current_user: Usuario = Depends(obtener_usuario_actual)):
    sesion_abierta = apertura_cierre.obtener_caja_abierta_por_usuario(db, current_user)
    if sesion_abierta:
        return EstadoCajaResponse(caja_abierta=True, id_sesion=sesion_abierta.id, fecha_apertura=sesion_abierta.fecha_apertura)
    return EstadoCajaResponse(caja_abierta=False)

@router.post("/abrir", response_model=RespuestaGenerica, dependencies=[Depends(es_cajero)])
def api_abrir_caja(req: AbrirCajaRequest, db: Session = Depends(get_db), current_user: Usuario = Depends(obtener_usuario_actual)):
    try:
        sesion = apertura_cierre.abrir_caja(db=db, usuario_apertura=current_user, saldo_inicial=req.saldo_inicial)
        db.commit()
        return RespuestaGenerica(status="success", message=f"Caja abierta con éxito. Sesión ID: {sesion.id}", data={"id_sesion": sesion.id})
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))

@router.post("/cerrar", response_model=RespuestaGenerica)
def api_cerrar_caja(req: CerrarCajaRequest, db: Session = Depends(get_db), current_user: Usuario = Depends(obtener_usuario_actual)):
    try:
        sesion = apertura_cierre.cerrar_caja(db=db, usuario_cierre=current_user, saldo_final_declarado=req.saldo_final_declarado)
        db.commit()
        return RespuestaGenerica(status="success", message=f"Caja cerrada con éxito. Sesión ID: {sesion.id}", data={"id_sesion": sesion.id})
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))

# =================================================================
# === ENDPOINTS DE OPERACIONES REFACTORIZADOS ===
# =================================================================

@router.post("/ventas/registrar", response_model=RespuestaGenerica, tags=["Caja - Operaciones"])
def api_registrar_venta(
    req: RegistrarVentaRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    """
    Orquesta el proceso completo de registro de una venta: DB, AFIP y Sheets.
    Maneja descuentos y calcula el vuelto si es necesario.
    """
    sesion_activa = apertura_cierre.obtener_caja_abierta_por_usuario(db, current_user)
    if not sesion_activa:
        raise HTTPException(status_code=400, detail="Operación denegada: El usuario no tiene una caja abierta.")

    # --- Lógica de Vuelto y Descuentos ---
    vuelto = None
    if req.monto_recibido:
        try:
            vuelto = registro_caja.calcular_vuelto(req.total_venta, req.monto_recibido)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    # El `total_venta` que llega ya debería tener los descuentos aplicados por el frontend.
    # La lógica de negocio `registrar_venta` guarda este total final.

    # --- PASO 1: TRANSACCIÓN CRÍTICA CON LA BASE DE DATOS ---
    try:
        venta_creada, _ = registro_caja.registrar_venta_y_movimiento_caja(
            db=db,
            usuario_actual=current_user,
            id_sesion_caja=sesion_activa.id,
            total_venta=req.total_venta,
            metodo_pago=req.metodo_pago.upper(),
            articulos_vendidos=req.articulos_vendidos,
            id_cliente=req.id_cliente
        )
        db.commit()
        db.refresh(venta_creada)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Conflicto de negocio: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")

    # --- PASO 2: INTEGRACIÓN CON AFIP Y ACTUALIZACIÓN DE LA VENTA ---
    resultado_afip: Dict[str, Any] = {"estado": "NO_SOLICITADA"}
    if req.quiere_factura:
        try:
            cliente_db = db.get(Tercero, req.id_cliente) if req.id_cliente else None
            
            # Mapeamos los datos para el especialista de AFIP
            venta_data_schema = TransaccionData(total=venta_creada.total, items=[ItemData.model_validate(art) for art in req.articulos_vendidos])
            cliente_data_schema = ReceptorData.model_validate(cliente_db) if cliente_db else None

            factura_generada = generar_factura_para_venta(venta_data=venta_data_schema, cliente_data=cliente_data_schema)
            
            venta_creada.facturada = True
            venta_creada.datos_factura = factura_generada
            db.add(venta_creada)
            db.commit()
            
            resultado_afip = {"estado": "EXITOSO", **factura_generada}

        except (ValueError, RuntimeError) as e:
            resultado_afip = {"estado": "FALLIDO", "error": str(e)}

    # --- PASO 3: INTEGRACIÓN CON GOOGLE SHEETS (SEGUNDO PLANO) ---
    cliente_final = db.get(Tercero, req.id_cliente) if req.id_cliente else None
    background_tasks.add_task(
        registro_caja.sincronizar_venta_con_sheets,
        venta=venta_creada,
        cliente=cliente_final,
        resultado_afip=resultado_afip
    )

    # --- PASO 4: RESPUESTA FINAL AL CLIENTE ---
    return RespuestaGenerica(
        status="success",
        message="Venta registrada.",
        data={
            "id_venta": venta_creada.id,
            "vuelto": vuelto,
            "facturacion_afip": resultado_afip
        }
    )

@router.post("/ingresos", response_model=RespuestaGenerica, tags=["Caja - Operaciones"])
def api_registrar_ingreso(req: MovimientoSimpleRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: Usuario = Depends(obtener_usuario_actual)):
    sesion_activa = apertura_cierre.obtener_caja_abierta_por_usuario(db, current_user)
    if not sesion_activa:
        raise HTTPException(status_code=400, detail="Operación denegada: El usuario no tiene una caja abierta.")
    
    try:
        movimiento_creado = registro_caja.registrar_movimiento_simple(
            db=db, usuario_actual=current_user, id_sesion_caja=sesion_activa.id,
            monto=req.monto, concepto=req.concepto, tipo=TipoMovimiento.INGRESO,
            metodo_pago=req.metodo_pago if req.metodo_pago else "EFECTIVO"
        )
        db.commit()
        background_tasks.add_task(registro_caja.sincronizar_movimiento_simple_con_sheets, movimiento=movimiento_creado)
        return RespuestaGenerica(status="success", message=f"Ingreso registrado con éxito. ID: {movimiento_creado.id}", data={"id_movimiento": movimiento_creado.id})
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))

@router.post("/egresos", response_model=RespuestaGenerica, tags=["Caja - Operaciones"])
def api_registrar_egreso(req: MovimientoSimpleRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: Usuario = Depends(obtener_usuario_actual)):
    sesion_activa = apertura_cierre.obtener_caja_abierta_por_usuario(db, current_user)
    if not sesion_activa:
        raise HTTPException(status_code=400, detail="Operación denegada: El usuario no tiene una caja abierta.")
    
    try:
        movimiento_creado = registro_caja.registrar_movimiento_simple(
            db=db, usuario_actual=current_user, id_sesion_caja=sesion_activa.id,
            monto=req.monto, concepto=req.concepto, tipo=TipoMovimiento.EGRESO
        )
        db.commit()
        background_tasks.add_task(registro_caja.sincronizar_movimiento_simple_con_sheets, movimiento=movimiento_creado)
        return RespuestaGenerica(status="success", message=f"Egreso registrado con éxito. ID: {movimiento_creado.id}", data={"id_movimiento": movimiento_creado.id})
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))

# =================================================================
# === ENDPOINT DE SUPERVISIÓN (SIN CAMBIOS) ===
# =================================================================
@router.get("/arqueos", response_model=InformeCajasResponse, tags=["Caja - Supervisión"])
def get_lista_de_arqueos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual) # <-- Inyectamos el usuario actual
):
    """
    Obtiene un informe de cajas abiertas y cerradas para la empresa del usuario.
    """
    try:
        # Le pasamos el usuario completo a la función de lógica de negocio
        return consultas_caja.obtener_arqueos_de_caja(db=db, usuario_actual=current_user)
    except Exception as e:
        # Si la capa de negocio lanza un error, lo convertimos en un 500.
        raise HTTPException(status_code=500, detail="Ocurrió un error al generar el informe de arqueos.")