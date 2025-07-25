# back/gestion/caja/registro_caja.py

from datetime import datetime
from mysql.connector import Error
from sqlmodel import Session, select
from datetime import datetime
from back.gestion.caja.cliente_publico import obtener_cliente_por_id
# Importa todos tus modelos. Asegúrate de que las rutas sean correctas.
from back.modelos import Tercero, Venta, VentaDetalle, CajaMovimiento, Articulo 
from back.utils.mysql_handler import get_db_connection
from back.utils.tablas_handler import TablasHandler
from back.gestion.facturacion_afip import generar_factura_para_venta

caller = TablasHandler()
#ACA TENGO QUE REGISTRAR CUANDO ENTRA Y CUANDO SALE PLATA, MODIFICA LA TABLA MOVIMIENTOS
  


from back.modelos import (
    Venta,
    VentaDetalle,
    CajaMovimiento,
    Articulo,
    Tercero
)

def registrar_ingreso_egreso(
    db: Session,
    id_sesion_caja: int,
    concepto: str,
    monto: float,
    tipo: str,
    id_usuario: int
) -> CajaMovimiento:
    """
    Registra un ingreso o egreso simple en la caja usando SQLModel.
    'tipo' debe ser 'INGRESO' o 'EGRESO'. El monto siempre es positivo.
    """
    print(f"\n--- [TRACE: REGISTRAR MOVIMIENTO] ---")
    print(f"1. Solicitud de {tipo} para Sesión ID: {id_sesion_caja}, Monto: {monto}")

    if tipo.upper() not in ['INGRESO', 'EGRESO']:
        raise ValueError("Tipo de movimiento no válido. Debe ser 'INGRESO' o 'EGRESO'.")
    
    if monto <= 0:
        raise ValueError("El monto del movimiento debe ser un número positivo.")

    # Creamos el objeto del movimiento directamente con SQLModel
    nuevo_movimiento = CajaMovimiento(
        id_caja_sesion=id_sesion_caja,
        id_usuario=id_usuario,
        tipo=tipo.upper(),
        concepto=concepto,
        monto=monto,  # El monto siempre se guarda en positivo
        metodo_pago="EFECTIVO" # Asumimos efectivo para movimientos simples
    )

    try:
        db.add(nuevo_movimiento)
        db.commit()
        db.refresh(nuevo_movimiento)
        print(f"   -> ÉXITO. Movimiento registrado con ID: {nuevo_movimiento.id}")
        print("--- [FIN TRACE] ---\n")

        try:

            datos_para_sheets = {
                    "Tipo_movimiento": "egreso",
                    "descripcion": concepto,
                    "monto": monto,
            }

            if not caller.registrar_movimiento(datos_para_sheets):
                print("⚠️ [DRIVE] La función registrar_movimiento devolvió False.")
           
            else:
               print(f"⚠️ [DRIVE] No se pudo encontrar el cliente con ID . No se registrará el movimiento en Drive.")

        except Exception as e_sheets:
            print(f"❌ [DRIVE] Ocurrió un error al intentar registrar en Google Sheets: {e_sheets}")
        



        return nuevo_movimiento
    except Exception as e:
        print(f"   -> ERROR de BD al registrar el movimiento: {e}")
        db.rollback()
        # Relanzamos la excepción para que el router la capture
        raise RuntimeError(f"Error de base de datos al registrar el movimiento: {e}")



def registrar_venta(
    db: Session,
    id_sesion_caja: int,
    articulos_vendidos: list,  
    id_cliente: int,
    id_usuario: int,
    metodo_pago: str,
    total_venta: float
) -> dict: # Añadimos un tipo de retorno para ser más claros
  
    try:
        # ====================================================================
        # === INICIO DE TU LÓGICA ORIGINAL (SIN CAMBIOS) ===
        # ====================================================================

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
        
        # --- COMMIT PRINCIPAL ---
        # Guardamos la venta, los detalles, el stock y el movimiento de caja.
        db.commit()

        db.refresh(nueva_venta)
        db.refresh(movimiento_caja)

        print(f"[REGISTRO_CAJA] Transacción completada. Venta ID: {nueva_venta.id}, Movimiento ID: {movimiento_caja.id}")

        # ====================================================================
        # === FIN DE TU LÓGICA ORIGINAL ===
        # ====================================================================

        # ====================================================================
        # === NUEVO BLOQUE DE INTEGRACIÓN CON FACTURACIÓN AFIP ===
        # ====================================================================
        resultado_factura = None
        try:
            print("[AFIP] Intentando generar factura para la venta...")
            cliente = db.get(Tercero, id_cliente) if id_cliente else None
            

            
            print(f"[AFIP] Factura generada con éxito. CAE: {resultado_factura.get('cae')}")
        
        except (ValueError, RuntimeError) as e_factura:
            # La venta se guardó, pero la facturación falló. Imprimimos una advertencia clara.
            # No revertimos la venta, solo informamos del fallo de facturación.
            print(f"⚠️ [AFIP] ADVERTENCIA: La venta {nueva_venta.id} se registró, pero NO se pudo facturar. Razón: {e_factura}")
            # Guardamos el error para devolverlo en la respuesta final
            resultado_factura = {"error": str(e_factura)}

        # ====================================================================
        # === FIN DEL BLOQUE DE FACTURACIÓN ===
        # ====================================================================

        # ====================================================================
        # === TU LÓGICA DE GOOGLE SHEETS (SIN CAMBIOS) ===
        # ====================================================================
        try:
            print("[DRIVE] Intentando registrar movimiento en Google Sheets...")
            cliente_sheets_data = obtener_cliente_por_id(id_cliente) # Asumo que esta función devuelve un dict

            if cliente_sheets_data:
                datos_para_sheets = {
                    "id_cliente": id_cliente,
                    "cliente": cliente_sheets_data.get("nombre-usuario", "No encontrado"),
                    "cuit": cliente_sheets_data.get("CUIT-CUIL", "N/A"),
                    "razon_social": cliente_sheets_data.get("Nombre de Contacto", "N/A"),
                    "Tipo_movimiento": "venta",
                    "descripcion": f"Venta de {len(articulos_vendidos)} artículos",
                    "monto": total_venta,
                }
                if not caller.registrar_movimiento(datos_para_sheets):
                    print("⚠️ [DRIVE] La función registrar_movimiento devolvió False.")
                if not caller.restar_stock(articulos_vendidos):
                    print("⚠️ [DRIVE] Ocurrió un error al intentar actualizar el stock en Google Sheets.")
            else:
                print(f"⚠️ [DRIVE] No se pudo encontrar el cliente con ID {id_cliente}. No se registrará el movimiento en Drive.")

        except Exception as e_sheets:
            print(f"❌ [DRIVE] Ocurrió un error al intentar registrar en Google Sheets: {e_sheets}")
        
        # ====================================================================
        # === FIN DE LA LÓGICA DE GOOGLE SHEETS ===
        # ====================================================================

        # Devolvemos una respuesta completa con el ID de la venta y el resultado de la facturación
        return {
            "id_venta": nueva_venta.id,
            "id_movimiento_caja": movimiento_caja.id,
            "factura_afip": resultado_factura
        }

    except Exception as e:
        # Si algo falla en la lógica principal de la venta, revertimos todo.
        print(f"❌ [REGISTRO_CAJA] ERROR FATAL, revirtiendo transacción. Detalle: {e}")
        db.rollback()
        # Re-lanzamos la excepción para que el endpoint la capture y devuelva un error
        raise e



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