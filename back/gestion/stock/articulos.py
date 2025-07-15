# back/gestion/stock/articulos.py

#ACA TENGO QUE USAR LA TABLA STOCK, Y DEVOLVER LOS PRODUCTOS 


from mysql.connector import Error
from sqlmodel import Session, select
from back.modelos import Articulo
from back.utils.mysql_handler import get_db_connection
from typing import Optional


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