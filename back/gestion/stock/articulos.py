# back/gestion/stock/articulos.py

#ACA TENGO QUE USAR LA TABLA STOCK, Y DEVOLVER LOS PRODUCTOS 


from mysql.connector import Error
from back.utils.mysql_handler import get_db_connection

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

def obtener_todos_los_articulos(limite: int = 100, pagina: int = 1):
    """
    Obtiene una lista paginada de todos los artículos de la base de datos.
    Ideal para mostrar en una tabla en el frontend.
    """
    conn = get_db_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)
    try:
        # Calculamos el offset para la paginación
        offset = (pagina - 1) * limite
        
        query = "SELECT * FROM articulos ORDER BY id_articulo LIMIT %s OFFSET %s"
        cursor.execute(query, (limite, offset))
        articulos = cursor.fetchall()
        
        # También podríamos querer devolver el total de artículos para la paginación del frontend
        # cursor.execute("SELECT COUNT(*) as total FROM articulos")
        # total_articulos = cursor.fetchone()['total']
        
        return articulos # , total_articulos
    except Error as e:
        print(f"Error de base deatos al obtener todos los artículos: {e}")
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

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
