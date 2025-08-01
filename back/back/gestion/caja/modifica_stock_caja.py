# back/gestion/stock_manager.py (función modificada)

#MODIFICA LA TABLA STOCK, TENGO QUE RESTAR LA CANTIDAD DE PRODUCTOS VENDIDOS O SUMAR

#HACER FUNCION PARA VOLVER PARA ATRAS LA VENTA, SUMAR LOS PRODUCTOS VENDIDOS

def actualizar_stock_por_venta_y_detalle(id_movimiento_venta: int, articulos_vendidos: list, cursor):
    """
    - Verifica el stock de los artículos.
    - Inserta los registros en la tabla `venta_detalle`.
    - Actualiza (reduce) el stock en la tabla `articulos`.
    Todo esto como parte de una transacción externa. Lanza excepción si algo falla.
    """
    try:
        # (Aquí va la lógica de verificación de stock que ya teníamos: SELECT ... FOR UPDATE)
        for item in articulos_vendidos:
            cursor.execute("SELECT stock FROM articulos WHERE id_articulo = %s FOR UPDATE", (item['id_articulo'],))
            articulo_db = cursor.fetchone()
            if not articulo_db:
                raise ValueError(f"Artículo ID {item['id_articulo']} no encontrado.")
            if articulo_db[0] < item['cantidad']:
                raise ValueError(f"Stock insuficiente para {item['id_articulo']}.")
        
        # Si la verificación pasa, procedemos
        query_detalle = "INSERT INTO venta_detalle (id_movimiento_venta, id_articulo, cantidad, precio_unitario, subtotal) VALUES (%s, %s, %s, %s, %s)"
        query_update_stock = "UPDATE articulos SET stock = stock - %s WHERE id_articulo = %s"

        for item in articulos_vendidos:
            valores_detalle = (id_movimiento_venta, item['id_articulo'], item['cantidad'], item['precio_unitario'], item['subtotal'])
            cursor.execute(query_detalle, valores_detalle)
            
            valores_stock = (item['cantidad'], item['id_articulo'])
            cursor.execute(query_update_stock, valores_stock)
        
        print(f"[STOCK_MANAGER] Detalles de venta y stock actualizados para Venta ID: {id_movimiento_venta}")

    except (Error, ValueError) as e:
        print(f"[STOCK_MANAGER] ERROR: {e}")
        raise e # Relanzamos la excepción para que la transacción principal haga rollback