# back/gestion/caja/apertura_cierre.py

from datetime import datetime
from mysql.connector import Error

# Importamos nuestro manejador de MySQL, la única dependencia de "bajo nivel" que necesitamos
from back.utils.mysql_handler import get_db_connection
# (Opcional) Importamos el futuro módulo de reportería
# from back.utils.reporteria_sheets import generar_reporte_cierre_a_sheets

def obtener_estado_caja_actual():
    """
    Verifica si hay alguna caja con estado 'ABIERTA' en la tabla `caja_sesiones`.
    Devuelve el diccionario de la sesión si la encuentra, o None si no hay ninguna abierta.
    """
    conn = get_db_connection()
    if not conn:
        print("Error de conexión al intentar obtener estado de caja.")
        return None 
    
    # Usar 'dictionary=True' nos devuelve las filas como diccionarios, igual que get_all_records
    cursor = conn.cursor(dictionary=True)
    try:
        # La consulta es simple, directa y muy rápida
        query = "SELECT * FROM caja_sesiones WHERE estado = 'ABIERTA' ORDER BY id_sesion DESC LIMIT 1"
        cursor.execute(query)
        sesion_abierta = cursor.fetchone() # fetchone() devuelve un registro o None si no hay resultados
        return sesion_abierta
    except Error as e:
        print(f"Error de base de datos al obtener estado de caja: {e}")
        return None
    finally:
        # Siempre cerramos la conexión para liberar recursos
        if conn.is_connected():
            cursor.close()
            conn.close()

def abrir_caja(saldo_inicial: float, usuario: str):
    """
    Registra la apertura de caja en la base de datos MySQL.
    1. Verifica que no haya otra caja abierta.
    2. Inserta un nuevo registro en `caja_sesiones`.
    3. Inserta el movimiento de apertura correspondiente en `caja_movimientos`.
    Todo dentro de una transacción para asegurar la consistencia.
    """
    # 1. Usamos nuestra función refactorizada para una verificación limpia
    if obtener_estado_caja_actual():
        return {
            "status": "error",
            "message": "Ya existe una caja abierta. Debe cerrarla antes de abrir una nueva."
        }

    conn = get_db_connection()
    if not conn:
        return {"status": "error", "message": "Error de conexión a la base de datos."}

    cursor = conn.cursor()
    try:
        # Una transacción asegura que si algo falla, no se guarda nada a medias
        conn.start_transaction()

        # 2. Insertar la nueva sesión. MySQL se encarga del ID automáticamente.
        query_sesion = """
            INSERT INTO caja_sesiones (fecha_apertura, usuario_apertura, saldo_inicial, estado)
            VALUES (%s, %s, %s, %s)
        """
        fecha_actual = datetime.now()
        # No necesitamos formatear la fecha, el conector de MySQL lo maneja
        valores_sesion = (fecha_actual, usuario, saldo_inicial, 'ABIERTA')
        cursor.execute(query_sesion, valores_sesion)
        
        # Obtenemos el ID autogenerado por MySQL para la sesión que acabamos de crear
        id_nueva_sesion = cursor.lastrowid

        # 3. Insertar el movimiento de apertura en la tabla de movimientos
        query_movimiento = """
            INSERT INTO caja_movimientos (id_sesion, fecha, tipo_movimiento, concepto, monto, usuario)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        valores_movimiento = (id_nueva_sesion, fecha_actual, 'APERTURA', 'Saldo inicial de caja', saldo_inicial, usuario)
        cursor.execute(query_movimiento, valores_movimiento)
        
        # Si todo fue bien, confirmamos los cambios
        conn.commit()

        return {
            "status": "success",
            "id_sesion": id_nueva_sesion,
            "message": f"Caja abierta exitosamente por {usuario} con un saldo de ${saldo_inicial:.2f}."
        }
    except Error as e:
        conn.rollback() # Revertimos todos los cambios si hubo un error
        return {"status": "error", "message": f"Error de base de datos al abrir la caja: {e}"}
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


def cerrar_caja(id_sesion: int, saldo_final_contado: float, usuario_cierre: str):
    """
    Cierra una sesión de caja en la base de datos MySQL.
    1. Calcula el saldo teórico a partir de los movimientos en la DB.
    2. Calcula la diferencia.
    3. Actualiza el registro de la sesión a 'CERRADA' con todos los datos del cierre.
    4. (Futuro) Llama al módulo de reportería.
    """
    conn = get_db_connection()
    if not conn:
        return {"status": "error", "message": "Error de conexión a la base de datos."}

    # Usamos cursores de diccionario para leer datos fácilmente
    cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()

        # Paso 0: Verificar que la sesión a cerrar existe y está abierta
        cursor.execute("SELECT id_sesion, saldo_inicial FROM caja_sesiones WHERE id_sesion = %s AND estado = 'ABIERTA'", (id_sesion,))
        sesion_a_cerrar = cursor.fetchone()
        if not sesion_a_cerrar:
            conn.rollback()
            return {"status": "error", "message": f"La sesión de caja {id_sesion} no existe o ya está cerrada."}
        
        saldo_inicial_db = sesion_a_cerrar['saldo_inicial']

        # Paso 1: Calcular el saldo teórico
        # Sumamos todos los montos de los movimientos para esta sesión (ventas, ingresos, egresos)
        cursor.execute("SELECT SUM(monto) as total_movimientos FROM caja_movimientos WHERE id_sesion = %s AND tipo_movimiento <> 'APERTURA'", (id_sesion,))
        resultado_movimientos = cursor.fetchone()
        
        total_movimientos = resultado_movimientos['total_movimientos'] if resultado_movimientos['total_movimientos'] is not None else 0
        saldo_teorico = float(saldo_inicial_db) + float(total_movimientos)

        # Paso 2: Calcular la diferencia
        diferencia = saldo_final_contado - saldo_teorico

        # Paso 3: Actualizar el registro de la sesión en la tabla `caja_sesiones`
        query_update = """
            UPDATE caja_sesiones
            SET
                estado = 'CERRADA',
                fecha_cierre = %s,
                usuario_cierre = %s,
                saldo_final_contado = %s,
                saldo_teorico = %s,
                diferencia = %s
            WHERE id_sesion = %s
        """
        valores_update = (datetime.now(), usuario_cierre, saldo_final_contado, saldo_teorico, diferencia, id_sesion)
        
        # Reutilizamos el cursor, esta vez sin ser de diccionario si no es necesario
        cursor_update = conn.cursor()
        cursor_update.execute(query_update, valores_update)

        # Si todo va bien, guardamos los cambios
        conn.commit()

        # Paso 4 (Futuro): Llamar a la función de reporte
        # print(f"Llamando al generador de reportes para la sesión {id_sesion}...")
        # generar_reporte_cierre_a_sheets(id_sesion)

        return {
            "status": "success",
            "message": "Caja cerrada exitosamente.",
            "data": {
                "id_sesion": id_sesion,
                "diferencia": diferencia,
                "saldo_teorico": saldo_teorico,
                "saldo_final_contado": saldo_final_contado
            }
        }
    except Error as e:
        conn.rollback()
        return {"status": "error", "message": f"Error de base deatos al cerrar la caja: {e}"}
    finally:
        if conn.is_connected():
            cursor.close()
            # cursor_update.close() # Si creaste un segundo cursor, también hay que cerrarlo
            conn.close()