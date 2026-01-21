from typing import List, Optional
from sqlmodel import Session, select
from back.modelos import ConsumoMesa, ConsumoMesaDetalle, ConfiguracionEmpresa, Articulo
from back.schemas.comprobante_schemas import GenerarComprobanteRequest, EmisorData, ReceptorData, TransaccionData, ItemData

def _obtener_emisor(db: Session, id_empresa: int) -> EmisorData:
    conf = db.exec(select(ConfiguracionEmpresa).where(ConfiguracionEmpresa.id_empresa == id_empresa)).first()
    cuit = conf.cuit if conf and conf.cuit else ""
    pv = conf.afip_punto_venta_predeterminado if conf and conf.afip_punto_venta_predeterminado else 1
    aclar = conf.aclaraciones_legales if conf and conf.aclaraciones_legales else {}
    return EmisorData(cuit=cuit, razon_social=None, domicilio=None, punto_venta=pv, condicion_iva=None, aclaraciones_legales=aclar)

def construir_request_ticket_mesa(db: Session, consumo: ConsumoMesa) -> GenerarComprobanteRequest:
    items: List[ItemData] = []
    for d in consumo.detalles:
        art: Optional[Articulo] = d.articulo
        desc = art.descripcion if art else "Artículo"
        subtotal = d.cantidad * d.precio_unitario
        items.append(ItemData(cantidad=d.cantidad, descripcion=desc, precio_unitario=d.precio_unitario, subtotal=subtotal))
    trans = TransaccionData(items=items, total=consumo.total, observaciones=None)
    emisor = _obtener_emisor(db, consumo.id_empresa)
    receptor = ReceptorData()
    return GenerarComprobanteRequest(tipo="ticket_mesa", formato="ticket", emisor=emisor, receptor=receptor, transaccion=trans)

def construir_request_comanda(db: Session, detalles: List[ConsumoMesaDetalle], id_empresa: int) -> GenerarComprobanteRequest:
    items: List[ItemData] = []
    for d in detalles:
        art: Optional[Articulo] = d.articulo
        desc = art.descripcion if art else "Item"
        items.append(ItemData(cantidad=d.cantidad, descripcion=desc, precio_unitario=0.0, subtotal=0.0))
    trans = TransaccionData(items=items, total=0.0, observaciones=None)
    emisor = _obtener_emisor(db, id_empresa)
    receptor = ReceptorData()
    return GenerarComprobanteRequest(tipo="comanda", formato="ticket", emisor=emisor, receptor=receptor, transaccion=trans)
