# back/gestion/caja/registro_caja.py

from datetime import datetime
from mysql.connector import Error
from sqlmodel import Session, select
from datetime import datetime
from back.gestion.caja.cliente_publico import obtener_cliente_por_id
# Importa todos tus modelos. Asegúrate de que las rutas sean correctas.
from back.modelos import Venta, VentaDetalle, CajaMovimiento, Articulo 
from back.utils.mysql_handler import get_db_connection
# Importamos los otros "gestores" que contendrán la lógica específica
# Suponemos que existen estos módulos que también migraremos
# from back.gestion.clientes_manager import verificar_cliente_y_cta_cte
# from back.gestion.facturacion_manager import generar_comprobante
from back.utils.tablas_handler import TablasHandler

caller = TablasHandler()
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
    articulos_vendidos: list,  
    id_cliente: int,
    id_usuario: int,
    metodo_pago: str,
    total_venta: float
):
  
    try:

        nueva_venta = Venta(
            total=total_venta,
            id_cliente=id_cliente,
            id_usuario=id_usuario,
            id_caja_sesion=id_sesion_caja,
            timestamp=datetime.utcnow()
 
        )
        db.add(nueva_venta)

        for item_data in articulos_vendidos:
            id_articulo = item_data.get("id_articulo")
            cantidad_vendida = item_data.get("cantidad")

            if not id_articulo or not cantidad_vendida:
                raise ValueError("Cada artículo vendido debe tener 'id_articulo' y 'cantidad'.")

            articulo_db = db.exec(
                select(Articulo).where(Articulo.id == id_articulo).with_for_update()
            ).first()

            if not articulo_db:
                raise ValueError(f"El artículo con ID {id_articulo} no existe.")

      
            if not articulo_db.activo:
                raise ValueError(f"El artículo '{articulo_db.descripcion}' (ID: {id_articulo}) no está activo y no se puede vender.")


            if articulo_db.stock_actual < cantidad_vendida:
                raise ValueError(f"Stock insuficiente para '{articulo_db.descripcion}'. Disponible: {articulo_db.stock_actual}, Solicitado: {cantidad_vendida}")

    
            articulo_db.stock_actual -= cantidad_vendida
            
     
            detalle_venta = VentaDetalle(
                cantidad=cantidad_vendida,
                precio_unitario=articulo_db.precio_venta, 
                id_articulo=id_articulo,
                venta=nueva_venta 
            )
            db.add(detalle_venta)


        db.flush()

      
        concepto_venta = f"Venta #{nueva_venta.id} (Cliente ID: {id_cliente})"
        
        movimiento_caja = CajaMovimiento(
            id_caja_sesion=id_sesion_caja,
            id_usuario=id_usuario,
            tipo='VENTA',
            concepto=concepto_venta,
            monto=total_venta,
            metodo_pago=metodo_pago,
            id_venta=nueva_venta.id 
        )
        db.add(movimiento_caja)
        
        db.commit()

        
        db.refresh(nueva_venta)
        db.refresh(movimiento_caja)

        print(f"[REGISTRO_CAJA] Transacción completada. Venta ID: {nueva_venta.id}, Movimiento ID: {movimiento_caja.id}")


      
        print(f"[REGISTRO_CAJA] Transacción completada. Venta ID: {nueva_venta.id}, Movimiento ID: {movimiento_caja.id}")

# --- INICIA LA PARTE DE GUARDAR EN DRIVE (BLOQUE SEGURO) ---
        try:
            print("[DRIVE] Intentando registrar movimiento en Google Sheets...")
            cliente = obtener_cliente_por_id(id_cliente)

   
            if cliente:
                datos_para_sheets = {
                    "id_cliente": id_cliente,
                    "cliente": cliente.get("nombre-usuario", "No encontrado"),
                    "cuit": cliente.get("CUIT-CUIL", "N/A"),
                    "razon_social": cliente.get("Nombre de Contacto", "N/A"),
                    "Tipo_movimiento": "venta",
                    "descripcion": f"Venta de {len(articulos_vendidos)} artículos",
                    "monto": total_venta,
              
                }
                if not caller.registrar_movimiento(datos_para_sheets):
                    print("⚠️ [DRIVE] La función registrar_movimiento devolvió False.")

                if not caller.restar_stock(articulos_vendidos):
                    print("⚠️ [DRIVE] Ocurrió un error al intentar actualizar el stock en Google Sheets.")
            else:
                print(f"⚠️ [DRIVE] No se pudo encontrar el cliente con ID {id_cliente} en Google Sheets. No se registrará el movimiento en Drive.")

        except Exception as e_sheets:
            print(f"❌ [DRIVE] Ocurrió un error al intentar registrar en Google Sheets: {e_sheets}")

# --- FIN DE LA PARTE DE DRIVE --

        #----ACA TERMINA ESTA PARTE -----------------------------------

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