# back/api/blueprints/mesas_router.py
# Endpoints para gestión de mesas y consumos

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlmodel import Session
from typing import List

# --- Dependencias ---
from back.database import get_db
from back.security import obtener_usuario_actual
from back.modelos import Usuario, Articulo

# --- Manager ---
import back.gestion.mesas_manager as mesas_manager

# --- Schemas ---
from back.schemas.mesa_schemas import (
    MesaCreate, MesaUpdate, MesaRead,
    ConsumoMesaCreate, ConsumoMesaUpdate, ConsumoMesaRead,
    ConsumoMesaDetalleCreate, TicketMesaRequest, TicketResponse,
    ConsumoMesaCierreRequest, ConsumoMesaFacturarRequest,
    ConsumoMesaDetallePopulated, MarcarImpresoRequest, UnirMesasRequest
)
from back.schemas.caja_schemas import RespuestaGenerica

router = APIRouter(
    prefix="/mesas",
    tags=["Mesas y Consumos"]
)

# ===================================================================
# === ENDPOINTS PARA MESAS
# ===================================================================

@router.get("/obtener_todas", response_model=List[MesaRead])
def api_get_mesas(
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    """Obtiene todas las mesas activas de la empresa."""
    mesas = mesas_manager.obtener_mesas_por_empresa(db, current_user.id_empresa)
    return mesas

@router.get("/obtener/{mesa_id}", response_model=MesaRead)
def api_get_mesa(
    mesa_id: int,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    """Obtiene una mesa específica."""
    mesa = mesas_manager.obtener_mesa_por_id(db, mesa_id, current_user.id_empresa)
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")
    return mesa

@router.post("/crear", response_model=MesaRead)
def api_create_mesa(
    mesa_data: MesaCreate,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    """Crea una nueva mesa."""
    try:
        mesa = mesas_manager.crear_mesa(db, mesa_data, current_user.id_empresa)
        return mesa
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al crear mesa: {str(e)}")

@router.put("/actualizar/{mesa_id}", response_model=MesaRead)
def api_update_mesa(
    mesa_id: int,
    mesa_data: MesaUpdate,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    """Actualiza una mesa existente."""
    mesa = mesas_manager.actualizar_mesa(db, mesa_id, current_user.id_empresa, mesa_data)
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")
    return mesa

@router.delete("/eliminar/{mesa_id}", response_model=RespuestaGenerica)
def api_delete_mesa(
    mesa_id: int,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    """Desactiva una mesa."""
    success = mesas_manager.eliminar_mesa(db, mesa_id, current_user.id_empresa)
    if not success:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")
    return RespuestaGenerica(mensaje="Mesa eliminada exitosamente")

# ===================================================================
# === ENDPOINTS PARA CONSUMOS EN MESAS
# ===================================================================

@router.get("/{mesa_id}/consumos_abiertos", response_model=List[ConsumoMesaRead])
def api_get_consumos_abiertos(
    mesa_id: int,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    """Obtiene consumos abiertos de una mesa."""
    consumos = mesas_manager.obtener_consumos_abiertos_por_mesa(db, mesa_id, current_user.id_empresa)
    return consumos

@router.post("/consumo/crear", response_model=ConsumoMesaRead)
def api_create_consumo(
    consumo_data: ConsumoMesaCreate,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    """Crea un nuevo consumo en mesa."""
    try:
        consumo = mesas_manager.crear_consumo_mesa(db, consumo_data, current_user.id, current_user.id_empresa)
        return consumo
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al crear consumo: {str(e)}")

@router.post("/consumo/{consumo_id}/agregar_detalle")
def api_add_detalle_consumo(
    consumo_id: int,
    detalle_data: ConsumoMesaDetalleCreate,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    """Agrega un detalle a un consumo."""
    try:
        detalle = mesas_manager.agregar_detalle_consumo(db, consumo_id, detalle_data, current_user.id_empresa)
        return {"mensaje": "Detalle agregado exitosamente", "detalle": detalle}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.put("/consumo/{consumo_id}/cerrar", response_model=ConsumoMesaRead)
def api_cerrar_consumo(
    consumo_id: int,
    cierre_data: ConsumoMesaCierreRequest = None,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    """Cierra un consumo para facturación."""
    porcentaje = cierre_data.porcentaje_propina if cierre_data else 0.0
    consumo = mesas_manager.cerrar_consumo_mesa(db, consumo_id, current_user.id_empresa, porcentaje)
    if not consumo:
        raise HTTPException(status_code=400, detail="No se pudo cerrar el consumo")
    return consumo

@router.put("/consumo/{consumo_id}/facturar", response_model=ConsumoMesaRead)
def api_facturar_consumo(
    consumo_id: int,
    facturar_data: ConsumoMesaFacturarRequest,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    """Marca un consumo como facturado."""
    consumo = mesas_manager.facturar_consumo_mesa(
        db, 
        consumo_id, 
        current_user.id_empresa, 
        current_user, 
        facturar_data
    )
    if not consumo:
        raise HTTPException(status_code=400, detail="No se pudo facturar el consumo")
    return consumo

# ===================================================================
# === ENDPOINTS PARA IMPRESIÓN DE TICKETS
# ===================================================================

@router.post("/ticket/generar", response_model=dict)
def api_generar_ticket(
    ticket_request: TicketMesaRequest,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    """Genera datos para imprimir ticket de consumo."""
    ticket_data = mesas_manager.generar_ticket_consumo(
        db, ticket_request.id_consumo_mesa, current_user.id_empresa, ticket_request.formato
    )
    if not ticket_data:
        raise HTTPException(status_code=404, detail="Consumo no encontrado")
    return ticket_data

# ===================================================================
# === ENDPOINTS PARA GESTIÓN DE COMANDAS (IMPRESIÓN CENTRALIZADA)
# ===================================================================

@router.get("/comandas/pendientes", response_model=List[ConsumoMesaDetallePopulated])
def api_get_comandas_pendientes(
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    """Obtiene detalles pendientes de impresión (Comandas)."""
    return mesas_manager.obtener_comandas_pendientes(db, current_user.id_empresa)

@router.post("/comandas/marcar_impreso", response_model=RespuestaGenerica)
def api_marcar_comandas_impresas(
    request: MarcarImpresoRequest,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    try:
        count = mesas_manager.marcar_comandas_impresas_con_sesion(db, current_user.id_empresa, request.ids_detalles)
        return RespuestaGenerica(mensaje=f"Detalles marcados como impresos: {count}")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al marcar impresos: {str(e)}")

@router.post("/unir", response_model=RespuestaGenerica)
def api_unir_mesas(
    request: "UnirMesasRequest",
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    try:
        moved = mesas_manager.unir_mesas(db, current_user.id_empresa, request.source_mesa_ids, request.target_mesa_id)
        if moved == 0:
            raise HTTPException(status_code=404, detail="No hay consumos para unir")
        return RespuestaGenerica(mensaje=f"Mesas unidas, consumos movidos: {moved}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al unir mesas: {str(e)}")
