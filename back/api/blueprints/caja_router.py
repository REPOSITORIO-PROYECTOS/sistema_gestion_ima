# back/api/blueprints/caja_router.py

from sqlite3.dbapi2 import Timestamp
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from starlette.responses import Response

# --- Módulos del Proyecto ---
from back.database import get_db
from back.security import obtener_usuario_actual, es_admin, es_cajero
from back.modelos import ConfiguracionEmpresa, Empresa, Usuario, Tercero, Venta, CajaMovimiento

# Especialistas de la capa de gestión
from back.gestion.caja import apertura_cierre, registro_caja, consultas_caja
from back.gestion.facturacion_afip import generar_factura_para_venta
from back.gestion.reportes import generador_comprobantes

# Schemas necesarios para este router
from back.schemas.caja_schemas import (
    AbrirCajaRequest, CajaMovimientoResponse, CerrarCajaRequest, EstadoCajaResponse,
    RegistrarVentaRequest, InformeCajasResponse, RespuestaGenerica,
    MovimientoSimpleRequest, TipoMovimiento, MovimientoContableResponse
)
from back.schemas.comprobante_schemas import EmisorData, TransaccionData, ReceptorData, ItemData

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
        sesion = apertura_cierre.cerrar_caja(db=db, usuario_cierre=current_user, saldo_final_declarado=req.saldo_final_declarado,saldo_final_transferencias=req.saldo_final_transferencias,saldo_final_efectivo=req.saldo_final_efectivo,saldo_final_bancario = req.saldo_final_bancario)
        db.commit()
        return RespuestaGenerica(status="success", message=f"Caja cerrada con éxito. Sesión ID: {sesion.id}", data={"id_sesion": sesion.id})
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))

# =================================================================
# === ENDPOINTS DE OPERACIONES REFACTORIZADOS ===
# =================================================================

# back/routers/ventas_router.py (o donde esté tu endpoint)



@router.post("/ventas/registrar", response_model=RespuestaGenerica, tags=["Caja - Operaciones"])
def api_registrar_venta(
    req: RegistrarVentaRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    """
    Orquesta el proceso completo de registro de una venta: DB, AFIP.
    Maneja descuentos y calcula el vuelto si es necesario.
    """
    sesion_activa = apertura_cierre.obtener_caja_abierta_por_usuario(db, current_user)
    if not sesion_activa:
        raise HTTPException(status_code=400, detail="Operación denegada: El usuario no tiene una caja abierta.")

    # --- Lógica de Vuelto (sin cambios) ---
    vuelto = None
    if req.paga_con:
        try:
            vuelto = registro_caja.calcular_vuelto(req.total_venta, req.paga_con)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    # --- PASO 1: TRANSACCIÓN CRÍTICA CON LA BASE DE DATOS (sin cambios) ---
    try:
        venta_creada, _ = registro_caja.registrar_venta_y_movimiento_caja(
            db=db,
            usuario_actual=current_user,
            id_sesion_caja=sesion_activa.id,
            total_venta=req.total_venta,
            metodo_pago=req.metodo_pago.upper(),
            articulos_vendidos=req.articulos_vendidos,
            id_cliente=req.id_cliente,
            pago_separado=req.pago_separado,
            detalles_pago_separado=req.detalles_pago_separado,
            tipo_comprobante_solicitado = req.tipo_comprobante_solicitado
        )
        db.commit()
        db.refresh(venta_creada)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Conflicto de negocio: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error interno al registrar la venta.")

    # --- PASO 2: INTEGRACIÓN CON AFIP Y ACTUALIZACIÓN DE LA VENTA ---
    resultado_afip: Dict[str, Any] = {"estado": "NO_SOLICITADA"}
    if req.quiere_factura:
        try:
            # === INICIO DE LA LÓGICA DE FACTURACIÓN CORREGIDA ===
            print("entramos al try de requiere factura")
            id_empresa_actual = current_user.id_empresa
            if not id_empresa_actual:
                 raise RuntimeError("El usuario actual no tiene una empresa asignada.")

            # Consultar los datos del EMISOR
            empresa_db = db.get(Empresa, id_empresa_actual)
            statement = select(ConfiguracionEmpresa).where(ConfiguracionEmpresa.id_empresa == id_empresa_actual)
            config_empresa_db = db.exec(statement).first()

            if not empresa_db or not empresa_db.cuit:
                raise ValueError(f"No se encontraron datos de empresa o CUIT para la empresa ID: {id_empresa_actual}")
            if not config_empresa_db or not config_empresa_db.afip_punto_venta_predeterminado:
                raise ValueError(f"No se encontró un punto de venta predeterminado para la empresa ID: {id_empresa_actual}")
            
            # Consultar los datos del RECEPTOR
            cliente_db = db.get(Tercero, req.id_cliente) if req.id_cliente else None
            
            # Mapear datos a Schemas Pydantic (¡AHORA CON TODOS LOS CAMPOS!)
            venta_data_schema = TransaccionData.model_validate(venta_creada, from_attributes=True)
            
            # Usar model_validate para manejar el caso de que cliente_db sea None
            cliente_data_schema = ReceptorData.model_validate(cliente_db, from_attributes=True) if cliente_db else None
            print("veta data schema :")
            print(venta_data_schema)
            print("cliente data schema : ")
            print(cliente_data_schema)
            
            # Construir el schema del emisor con TODOS los datos recuperados
            emisor_data_schema = EmisorData(
                cuit=empresa_db.cuit,
                razon_social=empresa_db.nombre_legal,
                domicilio=config_empresa_db.direccion_negocio,
                punto_venta=config_empresa_db.afip_punto_venta_predeterminado,
                condicion_iva=config_empresa_db.afip_condicion_iva
            )
            print("ANTES DE LA FUNCION GENERAR FACTURA")
            # Llamar al especialista de facturación
            factura_generada = generar_factura_para_venta(
                venta_data=venta_data_schema, 
                cliente_data=cliente_data_schema,
                emisor_data=emisor_data_schema
            )
            print("DESPUES DE LA FUNCION GENERAR FACTURA")
            # === FIN DE LA LÓGICA DE FACTURACIÓN CORREGIDA ===
            
            venta_creada.facturada = True
            venta_creada.datos_factura = factura_generada
            db.add(venta_creada)
            db.commit()
            
            resultado_afip = {"estado": "EXITOSO", **factura_generada}

        except (ValueError, RuntimeError) as e:
            resultado_afip = {"estado": "FALLIDO", "error": str(e)}

    # --- RESPUESTA FINAL (sin cambios) ---
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
        movimiento_creado = registro_caja.registrar_ingreso_egreso(
            db=db, usuario_actual=current_user, id_sesion_caja=sesion_activa.id,
            monto=req.monto, concepto=req.concepto, tipo=TipoMovimiento.INGRESO,
            metodo_pago=req.metodo_pago if req.metodo_pago else "EFECTIVO"
        )
        db.commit()
        
        return RespuestaGenerica(status="success", message=f"Ingreso registrado con éxito. ID: {movimiento_creado.id}", data={"id_movimiento": movimiento_creado.id})
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/egresos", response_model=CajaMovimientoResponse)
def api_registrar_egreso(
    req: MovimientoSimpleRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    """Registra un egreso de efectivo de la caja."""
    sesion_activa = apertura_cierre.obtener_caja_abierta_por_usuario(db, current_user)
    if not sesion_activa:
        raise HTTPException(status_code=400, detail="Operación denegada: El usuario no tiene una caja abierta.")
    
    try:
        movimiento = registro_caja.registrar_ingreso_egreso(
            db=db,
            usuario_actual=current_user,
            id_sesion_caja=sesion_activa.id,
            concepto=req.concepto,
            monto=req.monto,
            tipo="EGRESO",
            id_usuario=current_user.id,  
            fecha_hora=datetime.now(timezone.utc),
            facturado=False
        )

        return CajaMovimientoResponse(
            id=movimiento.id,
            id_sesion_caja=movimiento.id_caja_sesion,  # ⚠️ Asegurate que este es el nombre correcto
            id_venta_asociada=movimiento.id_venta,
            id_usuario=movimiento.id_usuario,
            tipo=movimiento.tipo,
            concepto=movimiento.concepto,
            monto=movimiento.monto,
            metodo_pago=movimiento.metodo_pago,
            fecha_hora=datetime.now(timezone.utc),  # Si usás timestamp, mapearlo aquí
            facturado=False
        )

    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))



# =================================================================
# === ENDPOINT DE SUPERVISIÓN (SIN CAMBIOS) ===
# =================================================================
@router.get("/arqueos", response_model=InformeCajasResponse, tags=["Caja - Supervisión"])
def get_lista_de_arqueos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual),
      # <-- Inyectamos el usuario actual
):
    """
    Obtiene un informe de cajas abiertas y cerradas para la empresa del usuario.
    """
    try:
        id_empresa = current_user.id_empresa
        # Le pasamos el usuario completo a la función de lógica de negocio
        return consultas_caja.obtener_arqueos_de_caja(id_empresa,db=db, usuario_actual=current_user)
    except Exception as e:
        # Si la capa de negocio lanza un error, lo convertimos en un 500.
        raise HTTPException(status_code=500, detail="Ocurrió un error al generar el informe de arqueos.")
    

@router.get(
    "/movimientos/todos", # Una ruta clara
    summary="Obtiene el 'Libro Mayor' de todos los movimientos de caja de la empresa",
    response_model=List[MovimientoContableResponse],
    tags=["Caja - Supervisión"]
)
def get_todos_los_movimientos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    """
    Endpoint maestro para el tablero de contabilidad. Devuelve una lista completa
    de ingresos, egresos y ventas, con el estado de facturación incluido.
    """
    # Llamamos a nuestra nueva y potente función de consulta
    id_empresa = current_user.id_empresa
    movimientos = consultas_caja.obtener_todos_los_movimientos_de_caja(
        db=db,
        usuario_actual=current_user
    )
    return movimientos


@router.get(
    "/sesion/{id_sesion}/ticket-cierre-detallado",
    summary="Generar PDF del Cierre de Lote Detallado"
)
def api_generar_ticket_cierre_detallado(
    id_sesion: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    """
    Genera y devuelve en formato PDF un ticket de cierre de lote para una sesión
    de caja específica, incluyendo el desglose detallado de todos los
    ingresos y egresos.
    """

    try:
        # 1. LLAMA AL MANAGER PARA OBTENER LOS DATOS
        # Llama a la función que ya creamos en 'consultas_caja.py'.
        # Esta función hace todo el trabajo de base de datos y seguridad.
        datos_para_plantilla = consultas_caja.obtener_datos_para_ticket_cierre_detallado(
            db=db, 
            id_sesion=id_sesion, 
            usuario_actual=current_user
        )
        
        # 2. LLAMA AL GENERADOR DE PDFS
        # Le pasa los datos a una función en tu generador de comprobantes
        # que sabe cómo usar la plantilla HTML 'cierre_lote_detallado.html'.
        pdf_bytes = generador_comprobantes.generar_ticket_cierre_pdf(datos_para_plantilla)
        
        # 3. DEVUELVE EL ARCHIVO PDF
        # Crea una respuesta HTTP con el contenido del PDF y las cabeceras correctas.
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            # 'inline' le dice al navegador que intente abrir el PDF en una nueva pestaña.
            # 'attachment' le diría que lo descargue directamente.
            headers={"Content-Disposition": f'inline; filename="cierre_detallado_{id_sesion}.pdf"'}
        )
        
    except (ValueError, PermissionError) as e:
        # Captura errores de negocio (ej: sesión no encontrada, no pertenece a la empresa).
        # Devuelve 404 para no dar información sensible.
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        # Captura errores internos (ej: fallo al renderizar la plantilla).
        raise HTTPException(status_code=500, detail=f"Error interno al generar el ticket: {e}")
    
@router.get(
    "/estado-actual", 
    response_model=EstadoCajaResponse,
    summary="Verifica el estado de la caja del usuario actual"
)
def api_obtener_estado_caja(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    """
    Verifica si el usuario autenticado tiene una caja abierta y devuelve el estado.
    Este endpoint es clave para sincronizar el frontend al recargar la página.
    """
    # ASEGÚRATE DE QUE ESTA LÍNEA LLAME A LA FUNCIÓN CON EL NOMBRE CORRECTO
    estado = consultas_caja.obtener_estado_caja_actual_usuario(db, current_user)
    return estado

@router.post("/admin/cerrar-por-id/{id_sesion}", response_model=RespuestaGenerica)
def api_cerrar_caja_por_id(
    id_sesion: int,
    req: CerrarCajaRequest, # Reutilizamos el mismo schema
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(es_admin) # ¡Protegido para admins!
):
    """
    [Admin] Cierra una sesión de caja específica por su ID.
    """
    try:
        sesion = apertura_cierre.cerrar_caja_por_id(
            db=db, 
            id_sesion=id_sesion,
            usuario_admin=current_user,
            saldo_final_declarado=req.saldo_final_declarado,
            saldo_final_transferencias=req.saldo_final_transferencias,
            saldo_final_bancario=req.saldo_final_bancario,
            saldo_final_efectivo=req.saldo_final_efectivo
        )
        db.commit()
        return RespuestaGenerica(status="success", message=f"Caja (Sesión ID: {sesion.id}) cerrada por un administrador.", data={"id_sesion": sesion.id})
    except (ValueError, PermissionError) as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
