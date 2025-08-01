# back/gestion/contabilidad/clientes_contabilidad/manager.py
# Lógica para el CRUD diario de clientes, operando 100% sobre SQL.

from sqlmodel import Session, select
from typing import List
from back.modelos import Tercero

def crear_cliente(id_empresa: int, db: Session, cliente_data: dict) -> Tercero:
    """Crea un nuevo cliente en la DB SQL, validando la unicidad del CUIT."""
    cuit = cliente_data.get('identificacion_fiscal')
    if cuit:
        cliente_existente = db.exec(
            select(Tercero).where(
                Tercero.identificacion_fiscal == cuit,
                Tercero.es_cliente == True
            )
        ).first()
        if cliente_existente:
            raise ValueError(f"Ya existe un cliente con el CUIT/CUIL {cuit}.")

    cliente_data['es_cliente'] = True
    cliente_data['id_empresa'] = id_empresa  # ← Aca lo agregás

    nuevo_cliente = Tercero.model_validate(cliente_data)
    db.add(nuevo_cliente)
    db.commit()
    db.refresh(nuevo_cliente)
    return nuevo_cliente


def obtener_cliente_por_id(id_empresa,db: Session, id_cliente: int) -> Tercero | None:
    return db.exec(select(Tercero).where(Tercero.id == id_cliente, Tercero.es_cliente == True, Tercero.id_empresa==id_empresa)).first()

def obtener_todos_los_clientes(id_empresa,db: Session, skip: int = 0, limit: int = 100) -> List[Tercero]:
    return db.exec(select(Tercero).where(Tercero.es_cliente == True, Tercero.id_empresa == id_empresa).order_by(Tercero.nombre_razon_social))
                   

def actualizar_cliente(id_empresa, db: Session, id_cliente: int, update_data: dict) -> Tercero:
    cliente_db = obtener_cliente_por_id(db, id_cliente)
    if not cliente_db:
        raise ValueError(f"Cliente con ID {id_cliente} no encontrado.")

    cuit_nuevo = update_data.get('identificacion_fiscal')
    if cuit_nuevo and cuit_nuevo != cliente_db.identificacion_fiscal:
        cliente_existente = db.exec(
            select(Tercero).where(Tercero.identificacion_fiscal == cuit_nuevo, Tercero.id != id_cliente, Tercero.id_empresa ==id_empresa)
        ).first()
        if cliente_existente:
            raise ValueError(f"El CUIT/CUIL '{cuit_nuevo}' ya pertenece a otro cliente.")
            
    for key, value in update_data.items():
        setattr(cliente_db, key, value)
        
    db.add(cliente_db)
    db.commit()
    db.refresh(cliente_db)
    return cliente_db


def desactivar_cliente(id_empresa, db: Session, id_cliente: int) -> Tercero:
    cliente_db = obtener_cliente_por_id(db, id_cliente)
    if not cliente_db:
        raise ValueError(f"Cliente con ID {id_cliente} no encontrado.")
    cliente_db.activo = False
    db.add(cliente_db)
    db.commit()
    db.refresh(cliente_db)
    return cliente_db