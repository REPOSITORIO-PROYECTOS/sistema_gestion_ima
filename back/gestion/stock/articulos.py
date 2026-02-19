# back/gestion/stock/articulos.py
# VERSIÓN REFACTORIZADA - Lógica de negocio para Artículos usando SQLModel (ORM)

from sqlmodel import Session, or_, select
from typing import List, Optional
from sqlalchemy.orm import selectinload

# --- Modelos de la Base de Datos ---
from back.modelos import Articulo, ArticuloCodigo

# --- Schemas (DTOs) para validación de datos ---
# ¡ESTA ES LA IMPORTACIÓN QUE FALTABA Y CAUSABA EL ERROR DE ARRANQUE!
from back.schemas.articulo_schemas import ArticuloCreate, ArticuloUpdate

# ===================================================================
# === FUNCIONES DE AYUDA INTERNA
# ===================================================================

def _recalcular_precio_venta(articulo: Articulo):
    """
    Función interna para recalcular el precio de venta de un artículo basado en su costo y márgenes.
    No guarda en la BD, solo modifica el objeto que se le pasa.
    """
    if not articulo.auto_actualizar_precio:
        return  # Si está en modo manual, no hacemos nada

    if articulo.factor_conversion <= 0:
        costo_unitario_venta = articulo.precio_costo
    else:
        costo_unitario_venta = articulo.precio_costo / articulo.factor_conversion

    precio_con_margen = costo_unitario_venta * (1 + articulo.margen_ganancia)
    precio_final = precio_con_margen * (1 + articulo.tasa_iva)
    
    articulo.precio_venta = round(precio_final, 2)

# ===================================================================
# === OPERACIONES DE LECTURA (GET)
# ===================================================================

def obtener_articulo_por_id(id_empresa: int, db: Session, articulo_id: int) -> Optional[Articulo]:
    """
    CORREGIDO: Obtiene un artículo específico por su ID, asegurando que pertenezca a la empresa.
    """
    statement = (
        select(Articulo)
        .where(Articulo.id == articulo_id, Articulo.id_empresa == id_empresa)
        .options(selectinload(Articulo.codigos))
    )
    return db.exec(statement).first() # Usamos .first() para obtener solo uno.

def buscar_articulo_por_codigo(db: Session, id_empresa_actual: int, codigo: str) -> Optional[Articulo]:
    """
    Busca un artículo por uno de sus códigos de barras, incluso si hay múltiples códigos
    separados por punto y coma. Asegura que el artículo pertenezca a la empresa del usuario.
    Pre-carga eficientemente todos los demás códigos de barras asociados al artículo encontrado.
    """

    statement = (
        select(Articulo)
        .join(ArticuloCodigo)
        .where(
            # Aseguramos que la búsqueda sea dentro de la empresa y en artículos activos
            Articulo.id_empresa == id_empresa_actual,
            Articulo.activo == True,
            # Nueva condición para buscar el código dentro del string
            or_(
                ArticuloCodigo.codigo == codigo,
                ArticuloCodigo.codigo.like(f'{codigo};%'),
                ArticuloCodigo.codigo.like(f'%;{codigo};%'),
                ArticuloCodigo.codigo.like(f'%;{codigo}')
            )
        )
        .options(selectinload(Articulo.codigos))
    )
    return db.exec(statement).first()


def obtener_todos_los_articulos(db: Session, id_empresa_actual: int, skip: int = 0, limit: int = 100) -> List[Articulo]:
    """
    Obtiene una lista paginada de artículos, pre-cargando eficientemente sus códigos de barras.
    Usa DISTINCT para evitar duplicados cuando hay múltiples códigos de barras.
    """
    statement = (
        select(Articulo)
        .where(Articulo.id_empresa == id_empresa_actual)
        .order_by(Articulo.descripcion)
        .offset(skip)
        .limit(limit)
        .distinct()
        .options(selectinload(Articulo.codigos))
    )
    return db.exec(statement).all()

def buscar_articulos_por_termino(
    db: Session, 
    id_empresa_actual: int, 
    termino: str,
    skip: int = 0, 
    limit: int = 100
) -> List[Articulo]:
    """
    NUEVA FUNCIÓN: Busca artículos de una empresa que coincidan con un término de búsqueda.
    Filtra por descripción, código interno y códigos de barras asociados.
    """
    
    # Preparamos el término para una búsqueda de tipo "contiene"
    termino_like = f"%{termino}%"

    # La consulta es casi idéntica a la que te propuse antes, pero ahora
    # vive en su propia función.
    statement = (
        select(Articulo)
        .join(ArticuloCodigo, isouter=True) # isouter=True es un LEFT JOIN
        .where(
            Articulo.id_empresa == id_empresa_actual,
            or_(
                Articulo.descripcion.ilike(termino_like),
                Articulo.codigo_interno.ilike(termino_like),
                ArticuloCodigo.codigo.ilike(termino_like)
            )
        )
        .distinct()
        .order_by(Articulo.descripcion)
        .offset(skip)
        .limit(limit)
        .options(selectinload(Articulo.codigos))
    )
    
    return db.exec(statement).all()

# ===================================================================
# === OPERACIONES DE ESCRITURA (CREATE, UPDATE, DELETE)
# ===================================================================
def crear_articulo(id_empresa: int, db: Session, articulo_data: ArticuloCreate) -> Articulo:
    """
    CORREGIDO: Crea un nuevo artículo. La validación de código duplicado ahora es por empresa.
    """
    if articulo_data.codigo_interno:
        statement = select(Articulo).where(
            Articulo.codigo_interno == articulo_data.codigo_interno,
            Articulo.id_empresa == id_empresa # <-- Seguridad añadida
        )
        if db.exec(statement).first():
            raise ValueError(f"El código interno '{articulo_data.codigo_interno}' ya está en uso en tu empresa.")

    db_articulo = Articulo.from_orm(articulo_data, {"id_empresa": id_empresa})
    _recalcular_precio_venta(db_articulo)
    db.add(db_articulo)
    db.commit()
    db.refresh(db_articulo)
    return db_articulo

def actualizar_articulo(id_empresa: int, db: Session, articulo_id: int, articulo_data: ArticuloUpdate) -> Optional[Articulo]:
    """
    Actualiza un artículo existente de una empresa específica.
    """
    stmt = select(Articulo).where(Articulo.id == articulo_id, Articulo.id_empresa == id_empresa)
    db_articulo = db.exec(stmt).first()
    if not db_articulo:
        return None
    update_data = articulo_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_articulo, key, value)
    _recalcular_precio_venta(db_articulo)
    db.add(db_articulo)
    db.commit()
    db.refresh(db_articulo)
    return db_articulo

def eliminar_articulo(db: Session, id_empresa_actual: int, articulo_id: int) -> Optional[Articulo]:
    """
    Realiza una "eliminación lógica" de un artículo, asegurando que pertenezca a la empresa.
    """
    db_articulo = db.exec(select(Articulo).where(Articulo.id == articulo_id, Articulo.id_empresa == id_empresa_actual)).first()
    if not db_articulo:
        return None
    db_articulo.activo = False
    db.add(db_articulo)
    db.commit()
    db.refresh(db_articulo)
    return db_articulo

# ===================================================================
# === GESTIÓN DE CÓDIGOS DE BARRAS MÚLTIPLES
# ===================================================================

def anadir_codigo_a_articulo(db: Session, articulo_id: int, nuevo_codigo: str) -> ArticuloCodigo:
    """Añade un nuevo código de barras a un artículo existente."""
    articulo = db.get(Articulo, articulo_id)
    if not articulo:
        raise ValueError("El artículo no existe.")
        
    codigo_existente = db.get(ArticuloCodigo, nuevo_codigo)
    if codigo_existente:
        raise ValueError(f"El código '{nuevo_codigo}' ya está asignado a otro artículo.")

    nuevo_codigo_obj = ArticuloCodigo(codigo=nuevo_codigo, id_articulo=articulo_id)
    db.add(nuevo_codigo_obj)
    db.commit()
    db.refresh(nuevo_codigo_obj)
    
    return nuevo_codigo_obj

def eliminar_codigo_de_articulo(db: Session, codigo_a_borrar: str) -> bool:
    """Elimina un código de barras de la base de datos."""
    codigo_obj = db.get(ArticuloCodigo, codigo_a_borrar)
    if not codigo_obj:
        return False

    db.delete(codigo_obj)
    db.commit()
    return True