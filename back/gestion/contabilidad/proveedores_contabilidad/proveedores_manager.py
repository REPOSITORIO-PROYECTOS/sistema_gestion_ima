# /back/gestion/contabilidad/proveedores_manager.py

from sqlmodel import Session, select
from typing import List
from fastapi import HTTPException

# Asegúrate de que las rutas de importación sean correctas para tu estructura
from back.modelos import Tercero, PlantillaMapeoProveedor, ArticuloProveedor, Articulo
from back.schemas.proveedor_schemas import ProveedorCreate, PlantillaMapeoCreate, ArticuloProveedorLink

def crear_proveedor(db: Session, proveedor_data: ProveedorCreate, id_empresa: int) -> Tercero:
    """Crea un nuevo Tercero asegurando que sea marcado como proveedor y pertenezca a la empresa."""
    nuevo_proveedor = Tercero.from_orm(proveedor_data)
    nuevo_proveedor.es_proveedor = True
    nuevo_proveedor.id_empresa = id_empresa
    
    db.add(nuevo_proveedor)
    db.commit()
    db.refresh(nuevo_proveedor)
    return nuevo_proveedor

def obtener_proveedores(db: Session, id_empresa: int) -> List[Tercero]:
    """Obtiene todos los terceros que son proveedores para una empresa específica."""
    statement = select(Tercero).where(Tercero.id_empresa == id_empresa, Tercero.es_proveedor == True)
    results = db.exec(statement).all()
    return results

def crear_o_actualizar_plantilla(
    db: Session,
    plantilla_data: PlantillaMapeoCreate,
    id_empresa: int
) -> PlantillaMapeoProveedor:
    """Crea o actualiza la plantilla de mapeo para un proveedor de la empresa."""
    statement = select(PlantillaMapeoProveedor).where(
        PlantillaMapeoProveedor.id_proveedor == plantilla_data.id_proveedor,
        PlantillaMapeoProveedor.id_empresa == id_empresa
    )
    plantilla_existente = db.exec(statement).first()

    if plantilla_existente:
        plantilla_existente.mapeo_columnas = plantilla_data.mapeo_columnas
        plantilla_existente.nombre_hoja_excel = plantilla_data.nombre_hoja_excel
        plantilla_existente.fila_inicio = plantilla_data.fila_inicio
        plantilla_existente.nombre_plantilla = plantilla_data.nombre_plantilla
        db.add(plantilla_existente)
        db.commit()
        db.refresh(plantilla_existente)
        return plantilla_existente
    else:
        nueva_plantilla = PlantillaMapeoProveedor.from_orm(plantilla_data)
        nueva_plantilla.id_empresa = id_empresa
        db.add(nueva_plantilla)
        db.commit()
        db.refresh(nueva_plantilla)
        return nueva_plantilla

def asociar_articulo_a_proveedor(db: Session, link_data: ArticuloProveedorLink, id_proveedor: int, id_empresa: int) -> ArticuloProveedor:
    """Crea o actualiza la asociación entre un artículo de la empresa y un proveedor."""
    # Validación: El proveedor debe pertenecer a la empresa
    proveedor = db.get(Tercero, id_proveedor)
    if not proveedor or proveedor.id_empresa != id_empresa:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado en esta empresa.")

    # Validación: El artículo debe pertenecer a la empresa
    articulo = db.get(Articulo, link_data.id_articulo)
    if not articulo or articulo.id_empresa != id_empresa:
        raise HTTPException(status_code=404, detail="Artículo no encontrado en esta empresa.")

    # Crea o actualiza la asociación
    asociacion = ArticuloProveedor(
        id_proveedor=id_proveedor,
        id_articulo=link_data.id_articulo,
        codigo_articulo_proveedor=link_data.codigo_articulo_proveedor
    )
    
    # merge() inserta o actualiza si la clave primaria (id_proveedor, id_articulo) ya existe.
    merged_asociacion = db.merge(asociacion)
    db.commit()
    db.refresh(merged_asociacion)
    return merged_asociacion

    
def obtener_proveedor_por_id(db: Session, id_proveedor: int, id_empresa: int) -> Tercero | None:
    """
    Busca un proveedor por su ID, asegurando que pertenezca a la empresa del usuario.
    Usa la sintaxis de SQLModel para consistencia.
    """
    # Esta es la forma consistente con el resto de tu código
    statement = select(Tercero).where(
        Tercero.id == id_proveedor,
        Tercero.id_empresa == id_empresa,
        Tercero.es_proveedor == True # Buena práctica añadir esto también
    )
    proveedor = db.exec(statement).first()
    return proveedor