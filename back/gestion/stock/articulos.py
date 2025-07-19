# back/gestion/stock/articulos.py

#ACA TENGO QUE USAR LA TABLA STOCK, Y DEVOLVER LOS PRODUCTOS 


from mysql.connector import Error
from sqlmodel import Session, select
from back.modelos import Articulo, ArticuloCodigo
from back.utils.mysql_handler import get_db_connection
from typing import Optional
from sqlalchemy.orm import selectinload



def obtener_articulo_por_id(id_articulo: str):
    """
    Obtiene un artículo específico por su ID desde la base de datos MySQL.
    Devuelve un diccionario con los datos del artículo o None si no se encuentra.
    """
    conn = get_db_connection()
    if not conn:
        print("Error de conexión al buscar artículo.")
        return None

    # Usamos un cursor de diccionario para obtener un resultado fácil de usar
    cursor = conn.cursor(dictionary=True)
    try:
        query = "SELECT * FROM articulos WHERE id_articulo = %s"
        cursor.execute(query, (id_articulo,))
        articulo = cursor.fetchone()
        
        if articulo:
            print(f"[ARTICULOS_DB] Artículo encontrado: {id_articulo}")
            return articulo
        else:
            print(f"[ARTICULOS_DB] Artículo con ID {id_articulo} no encontrado.")
            return None
    except Error as e:
        print(f"Error de base de datos al obtener artículo {id_articulo}: {e}")
        return None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def obtener_todos_los_articulos_orm(db: Session, skip: int = 0, limit: int = 100):
    """
    Obtiene una lista paginada de artículos usando el ORM (SQLModel).
    """
    # Creamos la consulta base
    statement = select(Articulo).order_by(Articulo.id).offset(skip).limit(limit)
    
    # Ejecutamos la consulta y obtenemos los resultados
    articulos = db.exec(statement).all()
    
    return articulos

def crear_articulo(id_articulo: str, descripcion: str, precio_venta: float, stock_inicial: int = 0):
    """
    Crea un nuevo artículo en la base de datos.
    """
    conn = get_db_connection()
    if not conn:
        return {"status": "error", "message": "Error de conexión."}

    cursor = conn.cursor()
    try:
        query = """
            INSERT INTO articulos (id_articulo, descripcion, precio_venta, stock)
            VALUES (%s, %s, %s, %s)
        """
        valores = (id_articulo, descripcion, precio_venta, stock_inicial)
        cursor.execute(query, valores)
        conn.commit()
        
        return {
            "status": "success",
            "message": f"Artículo '{descripcion}' creado exitosamente.",
            "data": {"id_articulo": id_articulo}
        }
    except Error as e:
        conn.rollback()
        # Manejar error de clave duplicada de forma amigable
        if e.errno == 1062: # Código de error para 'Duplicate entry'
            return {"status": "error", "message": f"El ID de artículo '{id_articulo}' ya existe."}
        return {"status": "error", "message": f"Error de base de datos: {e}"}
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def actualizar_articulo(id_articulo: str, descripcion: Optional[str] = None, precio_venta: Optional[float] = None, costo_ultimo: Optional[float] = None, categoria: Optional[str] = None):
    """
    Actualiza los datos de un artículo existente. Solo actualiza los campos que se proporcionan.
    El stock no se actualiza aquí, se maneja por ventas/compras.
    """
    conn = get_db_connection()
    if not conn: return {"status": "error", "message": "Error de conexión."}
    
    cursor = conn.cursor()
    try:
        # Construimos la consulta dinámicamente para solo actualizar los campos proporcionados
        update_fields = []
        valores = []
        
        if descripcion is not None:
            update_fields.append("descripcion = %s")
            valores.append(descripcion)
        if precio_venta is not None:
            update_fields.append("precio_venta = %s")
            valores.append(precio_venta)
        if costo_ultimo is not None:
            update_fields.append("costo_ultimo = %s")
            valores.append(costo_ultimo)
        if categoria is not None:
            update_fields.append("categoria = %s")
            valores.append(categoria)
        
        if not update_fields:
            return {"status": "info", "message": "No se proporcionaron campos para actualizar."}

        query = f"UPDATE articulos SET {', '.join(update_fields)} WHERE id_articulo = %s"
        valores.append(id_articulo)
        
        cursor.execute(query, tuple(valores))
        conn.commit()
        
        # rowcount nos dice cuántas filas fueron afectadas. Si es 0, el artículo no existía.
        if cursor.rowcount == 0:
            return {"status": "error", "message": f"Artículo con ID '{id_articulo}' no encontrado."}
            
        return {"status": "success", "message": f"Artículo '{id_articulo}' actualizado correctamente."}
    except Error as e:
        conn.rollback()
        return {"status": "error", "message": f"Error de base de datos: {e}"}
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def eliminar_articulo(id_articulo: str):
    """
    Elimina un artículo de la base de datos.
    ADVERTENCIA: Esto puede fallar si el artículo ya tiene ventas registradas (por la FOREIGN KEY).
    Una mejor práctica podría ser una "eliminación lógica" (marcarlo como inactivo).
    """
    conn = get_db_connection()
    if not conn: return {"status": "error", "message": "Error de conexión."}

    cursor = conn.cursor()
    try:
        query = "DELETE FROM articulos WHERE id_articulo = %s"
        cursor.execute(query, (id_articulo,))
        conn.commit()
        
        if cursor.rowcount == 0:
            return {"status": "error", "message": f"Artículo con ID '{id_articulo}' no encontrado."}
        
        return {"status": "success", "message": f"Artículo '{id_articulo}' eliminado exitosamente."}
    except Error as e:
        conn.rollback()
        # Error de restricción de clave foránea
        if e.errno == 1451:
            return {"status": "error", "message": f"No se puede eliminar el artículo '{id_articulo}' porque tiene movimientos asociados (ventas, compras, etc.). Considere marcarlo como inactivo."}
        return {"status": "error", "message": f"Error de base de datos: {e}"}
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
            
def obtener_articulo_por_codigo_barras(db: Session, codigo_barras: str) -> Optional[Articulo]:
    """
    Busca un único artículo por su código de barras.
    La búsqueda distingue mayúsculas/minúsculas y espacios, debe ser exacta.
    Devuelve el objeto Articulo o None si no se encuentra.
    """
    statement = (
        select(Articulo)
        .where(Articulo.codigo_barras == codigo_barras)
        .where(Articulo.activo == True) # Importante: solo buscar artículos activos
        .options(selectinload('*')) # Opcional: Cargar relaciones si es necesario para la venta
    )
    
    articulo = db.exec(statement).first()
    return articulo

def anadir_codigo_a_articulo(db: Session, articulo_id: int, nuevo_codigo: str) -> ArticuloCodigo:
    """Añade un nuevo código de barras a un artículo existente."""
    
    # 1. Verificar si el artículo existe
    articulo = db.get(Articulo, articulo_id)
    if not articulo:
        raise ValueError("El artículo no existe.")
        
    # 2. Verificar si el código ya está en uso por OTRO artículo
    codigo_existente = db.get(ArticuloCodigo, nuevo_codigo)
    if codigo_existente:
        raise ValueError(f"El código '{nuevo_codigo}' ya está asignado a otro artículo.")

    # 3. Crear y guardar el nuevo código
    nuevo_codigo_obj = ArticuloCodigo(codigo=nuevo_codigo, id_articulo=articulo_id)
    db.add(nuevo_codigo_obj)
    db.commit()
    db.refresh(nuevo_codigo_obj)
    
    return nuevo_codigo_obj

def eliminar_codigo_de_articulo(db: Session, codigo_a_borrar: str) -> bool:
    """Elimina un código de barras."""
    codigo_obj = db.get(ArticuloCodigo, codigo_a_borrar)
    if not codigo_obj:
        return False # No se encontró el código

    db.delete(codigo_obj)
    db.commit()
    return True

def _recalcular_precio_venta(articulo: Articulo):
    """
    Función interna para recalcular el precio de venta de un artículo.
    No guarda en la BD, solo modifica el objeto.
    """
    if not articulo.auto_actualizar_precio:
        return # Si está en modo manual, no hacemos nada

    if articulo.factor_conversion <= 0:
        # Evitar división por cero
        costo_unitario_venta = articulo.precio_costo
    else:
        # El costo por unidad de venta (la "división")
        costo_unitario_venta = articulo.precio_costo / articulo.factor_conversion

    # Aplicamos el margen de ganancia
    precio_con_margen = costo_unitario_venta * (1 + articulo.margen_ganancia)
    
    # Aplicamos el impuesto (el IVA de AFIP)
    precio_final = precio_con_margen * (1 + articulo.tasa_iva)
    
    # Actualizamos el precio de venta del artículo, redondeando a 2 decimales
    articulo.precio_venta = round(precio_final, 2)

# Ahora, en tu función de crear o actualizar, llamas a esta ayuda:
def crear_articulosa(db: Session, articulo_data: ArticuloCreate) -> Articulo:
    # ... (validaciones de código duplicado)
    
    db_articulo = Articulo.from_orm(articulo_data)
    
    # ¡Llamamos al calculador antes de guardar!
    _recalcular_precio_venta(db_articulo)
    
    db.add(db_articulo)
    db.commit()
    db.refresh(db_articulo)
    return db_articulo

def actualizar_articulo(db: Session, articulo_id: int, articulo_data: ArticuloUpdate) -> Optional[Articulo]:
    db_articulo = db.get(Articulo, articulo_id)
    if not db_articulo:
        return None

    update_data = articulo_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_articulo, key, value)
        
    # ¡Llamamos al calculador antes de guardar!
    _recalcular_precio_venta(db_articulo)

    db.add(db_articulo)
    db.commit()
    db.refresh(db_articulo)
    return db_articulo