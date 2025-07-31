# back/gestion/caja/registro_caja.py

from datetime import datetime
from mysql.connector import Error
from sqlmodel import Session, select
from typing import List, Tuple, Dict, Any
from datetime import datetime
from back.gestion.caja.cliente_publico import obtener_cliente_por_id
# Importa todos tus modelos. Asegúrate de que las rutas sean correctas.
from back.modelos import Usuario, Venta, VentaDetalle, Articulo, CajaMovimiento, Tercero, CajaSesion, ConfiguracionEmpresa
from back.schemas.caja_schemas import ArticuloVendido, RegistrarVentaRequest, TipoMovimiento
from back.utils.mysql_handler import get_db_connection
from back.utils.tablas_handler import TablasHandler
from back.gestion.facturacion_afip import generar_factura_para_venta

caller = TablasHandler()
#ACA TENGO QUE REGISTRAR CUANDO ENTRA Y CUANDO SALE PLATA, MODIFICA LA TABLA MOVIMIENTOS

# =============================================================================
# === ESPECIALISTA DE BASE DE DATOS ===
# =============================================================================

def registrar_venta_y_movimiento_caja(
    db: Session,
    usuario_actual: Usuario,
    id_sesion_caja: int,
    total_venta: float, # Este es el total de los productos ANTES de recargos
    metodo_pago: str,
    articulos_vendidos: List[ArticuloVendido],
    id_cliente: int = None
) -> Tuple[Venta, CajaMovimiento]:
    """
    Registra una Venta, aplica recargos dinámicos según la configuración
    de la empresa, y sincroniza el resultado final con Google Sheets.
    """
    # --- 1. VALIDACIÓN DE ARTÍCULOS Y STOCK (Sin Cambios) ---
    for item in articulos_vendidos:
        articulo_db = db.get(Articulo, item.id_articulo)
        if not articulo_db:
            raise ValueError(f"El artículo con ID {item.id_articulo} no existe.")
        if articulo_db.id_empresa != usuario_actual.id_empresa:
            raise ValueError(f"El artículo '{articulo_db.descripcion}' no pertenece a la empresa.")
        if articulo_db.stock_actual < item.cantidad:
            raise ValueError(f"Stock insuficiente para '{articulo_db.descripcion}'.")

    # --- 2. LÓGICA DE RECARGO DINÁMICO ---
    total_final_con_recargo = total_venta
    monto_recargo = 0.0
    concepto_recargo = ""
    metodo_pago_upper = metodo_pago.upper()

    config_empresa = db.get(ConfiguracionEmpresa, usuario_actual.id_empresa)
    if not config_empresa:
        raise RuntimeError("No se encontró la configuración para la empresa.")

    porcentaje_recargo = 0.0
    if metodo_pago_upper == "TRANSFERENCIA":
        porcentaje_recargo = config_empresa.recargo_transferencia
        concepto_recargo = config_empresa.concepto_recargo_transferencia
    elif metodo_pago_upper == "BANCARIO":
        porcentaje_recargo = config_empresa.recargo_banco
        concepto_recargo = config_empresa.concepto_recargo_banco
    
    if porcentaje_recargo > 0:
        monto_recargo = total_venta * (porcentaje_recargo / 100.0)
        total_final_con_recargo = total_venta + monto_recargo
        print(f"Recargo del {porcentaje_recargo}% aplicado. Monto: {monto_recargo:.2f}. Total final: {total_final_con_recargo:.2f}")

    # --- 3. CREACIÓN DE OBJETOS PARA LA BASE DE DATOS ---
    nueva_venta = Venta(
        total=total_final_con_recargo, # <-- Usamos el total CON recargo
        id_cliente=id_cliente,
        id_usuario=usuario_actual.id,
        id_caja_sesion=id_sesion_caja,
        id_empresa=usuario_actual.id_empresa
    )
    db.add(nueva_venta)
    db.flush()

    for item in articulos_vendidos:
        articulo_a_actualizar = db.get(Articulo, item.id_articulo)
        detalle = VentaDetalle(
            id_venta=nueva_venta.id,
            id_articulo=item.id_articulo,
            cantidad=item.cantidad,
            precio_unitario=item.precio_unitario
        )
        db.add(detalle)
        articulo_a_actualizar.stock_actual -= item.cantidad
        db.add(articulo_a_actualizar)

    movimiento_principal = CajaMovimiento(
        tipo=TipoMovimiento.VENTA.value,
        concepto=f"Venta ID: {nueva_venta.id}",
        monto=total_final_con_recargo, # <-- Usamos el total CON recargo
        metodo_pago=metodo_pago,
        id_caja_sesion=id_sesion_caja,
        id_usuario=usuario_actual.id,
        id_venta=nueva_venta.id,
    )
    db.add(movimiento_principal)

    if monto_recargo > 0:
        movimiento_recargo = CajaMovimiento(
            tipo=TipoMovimiento.INGRESO.value,
            concepto=concepto_recargo,
            monto=monto_recargo,
            metodo_pago=metodo_pago,
            id_caja_sesion=id_sesion_caja,
            id_usuario=usuario_actual.id,
            id_venta=nueva_venta.id
        )
        db.add(movimiento_recargo)
        
    db.flush()

    # --- 4. SINCRONIZACIÓN CON GOOGLE SHEETS (TU LÓGICA ORIGINAL) ---
    # Esta parte ahora se ejecuta DENTRO de la misma función, antes del commit.
    # El router la convertirá en una tarea en segundo plano.
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

    return nueva_venta, movimiento_principal



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



def registrar_ingreso_egreso(
    db: Session,
    id_sesion_caja: int,
    concepto: str,
    monto: float,
    tipo: str,
    id_usuario: int,
    facturado: bool,
    fecha_hora: datetime
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
        metodo_pago="EFECTIVO", # Asumimos efectivo para movimientos simples
        facturado=facturado,
        fecha_hora=fecha_hora,
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

