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
    """Obtiene consumos abiertos de una mesa."""
    statement = select(ConsumoMesa).where(
        ConsumoMesa.id_mesa == id_mesa,
        ConsumoMesa.id_empresa == id_empresa,
        ConsumoMesa.estado == "ABIERTO"
    ).options(selectinload(ConsumoMesa.detalles).selectinload(ConsumoMesaDetalle.articulo))
    return db.exec(statement).all()

def obtener_consumo_por_id(db: Session, id_consumo: int, id_empresa: int) -> Optional[ConsumoMesa]:
    """Obtiene un consumo específico con detalles."""
    statement = select(ConsumoMesa).where(
        ConsumoMesa.id == id_consumo,
        ConsumoMesa.id_empresa == id_empresa
    ).options(selectinload(ConsumoMesa.detalles).selectinload(ConsumoMesaDetalle.articulo))
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

def cerrar_consumo_mesa(db: Session, id_consumo: int, id_empresa: int) -> Optional[ConsumoMesa]:
    """Cierra un consumo (prepara para facturación)."""
    consumo = obtener_consumo_por_id(db, id_consumo, id_empresa)
    if not consumo or consumo.estado != "ABIERTO":
        return None

    consumo.estado = "CERRADO"
    consumo.timestamp_cierre = datetime.utcnow()
    db.commit()
    db.refresh(consumo)
    return consumo

def facturar_consumo_mesa(db: Session, id_consumo: int, id_empresa: int) -> Optional[ConsumoMesa]:
    """Marca un consumo como facturado."""
    consumo = obtener_consumo_por_id(db, id_consumo, id_empresa)
    if not consumo or consumo.estado != "CERRADO":
        return None

    consumo.estado = "FACTURADO"
    db.commit()
    db.refresh(consumo)
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
        "timestamp": consumo.timestamp_inicio.isoformat(),
        "detalles": [
            {
                "articulo": detalle.articulo.descripcion,
                "cantidad": detalle.cantidad,
                "precio_unitario": detalle.precio_unitario,
                "subtotal": detalle.cantidad * detalle.precio_unitario,
                "categoria": (detalle.articulo.categoria.nombre if detalle.articulo and detalle.articulo.categoria else None),
            } for detalle in consumo.detalles
        ],
        "total": consumo.total,
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
