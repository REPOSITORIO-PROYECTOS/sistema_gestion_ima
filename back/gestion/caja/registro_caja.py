# back/gestion/caja/registro_caja.py

from datetime import datetime
from mysql.connector import Error

from back.utils.mysql_handler import get_db_connection
# Importamos los otros "gestores" que contendrán la lógica específica
from back.gestion.stock_manager import actualizar_stock_por_venta_y_detalle
# Suponemos que existen estos módulos que también migraremos
# from back.gestion.clientes_manager import verificar_cliente_y_cta_cte
# from back.gestion.facturacion_manager import generar_comprobante

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
    id_sesion_caja: int,
    articulos_vendidos: list,
    id_cliente: int,
    metodo_pago: str,
    usuario: str,
    total_venta: float,
    quiere_factura: bool = True,
    tipo_comprobante_solicitado: str = None
):
    """
    Orquesta el registro de una venta completa dentro de una única transacción de base de datos.
    Esto incluye: movimiento de caja, actualización de stock, (futuro) cuenta corriente y facturación.
    """
    conn = get_db_connection()
    if not conn:
        return {"status": "error", "message": "Error de conexión a la base de datos."}

    cursor = conn.cursor()

    try:
        # --- INICIO DE LA TRANSACCIÓN MAESTRA ---
        # Si algo falla en cualquier punto, todo se revierte.
        conn.start_transaction()

        # --- 1. Lógica de Cliente y Cuenta Corriente (a implementar en su propio módulo) ---
        # cliente_data = verificar_cliente_y_cta_cte(id_cliente, total_venta, metodo_pago, cursor)
        # monto_para_caja = cliente_data['monto_para_caja']
        # monto_a_cta_cte = cliente_data['monto_a_cta_cte']
        # Por ahora, simplificamos y asumimos que todo va a caja:
        monto_para_caja = total_venta
        
        # --- 2. Crear el Movimiento de Caja ---
        concepto_venta = f"Venta (Cliente ID: {id_cliente}, Items: {len(articulos_vendidos)})"
        query_movimiento = """
            INSERT INTO caja_movimientos (id_sesion, fecha, usuario, tipo_movimiento, concepto, monto, metodo_pago)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        valores_movimiento = (id_sesion_caja, datetime.now(), usuario, 'VENTA', concepto_venta, monto_para_caja, metodo_pago)
        cursor.execute(query_movimiento, valores_movimiento)
        id_movimiento_venta = cursor.lastrowid
        print(f"[REGISTRO_CAJA] Movimiento de Venta ID {id_movimiento_venta} creado.")

        # --- 3. Actualizar Stock y Registrar Detalles de Venta ---
        # Llamamos al gestor de stock, que trabaja dentro de NUESTRA transacción.
        # Esta función ahora también se encargará de insertar en `venta_detalle`.
        actualizar_stock_por_venta_y_detalle(id_movimiento_venta, articulos_vendidos, cursor)
        
        # --- 4. Generar Comprobante Fiscal (a implementar en su propio módulo) ---
        # if quiere_factura:
        #     res_factura = generar_comprobante(
        #         id_movimiento_origen=id_movimiento_venta,
        #         cliente_data=cliente_data,
        #         items=articulos_vendidos,
        #         total=total_venta,
        #         tipo_solicitado=tipo_comprobante_solicitado,
        #         cursor=cursor
        #     )
        #     id_comprobante_emitido = res_factura['id_comprobante']
        #     numero_comprobante = res_factura['numero']
        # else:
        id_comprobante_emitido = None
        numero_comprobante = "N/A"

        # --- FIN DE LA TRANSACCIÓN ---
        # Si llegamos aquí, todas las partes (caja, stock, cta cte, factura) funcionaron.
        conn.commit()
        print(f"[REGISTRO_CAJA] Transacción completada y guardada exitosamente.")

        return {
            "status": "success",
            "message": f"Venta registrada. Comprobante: {numero_comprobante}.",
            "id_movimiento_venta": id_movimiento_venta,
            "id_comprobante_emitido": id_comprobante_emitido
        }

    except (Error, ValueError) as e:
        # Si CUALQUIER error ocurre en CUALQUIER paso, se revierte todo.
        print(f"[REGISTRO_CAJA] ERROR en la transacción, revirtiendo todo. Detalle: {e}")
        conn.rollback()
        # Devolvemos un mensaje de error claro al frontend.
        return {"status": "error", "message": str(e)}
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

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