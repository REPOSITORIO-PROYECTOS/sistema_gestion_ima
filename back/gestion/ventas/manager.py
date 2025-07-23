# back/gestion/ventas/manager.py
# Lógica de negocio para consultar datos de ventas y generar boletas.

from sqlmodel import Session, select
from back.modelos import Venta, Tercero, VentaDetalle, Articulo

def obtener_datos_boleta(db: Session, id_venta: int) -> dict:
    """Recolecta y formatea todos los datos necesarios para un Comprobante de Venta."""
    venta = db.get(Venta, id_venta)
    if not venta:
        raise ValueError(f"Venta con ID {id_venta} no encontrada.")

    # Consultas explícitas para ser robustos
    cliente_obj = db.get(Tercero, venta.id_cliente) if venta.id_cliente else None
    detalles_db = db.exec(select(VentaDetalle).where(VentaDetalle.id_venta == id_venta)).all()

    # Ensamblaje de datos (como en la respuesta anterior)
    cliente_data = {
        "nombre_razon_social": "Consumidor Final", "identificacion_fiscal": None,
        "condicion_iva": "Consumidor Final", "direccion": None
    }
    if cliente_obj:
        cliente_data.update({
            "nombre_razon_social": cliente_obj.nombre_razon_social, "identificacion_fiscal": cliente_obj.identificacion_fiscal,
            "condicion_iva": cliente_obj.condicion_iva, "direccion": cliente_obj.direccion
        })

    items_data = []
    for detalle in detalles_db:
        articulo = db.get(Articulo, detalle.id_articulo)
        items_data.append({
            "cantidad": detalle.cantidad, "descripcion": articulo.descripcion if articulo else "N/A",
            "precio_unitario": detalle.precio_unitario, "subtotal": detalle.cantidad * detalle.precio_unitario
        })

    boleta_completa = {
        "id_venta": venta.id, "fecha_emision": venta.timestamp,
        "vendedor_razon_social": "IMA Swing Jugos S.A.", "vendedor_cuit": "30-12345678-9",
        "vendedor_direccion": "Calle Falsa 123, San Juan",
        "cliente": cliente_data, "items": items_data, "total_final": venta.total
    }
    return boleta_completa