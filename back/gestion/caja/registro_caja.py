# back/gestion/caja/registro_caja.py

from datetime import datetime
from mysql.connector import Error
from sqlmodel import Session, select
from datetime import datetime
# Importa todos tus modelos. Asegúrate de que las rutas sean correctas.
from back.modelos import Venta, VentaDetalle, CajaMovimiento, Articulo 
from back.utils.mysql_handler import get_db_connection
# Importamos los otros "gestores" que contendrán la lógica específica
# Suponemos que existen estos módulos que también migraremos
# from back.gestion.clientes_manager import verificar_cliente_y_cta_cte
# from back.gestion.facturacion_manager import generar_comprobante

#ACA TENGO QUE REGISTRAR CUANDO ENTRA Y CUANDO SALE PLATA, MODIFICA LA TABLA MOVIMIENTOS
  


def registrar_ingreso_egreso(id_sesion_caja: int, concepto: str, monto: float, tipo: str, usuario: str):
    """
    Registra un ingreso o egreso simple en la caja.
    'tipo' debe ser 'INGRESO' o 'EGRESO'.
    """
    if tipo.upper() not in ['INGRESO', 'EGRESO']:
        return {"status": "error", "message": "Tipo de movimiento no válido."}

    conn = get_db_connection()
    if not conn:
        return {"status": "error", "message": "Error de conexión a la base de datos."}
    
    cursor = conn.cursor()
    try:
        query = """
            INSERT INTO caja_movimientos (id_sesion, fecha, usuario, tipo_movimiento, concepto, monto)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        # Guardamos el monto como negativo si es un egreso para facilitar sumas
        monto_a_registrar = monto if tipo.upper() == 'INGRESO' else -abs(monto)
        
        valores = (id_sesion_caja, datetime.now(), usuario, tipo.upper(), concepto, monto_a_registrar)
        cursor.execute(query, valores)
        conn.commit()
        
        return {
            "status": "success",
            "message": f"{tipo.capitalize()} de ${abs(monto):.2f} registrado.",
            "id_movimiento": cursor.lastrowid
        }
    except Error as e:
        conn.rollback()
        return {"status": "error", "message": f"Error de base de datos: {e}"}
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()



def registrar_venta(
    db: Session,
    id_sesion_caja: int,
    articulos_vendidos: list,  # Espera una lista de dicts: [{"id_articulo": 1, "cantidad": 2}, ...]
    id_cliente: int,
    id_usuario: int,
    metodo_pago: str,
    total_venta: float
):
    """
    Orquesta el registro de una venta completa usando SQLModel
    dentro de una única transacción de base de datos.
    Actualiza Venta, VentaDetalle, Articulo (stock) y CajaMovimiento.
    """
    try:
        # --- PASO 1: Crear el registro principal de la VENTA ---
        nueva_venta = Venta(
            total=total_venta,
            id_cliente=id_cliente,
            id_usuario=id_usuario,
            id_caja_sesion=id_sesion_caja,
            timestamp=datetime.utcnow()
            # estado se establece por defecto a "COMPLETADA"
        )
        db.add(nueva_venta)

        # --- PASO 2: Iterar artículos, actualizar stock y crear detalles ---
        for item_data in articulos_vendidos:
            id_articulo = item_data.get("id_articulo")
            cantidad_vendida = item_data.get("cantidad")

            if not id_articulo or not cantidad_vendida:
                raise ValueError("Cada artículo vendido debe tener 'id_articulo' y 'cantidad'.")

            # Busca el artículo en la BDD y lo bloquea para la actualización.
            articulo_db = db.exec(
                select(Articulo).where(Articulo.id == id_articulo).with_for_update()
            ).first()

            if not articulo_db:
                raise ValueError(f"El artículo con ID {id_articulo} no existe.")

            # VALIDACIÓN ADICIONAL: Comprobar si el artículo está activo
            if not articulo_db.activo:
                raise ValueError(f"El artículo '{articulo_db.descripcion}' (ID: {id_articulo}) no está activo y no se puede vender.")

            # VALIDACIÓN DE STOCK: Usando el campo correcto 'stock_actual'
            if articulo_db.stock_actual < cantidad_vendida:
                raise ValueError(f"Stock insuficiente para '{articulo_db.descripcion}'. Disponible: {articulo_db.stock_actual}, Solicitado: {cantidad_vendida}")

            # ACTUALIZACIÓN DE STOCK: Usando el campo correcto 'stock_actual'
            articulo_db.stock_actual -= cantidad_vendida
            
            # NOTA: Si `maneja_lotes` es True, aquí iría una lógica más compleja
            # para seleccionar y descontar de un lote específico. Por ahora, se omite.
            
            # Crear el registro de VentaDetalle
            detalle_venta = VentaDetalle(
                cantidad=cantidad_vendida,
                precio_unitario=articulo_db.precio_venta, # Guarda el precio al momento de la venta
                id_articulo=id_articulo,
                venta=nueva_venta # El ORM asocia este detalle con la venta padre
            )
            db.add(detalle_venta)

        # Hacemos un "flush" para que nueva_venta obtenga su ID de la BDD.
        # Esto es necesario para poder usarlo en el concepto del movimiento de caja.
        db.flush()

        # --- PASO 3: Crear el movimiento de caja asociado ---
        concepto_venta = f"Venta #{nueva_venta.id} (Cliente ID: {id_cliente})"
        
        movimiento_caja = CajaMovimiento(
            id_caja_sesion=id_sesion_caja,
            id_usuario=id_usuario,
            tipo='VENTA',
            concepto=concepto_venta,
            monto=total_venta,
            metodo_pago=metodo_pago,
            id_venta=nueva_venta.id # Asociamos el movimiento con la venta
        )
        db.add(movimiento_caja)
        
        # --- PASO 4: Confirmar la transacción ---
        # Si llegamos aquí sin errores, guardamos todos los cambios a la vez.
        db.commit()

        # Refrescamos los objetos para obtener sus datos finales (como IDs generados)
        db.refresh(nueva_venta)
        db.refresh(movimiento_caja)

        print(f"[REGISTRO_CAJA] Transacción completada. Venta ID: {nueva_venta.id}, Movimiento ID: {movimiento_caja.id}")

        return {
            "status": "success",
            "message": f"Venta ID {nueva_venta.id} registrada exitosamente.",
            "id_venta": nueva_venta.id,
            "id_movimiento": movimiento_caja.id
        }

    except ValueError as e: # Errores de negocio (ej. stock)
        print(f"[REGISTRO_CAJA] ERROR de lógica, revirtiendo transacción. Detalle: {e}")
        db.rollback()
        return {"status": "error", "message": str(e)}
    except Exception as e: # Cualquier otro error inesperado
        print(f"[REGISTRO_CAJA] ERROR inesperado, revirtiendo transacción. Detalle: {e}")
        db.rollback()
        return {"status": "error", "message": "Ocurrió un error interno al procesar la venta."}



def calcular_vuelto(total_a_pagar: float, monto_recibido: float):
    """
    Calcula el vuelto para una transacción. Es una función puramente matemática,
    no necesita base de datos ni E/S, por lo que puede permanecer casi igual.
    """
    if monto_recibido < total_a_pagar:
        # En una API, en lugar de imprimir, devolvemos un error estructurado.
        raise ValueError(f"Monto insuficiente. Faltan: ${total_a_pagar - monto_recibido:.2f}")

    vuelto = monto_recibido - total_a_pagar
    return vuelto