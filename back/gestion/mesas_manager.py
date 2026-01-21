# back/gestion/mesas_manager.py
# Lógica de negocio para gestión de mesas y consumos

from sqlmodel import Session, select, update
from typing import List, Optional
from sqlalchemy.orm import selectinload
from datetime import datetime

# --- Modelos ---
from back.modelos import Mesa, ConsumoMesa, ConsumoMesaDetalle, Articulo, Usuario, StockMovimiento

# --- Schemas ---
from back.schemas.mesa_schemas import (
    MesaCreate, MesaUpdate, MesaRead,
    ConsumoMesaCreate, ConsumoMesaUpdate, ConsumoMesaRead,
    ConsumoMesaDetalleCreate, ConsumoMesaDetalleRead
)
from back.schemas.caja_schemas import ConsumoMesaFacturarRequest, ArticuloVendido
from back.gestion.caja.registro_caja import registrar_venta_y_movimiento_caja
from back.gestion.caja.apertura_cierre import obtener_caja_abierta_por_usuario
from back.gestion.ordenes_manager import registrar_orden_por_consumo, actualizar_orden_con_venta
from back.modelos import AuditLog

# ===================================================================
# === FUNCIONES PARA MESAS
# ===================================================================

def obtener_mesas_por_empresa(db: Session, id_empresa: int) -> List[Mesa]:
    """Obtiene todas las mesas activas de una empresa."""
    statement = select(Mesa).where(Mesa.id_empresa == id_empresa, Mesa.activo == True)
    return db.exec(statement).all()

def obtener_mesa_por_id(db: Session, id_mesa: int, id_empresa: int) -> Optional[Mesa]:
    """Obtiene una mesa específica por ID, verificando empresa."""
    statement = select(Mesa).where(Mesa.id == id_mesa, Mesa.id_empresa == id_empresa)
    return db.exec(statement).first()

def crear_mesa(db: Session, mesa_data: MesaCreate, id_empresa: int) -> Mesa:
    """Crea una nueva mesa."""
    mesa = Mesa(**mesa_data.model_dump(), id_empresa=id_empresa)
    db.add(mesa)
    db.commit()
    db.refresh(mesa)
    return mesa

def actualizar_mesa(db: Session, id_mesa: int, id_empresa: int, mesa_data: MesaUpdate) -> Optional[Mesa]:
    """Actualiza una mesa existente."""
    mesa = obtener_mesa_por_id(db, id_mesa, id_empresa)
    if not mesa:
        return None

    update_data = mesa_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(mesa, key, value)

    db.commit()
    db.refresh(mesa)
    return mesa

def eliminar_mesa(db: Session, id_mesa: int, id_empresa: int) -> bool:
    """Desactiva una mesa (soft delete)."""
    mesa = obtener_mesa_por_id(db, id_mesa, id_empresa)
    if not mesa:
        return False

    mesa.activo = False
    db.commit()
    return True

# ===================================================================
# === FUNCIONES PARA CONSUMOS EN MESAS
# ===================================================================

def obtener_consumos_abiertos_por_mesa(db: Session, id_mesa: int, id_empresa: int) -> List[ConsumoMesa]:
    """Obtiene consumos abiertos o cerrados (no facturados) de una mesa."""
    statement = select(ConsumoMesa).where(
        ConsumoMesa.id_mesa == id_mesa,
        ConsumoMesa.id_empresa == id_empresa,
        ConsumoMesa.estado.in_(["ABIERTO", "CERRADO"])
    ).options(selectinload(ConsumoMesa.detalles).selectinload(ConsumoMesaDetalle.articulo))
    return db.exec(statement).all()

def obtener_consumo_por_id(db: Session, id_consumo: int, id_empresa: int) -> Optional[ConsumoMesa]:
    """Obtiene un consumo específico con detalles."""
    statement = select(ConsumoMesa).where(
        ConsumoMesa.id == id_consumo,
        ConsumoMesa.id_empresa == id_empresa
    ).options(
        selectinload(ConsumoMesa.detalles).selectinload(ConsumoMesaDetalle.articulo),
        selectinload(ConsumoMesa.usuario)
    )
    return db.exec(statement).first()

def crear_consumo_mesa(db: Session, consumo_data: ConsumoMesaCreate, id_usuario: int, id_empresa: int) -> ConsumoMesa:
    """Crea un nuevo consumo en mesa."""
    consumo = ConsumoMesa(
        **consumo_data.model_dump(),
        id_usuario=id_usuario,
        id_empresa=id_empresa
    )
    db.add(consumo)
    db.commit()
    db.refresh(consumo)
    return consumo

def agregar_detalle_consumo(db: Session, id_consumo: int, detalle_data: ConsumoMesaDetalleCreate, id_empresa: int) -> Optional[ConsumoMesaDetalle]:
    """Agrega un detalle a un consumo."""
    consumo = obtener_consumo_por_id(db, id_consumo, id_empresa)
    if not consumo or consumo.estado != "ABIERTO":
        return None

    # Verificar stock disponible
    articulo = db.get(Articulo, detalle_data.id_articulo)
    if not articulo or articulo.stock_actual < detalle_data.cantidad:
        return None  # Stock insuficiente

    detalle = ConsumoMesaDetalle(**detalle_data.model_dump(), id_consumo_mesa=id_consumo)
    db.add(detalle)
    db.commit()  # Commit para obtener el ID del detalle
    db.refresh(detalle)

    # Crear movimiento de stock
    movimiento = crear_movimiento_stock_consumo(db, detalle, consumo.id_usuario, id_empresa)
    detalle.movimiento_stock = movimiento

    # Recalcular total
    subtotal = detalle.cantidad * (detalle.precio_unitario - detalle.descuento_aplicado)
    consumo.total += subtotal
    db.commit()
    db.refresh(detalle)
    return detalle

def obtener_comandas_pendientes(db: Session, id_empresa: int) -> List[ConsumoMesaDetalle]:
    """Obtiene los detalles de consumo (comandas) que no han sido impresos."""
    statement = select(ConsumoMesaDetalle).join(ConsumoMesa).where(
        ConsumoMesa.id_empresa == id_empresa,
        ConsumoMesa.estado == "ABIERTO",
        ConsumoMesaDetalle.impreso == False
    ).options(
        selectinload(ConsumoMesaDetalle.articulo).selectinload(Articulo.categoria),
        selectinload(ConsumoMesaDetalle.consumo).selectinload(ConsumoMesa.mesa)
    )
    return db.exec(statement).all()

def marcar_comanda_como_impresa(db: Session, ids_detalle: List[int], id_empresa: Optional[int] = None) -> int:
    statement = select(ConsumoMesaDetalle).join(ConsumoMesa).where(
        ConsumoMesaDetalle.id.in_(ids_detalle)
    )
    if id_empresa is not None:
        statement = statement.where(ConsumoMesa.id_empresa == id_empresa)
    detalles = db.exec(statement).all()
    count = 0
    for detalle in detalles:
        detalle.impreso = True
        count += 1
    if count > 0 and id_empresa is not None:
        db.add(AuditLog(
            accion="MARCAR_IMPRESO",
            entidad="ConsumoMesaDetalle",
            entidad_id=detalles[0].id if detalles else None,
            exito=True,
            detalles={"ids_detalle": ids_detalle, "marcados": count},
            id_usuario=0,
            id_empresa=id_empresa
        ))
    db.commit()
    return count

def cerrar_consumo_mesa(db: Session, id_consumo: int, id_empresa: int, porcentaje_propina: float = 0.0) -> Optional[ConsumoMesa]:
    """Cierra un consumo (prepara para facturación)."""
    consumo = obtener_consumo_por_id(db, id_consumo, id_empresa)
    if not consumo or consumo.estado != "ABIERTO":
        return None

    # Calcular propina
    propina_monto = (consumo.total * porcentaje_propina) / 100.0

    consumo.estado = "CERRADO"
    consumo.timestamp_cierre = datetime.utcnow()
    consumo.porcentaje_propina = porcentaje_propina
    consumo.propina = propina_monto
    
    db.commit()
    db.refresh(consumo)
    return registrar_orden_por_consumo(db, consumo, usuario_actual) or consumo

def facturar_consumo_mesa(
    db: Session, 
    id_consumo: int, 
    id_empresa: int, 
    usuario_actual: Usuario,
    facturar_data: ConsumoMesaFacturarRequest
) -> Optional[ConsumoMesa]:
    """Marca un consumo como facturado y registra la venta en caja."""
    consumo = obtener_consumo_por_id(db, id_consumo, id_empresa)
    if not consumo or consumo.estado != "CERRADO":
        return None

    # 1. Verificar sesión de caja abierta
    sesion_caja = obtener_caja_abierta_por_usuario(db, usuario_actual)
    if not sesion_caja:
        raise ValueError("No tienes una caja abierta. Debes abrir caja para facturar.")

    # 2. Preparar datos para registro de venta
    articulos_vendidos = []
    for detalle in consumo.detalles:
        articulos_vendidos.append(ArticuloVendido(
            id_articulo=detalle.id_articulo,
            cantidad=detalle.cantidad,
            precio_unitario=detalle.precio_unitario
        ))

    propina_a_cobrar = consumo.propina if facturar_data.cobrar_propina else 0.0

    # 3. Registrar venta y movimiento (OMITIENDO STOCK porque ya se descontó al agregar)
    registrar_venta_y_movimiento_caja(
        db=db,
        usuario_actual=usuario_actual,
        id_sesion_caja=sesion_caja.id,
        total_venta=consumo.total,
        metodo_pago=facturar_data.metodo_pago,
        articulos_vendidos=articulos_vendidos,
        id_cliente=None, # Por ahora sin cliente específico en mesa
        tipo_comprobante_solicitado="Ticket", # O configurable
        omitir_stock=True,
        propina=propina_a_cobrar,
    )

    # 4. Actualizar estado del consumo

    consumo.estado = "FACTURADO"
    db.commit()
    db.refresh(consumo)
    actualizar_orden_con_venta(db, consumo, consumo.ventas[0] if hasattr(consumo, "ventas") and consumo.ventas else None, usuario_actual)
    return consumo

# ===================================================================
# === FUNCIONES PARA IMPRESIÓN DE TICKETS
# ===================================================================

def generar_ticket_consumo(db: Session, id_consumo: int, id_empresa: int, formato: str = "ticket") -> Optional[dict]:
    """Genera datos para imprimir ticket de consumo."""
    consumo = obtener_consumo_por_id(db, id_consumo, id_empresa)
    if not consumo:
        return None

    # Aquí iría la lógica para generar el HTML/texto del ticket
    # Por ahora, devolver datos básicos
    ticket_data = {
        "mesa_numero": consumo.mesa.numero,
        "mozo": consumo.usuario.nombre_usuario if consumo.usuario else "Desconocido",
        "timestamp": consumo.timestamp_inicio.isoformat(),
        "detalles": [
            {
                "articulo": detalle.articulo.descripcion,
                "cantidad": detalle.cantidad,
                "precio_unitario": detalle.precio_unitario,
                "subtotal": detalle.cantidad * detalle.precio_unitario,
                "categoria": (detalle.articulo.categoria.nombre if detalle.articulo and detalle.articulo.categoria else None),
                "observacion": detalle.observacion,
            } for detalle in consumo.detalles
        ],
        "total": consumo.total,
        "propina": consumo.propina,
        "porcentaje_propina": consumo.porcentaje_propina,
        "total_con_propina": consumo.total + consumo.propina,
    }

    return ticket_data

# ===================================================================
# === FUNCIONES PARA MOVIMIENTOS DE STOCK
# ===================================================================

def crear_movimiento_stock_consumo(db: Session, detalle: ConsumoMesaDetalle, id_usuario: int, id_empresa: int) -> StockMovimiento:
    """Crea un movimiento de stock para un detalle de consumo de mesa."""
    # Obtener el stock actual del artículo
    articulo = detalle.articulo
    stock_anterior = articulo.stock_actual
    
    # Calcular nuevo stock (restar la cantidad consumida)
    nuevo_stock = stock_anterior - detalle.cantidad
    
    # Crear movimiento de stock
    movimiento = StockMovimiento(
        tipo="VENTA_CONSUMO_MESA",  # Tipo específico para consumos en mesa
        cantidad=-detalle.cantidad,  # Negativo porque es salida
        stock_anterior=stock_anterior,
        stock_nuevo=nuevo_stock,
        id_articulo=detalle.id_articulo,
        id_usuario=id_usuario,
        id_consumo_mesa_detalle=detalle.id,
        id_empresa=id_empresa
    )
    
    db.add(movimiento)
    
    # Actualizar stock del artículo
    articulo.stock_actual = nuevo_stock
    db.commit()
    db.refresh(movimiento)
    
    return movimiento

def unir_mesas(db: Session, id_empresa: int, source_mesa_ids: List[int], target_mesa_id: int) -> int:
    target = select(Mesa).where(Mesa.id == target_mesa_id, Mesa.id_empresa == id_empresa)
    target_mesa = db.exec(target).first()
    if not target_mesa or not target_mesa.activo:
        raise ValueError("Mesa destino inválida o inactiva")
    total_movidos = 0
    for mid in source_mesa_ids:
        if mid == target_mesa_id:
            continue
        src_stmt = select(Mesa).where(Mesa.id == mid, Mesa.id_empresa == id_empresa)
        src_mesa = db.exec(src_stmt).first()
        if not src_mesa or not src_mesa.activo:
            continue
        cons_stmt = select(ConsumoMesa).where(
            ConsumoMesa.id_mesa == mid,
            ConsumoMesa.id_empresa == id_empresa,
            ConsumoMesa.estado.in_(["ABIERTO", "CERRADO"])
        )
        consumos = db.exec(cons_stmt).all()
        for consumo in consumos:
            consumo.id_mesa = target_mesa_id
            total_movidos += 1
    if total_movidos > 0:
        target_mesa.estado = "OCUPADA"
        db.commit()
    db.add(AuditLog(
        accion="UNIR_MESAS",
        entidad="Mesa",
        entidad_id=target_mesa_id,
        exito=True,
        detalles={"source_mesa_ids": source_mesa_ids, "movidos": total_movidos},
        id_usuario=0,
        id_empresa=id_empresa
    ))
    db.commit()
    return total_movidos
