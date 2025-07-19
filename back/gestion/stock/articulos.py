# back/gestion/stock/articulos.py
# VERSIÓN REFACTORIZADA - Lógica de negocio para Artículos usando SQLModel (ORM)

from sqlmodel import Session, select
from typing import List, Optional

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

def obtener_articulo_por_id(db: Session, articulo_id: int) -> Optional[Articulo]:
    """
    Obtiene un artículo específico por su ID usando el ORM.
    Devuelve el objeto Articulo o None si no se encuentra.
    """
    return db.get(Articulo, articulo_id)

def obtener_todos_los_articulos(db: Session, skip: int = 0, limit: int = 100) -> List[Articulo]:
    """
    Obtiene una lista paginada de todos los artículos usando el ORM.
    """
    statement = select(Articulo).order_by(Articulo.descripcion).offset(skip).limit(limit)
    return db.exec(statement).all()

def obtener_articulo_por_codigo_barras(db: Session, codigo_barras: str) -> Optional[Articulo]:
    """
    Busca un artículo a través de CUALQUIERA de sus códigos de barras en la tabla 'ArticuloCodigo'.
    Devuelve el objeto Articulo completo si lo encuentra y está activo.
    """
    statement = select(ArticuloCodigo).where(ArticuloCodigo.codigo == codigo_barras)
    resultado_codigo = db.exec(statement).first()
    
    if resultado_codigo and resultado_codigo.articulo and resultado_codigo.articulo.activo:
        return resultado_codigo.articulo
    
    return None

# ===================================================================
# === OPERACIONES DE ESCRITURA (CREATE, UPDATE, DELETE)
# ===================================================================

def crear_articulo(db: Session, articulo_data: ArticuloCreate) -> Articulo:
    """
    Crea un nuevo artículo en la base de datos a partir de datos validados por un schema.
    Lanza una excepción ValueError si ya existe un código duplicado.
    """
    if articulo_data.codigo_interno:
        statement = select(Articulo).where(Articulo.codigo_interno == articulo_data.codigo_interno)
        if db.exec(statement).first():
            raise ValueError(f"El código interno '{articulo_data.codigo_interno}' ya está en uso.")

    db_articulo = Articulo.from_orm(articulo_data)
    
    # Recalculamos el precio de venta automáticamente antes de guardarlo
    _recalcular_precio_venta(db_articulo)
    
    db.add(db_articulo)
    db.commit()
    db.refresh(db_articulo)
    
    return db_articulo

def actualizar_articulo(db: Session, articulo_id: int, articulo_data: ArticuloUpdate) -> Optional[Articulo]:
    """
    Actualiza un artículo existente. Solo modifica los campos que se proporcionan en el schema.
    Recalcula el precio de venta si es necesario.
    """
    db_articulo = db.get(Articulo, articulo_id)
    if not db_articulo:
        return None

    update_data = articulo_data.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_articulo, key, value)
        
    # Después de aplicar los cambios, recalculamos el precio
    _recalcular_precio_venta(db_articulo)

    db.add(db_articulo)
    db.commit()
    db.refresh(db_articulo)
    
    return db_articulo

def eliminar_articulo(db: Session, articulo_id: int) -> Optional[Articulo]:
    """
    Realiza una "eliminación lógica" de un artículo, marcándolo como inactivo.
    Devuelve el artículo actualizado o None si no se encontró.
    """
    db_articulo = db.get(Articulo, articulo_id)
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