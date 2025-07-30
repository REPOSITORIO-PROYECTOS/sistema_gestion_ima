# back/gestion/caja/registro_caja.py

from datetime import datetime
from mysql.connector import Error
from sqlmodel import Session, select
from typing import List, Tuple, Dict, Any
from datetime import datetime
from back.gestion.caja.cliente_publico import obtener_cliente_por_id
# Importa todos tus modelos. Asegúrate de que las rutas sean correctas.
from back.modelos import Usuario, Venta, VentaDetalle, Articulo, CajaMovimiento, Tercero, CajaSesion
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
    total_venta: float,
    metodo_pago: str,
    articulos_vendidos: List[ArticuloVendido],
    id_cliente: int = None
) -> Tuple[Venta, CajaMovimiento]:
    """
    Registra una Venta y su Movimiento de Caja de forma ATÓMICA en la DB.
    Esta es la única fuente de la verdad. No habla con servicios externos.
    Devuelve los objetos creados para que el orquestador los use.
    """
    # Validación de stock y pertenencia de artículos a la empresa
    for item in articulos_vendidos:
        articulo_db = db.get(Articulo, item.id_articulo)
        if not articulo_db:
            raise ValueError(f"El artículo con ID {item.id_articulo} no existe.")
        if articulo_db.id_empresa != usuario_actual.id_empresa:
            raise ValueError(f"El artículo '{articulo_db.descripcion}' no pertenece a la empresa.")
        if articulo_db.stock_actual < item.cantidad:
            raise ValueError(f"Stock insuficiente para '{articulo_db.descripcion}'.")

    # Creación de objetos de la venta
    nueva_venta = Venta(
        total=total_venta,
        id_cliente=id_cliente,
        id_usuario=usuario_actual.id,
        id_caja_sesion=id_sesion_caja,
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

    movimiento_caja = CajaMovimiento(
        tipo=TipoMovimiento.VENTA.value,
        concepto=f"Venta ID: {nueva_venta.id}",
        monto=total_venta,
        metodo_pago=metodo_pago,
        id_caja_sesion=id_sesion_caja,
        id_usuario=usuario_actual.id,
        id_venta=nueva_venta.id,
    )
    db.add(movimiento_caja)
    db.flush()
    
    return nueva_venta, movimiento_caja


# =============================================================================
# === ESPECIALISTA DE SINCRONIZACIÓN CON GOOGLE SHEETS ===
# =============================================================================

def sincronizar_venta_con_sheets(
    venta: Venta,
    cliente: Tercero,
    resultado_afip: Dict[str, Any]
):
    """
    Función diseñada para ser ejecutada en segundo plano (Background Task).
    Contiene la lógica para comunicarse con Google Sheets.
    """
    print("--- [INICIO TAREA EN SEGUNDO PLANO: SINCRONIZAR CON SHEETS] ---")
    caller = TablasHandler()

    try:
        # Preparamos los datos para la hoja "MOVIMIENTOS"
        nro_comprobante_afip = resultado_afip.get("comprobante_numero", "") if resultado_afip.get("estado") == "EXITOSO" else "PENDIENTE"
        
        datos_para_sheets = {
            "id_cliente": venta.id_cliente,
            "cliente": cliente.nombre_razon_social if cliente else "Consumidor Final",
            "cuit": cliente.cuit if cliente else "N/A",
            "razon_social": cliente.nombre_razon_social if cliente else "N/A",
            "Tipo_movimiento": "venta",
            "nro_comprobante": nro_comprobante_afip,
            "descripcion": f"Venta de {len(venta.items)} artículos",
            "monto": venta.total,
        }
        
        # 1. Registrar el movimiento general
        if not caller.registrar_movimiento(datos_para_sheets):
            print("⚠️ [SHEETS] ADVERTENCIA: La función registrar_movimiento devolvió False.")
        else:
            print("✅ [SHEETS] Movimiento general de venta registrado con éxito.")
            
        # 2. Actualizar el stock de cada artículo
        # Convertimos los VentaDetalle a un formato que restar_stock entienda
        articulos_para_sheets = [{"id_articulo": detalle.id_articulo, "cantidad": detalle.cantidad} for detalle in venta.items]
        
        if not caller.restar_stock(articulos_para_sheets):
            print("⚠️ [SHEETS] ADVERTENCIA: Ocurrió un error al actualizar el stock en Google Sheets.")
        else:
            print("✅ [SHEETS] Stock actualizado con éxito.")

    except Exception as e:
        # Captura cualquier error de la integración y solo lo reporta.
        # No detiene la aplicación porque es una tarea en segundo plano.
        print(f"❌ [SHEETS] ERROR NO CRÍTICO: La sincronización falló. Razón: {e}")
    
    print("--- [FIN TAREA EN SEGUNDO PLANO] ---")


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