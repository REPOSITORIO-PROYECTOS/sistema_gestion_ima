# /back/api/blueprints/proveedores_router.py

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List

# Dependencias y modelos
from back.database import get_db
from back.security import obtener_usuario_actual # Dependencia clave para multi-empresa
from back.modelos import Usuario
from back.schemas.caja_schemas import RespuestaGenerica

# Lógica de negocio (Managers)
from back.gestion.contabilidad.proveedores_contabilidad import proveedores_manager

# Schemas específicos
from back.schemas.proveedor_schemas import (
    ProveedorCreate, 
    ProveedorRead, 
    PlantillaMapeoCreate, 
    PlantillaMapeoRead,
    ArticuloProveedorLink
)

# Creamos el router con prefijo y tag para la documentación
router = APIRouter(prefix="/proveedores", tags=["Proveedores y Mapeos"])

@router.post("/crear", response_model=ProveedorRead, status_code=201)
def crear_proveedor(
    req: ProveedorCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    """Crea un nuevo proveedor asociado a la empresa del usuario autenticado."""
    # El manager se encarga de la lógica, el router solo pasa los datos correctos.
    nuevo_proveedor = proveedores_manager.crear_proveedor(db, req, current_user.id_empresa)
    return nuevo_proveedor

@router.get("/obtener-todos", response_model=List[ProveedorRead])
def listar_proveedores(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    """Obtiene la lista de todos los proveedores de la empresa del usuario."""
    proveedores = proveedores_manager.obtener_proveedores(db, current_user.id_empresa)
    return proveedores

@router.post("/plantilla", response_model=PlantillaMapeoRead)
def crear_o_actualizar_plantilla(
    req: PlantillaMapeoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    """
    Crea o actualiza la plantilla de mapeo de columnas de Excel para un proveedor.
    El proveedor debe pertenecer a la empresa del usuario.
    """
    # Primero, validamos que el proveedor pertenezca a la empresa del usuario.
    proveedor = db.get(proveedores_manager.Tercero, req.id_proveedor)
    if not proveedor or proveedor.id_empresa != current_user.id_empresa:
        raise HTTPException(status_code=404, detail="El proveedor especificado no pertenece a tu empresa.")
    
    plantilla = proveedores_manager.crear_o_actualizar_plantilla(db, req, current_user.id_empresa)
    return plantilla

@router.post("/{id_proveedor}/asociar-articulo", response_model=RespuestaGenerica)
def asociar_articulo_con_proveedor(
    id_proveedor: int,
    req: ArticuloProveedorLink,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    """
    Asocia un artículo de la empresa con un proveedor, guardando el código
    que ese proveedor usa para identificar el artículo.
    """
    try:
        proveedores_manager.asociar_articulo_a_proveedor(db, req, id_proveedor, current_user.id_empresa)
        return RespuestaGenerica(status="ok", message="Asociación creada/actualizada correctamente.")
    except HTTPException as e:
        # Re-lanza las excepciones HTTP que vienen del manager (ej: 404)
        raise e