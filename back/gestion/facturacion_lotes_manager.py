# back/gestion/facturacion_lotes_manager.py
# VERSIÓN FINAL COMPLETA

import requests
from datetime import datetime
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from typing import List, Dict, Any
from jinja2 import Environment, FileSystemLoader

# --- Módulos del Proyecto ---
from back.modelos import ConfiguracionEmpresa, Usuario, Tercero, Venta, CajaMovimiento, VentaDetalle, Articulo, StockMovimiento
# Importamos el especialista de AFIP refactorizado
from back.gestion.facturacion_afip import generar_factura_para_venta, generar_nota_credito_para_venta
# Importamos los schemas que vamos a construir
from back.schemas.comprobante_schemas import EmisorData, ReceptorData, TransaccionData, ItemData
# Importamos la configuración para obtener las URLs y API Keys
from back.config import URL_BOVEDA, API_KEY_INTERNA
from back.gestion.reportes.generador_comprobantes import TEMPLATE_DIR, format_datetime

# Límite para Consumidor Final
LIMITE_CONSUMIDOR_FINAL = 200000.00

def facturar_lote_de_ventas(
    db: Session,
    usuario_actual: Usuario,
    ids_movimientos: List[int],
    id_cliente_final: int = None
) -> Dict[str, Any]:
    """
    Orquesta la facturación de un lote de ventas de CUALQUIER TIPO 
    (Recibos, Remitos, Presupuestos, o facturas fallidas), consolidándolos
    en una única y nueva factura fiscal.
    """
    print(f"--- [FACTURACIÓN UNIVERSAL DE LOTE] Iniciando para {len(ids_movimientos)} movimientos ---")
    
    # --- FASE 1: BÚSQUEDA Y VALIDACIONES SIMPLIFICADAS ---
    consulta = (
        select(CajaMovimiento)
        .where(CajaMovimiento.id.in_(ids_movimientos))
        .options(
            selectinload(CajaMovimiento.venta).selectinload(Venta.items).selectinload(VentaDetalle.articulo)
        )
    )
    movimientos = db.exec(consulta).all()

    if len(movimientos) != len(ids_movimientos):
        raise ValueError("Algunos de los movimientos seleccionados no fueron encontrados.")

    total_a_facturar = 0.0
    ventas_a_procesar: List[Venta] = []
    items_consolidados: List[ItemData] = []
    
    # --- LA NUEVA LÓGICA DE VALIDACIÓN ---
    # Ya no nos importa el tipo de comprobante, solo que sea una venta válida y no esté facturada.
    for mov in movimientos:
        if not mov.venta or mov.venta.facturada or mov.tipo != "VENTA" or mov.venta.id_empresa != usuario_actual.id_empresa:
            raise ValueError(f"El movimiento ID {mov.id} es inválido: puede que ya esté facturado, no sea una venta, o no pertenezca a su empresa.")
        
        total_a_facturar += mov.venta.total
        ventas_a_procesar.append(mov.venta)
        for detalle in mov.venta.items:
            # Consolidamos los ítems de todos los comprobantes, sin importar su origen
            items_consolidados.append(ItemData(
                cantidad=detalle.cantidad,
                descripcion=detalle.articulo.descripcion,
                precio_unitario=detalle.precio_unitario,
                subtotal=detalle.cantidad * detalle.precio_unitario
            ))
            
    # --- FASE 2: VALIDACIÓN DE CLIENTE (sin cambios) ---
    cliente_db = None
    if id_cliente_final:
        cliente_db = db.get(Tercero, id_cliente_final)
        if not cliente_db or cliente_db.id_empresa != usuario_actual.id_empresa:
            raise ValueError("El cliente final especificado es inválido.")
    elif total_a_facturar > LIMITE_CONSUMIDOR_FINAL:
        raise ValueError(f"El monto total (${total_a_facturar:,.2f}) supera el límite para Consumidor Final.")

    # --- FASE 3: PREPARACIÓN Y LLAMADA A AFIP (sin cambios) ---
    # (Tu lógica existente para obtener credenciales y datos del emisor/receptor es correcta)
    id_empresa_actual = usuario_actual.id_empresa
    config_empresa_db = db.query(ConfiguracionEmpresa).filter(ConfiguracionEmpresa.id_empresa == id_empresa_actual).first()
    if not config_empresa_db or not usuario_actual.empresa.cuit or not config_empresa_db.afip_punto_venta_predeterminado:
        raise ValueError(f"La configuración del emisor para la empresa ID {id_empresa_actual} es incompleta.")

    cuit_emisor = usuario_actual.empresa.cuit
    try:
        headers = {"X-API-KEY": API_KEY_INTERNA}
        respuesta_boveda = requests.get(f"{URL_BOVEDA}/secretos/{cuit_emisor}", headers=headers, timeout=10)
        respuesta_boveda.raise_for_status()
        credenciales = respuesta_boveda.json()
    except requests.RequestException as e:
        raise RuntimeError(f"No se pudo comunicar con la Bóveda de Secretos: {e}")

    emisor_data = EmisorData(
        cuit=cuit_emisor,
        razon_social=usuario_actual.empresa.nombre_legal,
        domicilio=config_empresa_db.direccion_negocio,
        punto_venta=config_empresa_db.afip_punto_venta_predeterminado,
        condicion_iva=config_empresa_db.afip_condicion_iva,
        afip_certificado=credenciales.get("certificado"),
        afip_clave_privada=credenciales.get("clave_privada")
    )

    receptor_data = ReceptorData.model_validate(cliente_db, from_attributes=True) if cliente_db else ReceptorData(
        nombre_razon_social="Consumidor Final", cuit_o_dni="0", domicilio="", condicion_iva="CONSUMIDOR_FINAL"
    )

    # Creamos la venta "virtual" que consolida el total.
    venta_consolidada_para_afip = Venta(total=total_a_facturar)

    # Llamamos al especialista que ya es transaccional.
    resultado_afip = generar_factura_para_venta(
        db=db,
        venta_a_facturar=venta_consolidada_para_afip,
        total=total_a_facturar,
        cliente_data=receptor_data,
        emisor_data=emisor_data,
        formato_comprobante="pdf",  # Facturas de lotes siempre en PDF
        tipo_solicitado=None
    )

    if not resultado_afip or not resultado_afip.get("cae"):
        raise RuntimeError("La facturación en AFIP falló. La operación ha sido cancelada.")

    # --- FASE 4: ACTUALIZACIÓN ATÓMICA DE LA BASE DE DATOS ---
    # SOBREESCRIBIMOS el estado de TODAS las ventas originales.
    for venta in ventas_a_procesar:
        venta.facturada = True
        venta.estado = "FACTURADA_EN_LOTE" # Un estado claro que indica que fue parte de una consolidación.
        venta.datos_factura = resultado_afip # Guardamos el mismo resultado en todas.
        db.add(venta)

    # El commit se hará en el router.
    return resultado_afip

def crear_nota_credito_para_anular(
    db: Session,
    usuario_actual: Usuario,
    id_movimiento_a_anular: int
) -> Dict[str, Any]:
    """
    Crea una Nota de Crédito para anular una factura/venta existente.
    """
    # 1. Búsqueda y Validación de la Venta Original (sin cambios)
    movimiento_original = db.get(CajaMovimiento, id_movimiento_a_anular)
    
    if not (movimiento_original and 
            movimiento_original.venta and 
            movimiento_original.venta.facturada and
            movimiento_original.venta.id_empresa == usuario_actual.id_empresa):
        raise ValueError("El movimiento a anular es inválido, no corresponde a una factura o no pertenece a su empresa.")
        
    if movimiento_original.venta.estado == "ANULADA":
        raise ValueError("Esta factura ya ha sido anulada previamente.")

    venta_original = movimiento_original.venta
    
    # 2. Preparación de datos del Emisor desde la base de datos (corregido)
    id_empresa_actual = usuario_actual.id_empresa
    config_empresa_db = db.query(ConfiguracionEmpresa).filter(ConfiguracionEmpresa.id_empresa == id_empresa_actual).first()
    
    if not config_empresa_db or not usuario_actual.empresa.cuit or not config_empresa_db.afip_punto_venta_predeterminado:
        raise ValueError(f"La configuración del emisor para la empresa ID {id_empresa_actual} es incompleta.")

    cuit_emisor = usuario_actual.empresa.cuit
    try:
        headers = {"X-API-KEY": API_KEY_INTERNA}
        respuesta_boveda = requests.get(f"{URL_BOVEDA}/secretos/{cuit_emisor}", headers=headers, timeout=10)
        respuesta_boveda.raise_for_status()
        credenciales = respuesta_boveda.json()
    except requests.RequestException as e:
        raise RuntimeError(f"No se pudo comunicar con la Bóveda de Secretos: {e}")

    emisor_data = EmisorData(
        cuit=cuit_emisor,
        razon_social=usuario_actual.empresa.nombre_legal,
        domicilio=config_empresa_db.direccion_negocio,
        punto_venta=config_empresa_db.afip_punto_venta_predeterminado,
        condicion_iva=config_empresa_db.afip_condicion_iva,
        afip_certificado=credenciales.get("certificado"),
        afip_clave_privada=credenciales.get("clave_privada")
    )
    
    cliente_db = db.get(Tercero, venta_original.id_cliente) if venta_original.id_cliente else None
    receptor_data = ReceptorData.model_validate(cliente_db, from_attributes=True) if cliente_db else ReceptorData(
        nombre_razon_social="Consumidor Final", cuit_o_dni="0", domicilio="", condicion_iva="CONSUMIDOR_FINAL"
    )
    
    # 3. Llamada al especialista de facturación para generar la NC (sin cambios)
    resultado_afip_nc = generar_nota_credito_para_venta(
        db=db,
        venta_a_anular=venta_original,
        total=venta_original.total,
        cliente_data=receptor_data,
        emisor_data=emisor_data,
        comprobante_asociado=venta_original.datos_factura
    )

    if not resultado_afip_nc or not resultado_afip_nc.get("cae"):
        raise RuntimeError("La generación de la Nota de Crédito en AFIP falló.")

    # --- INICIO DE LA CORRECCIÓN CLAVE ---

    # 4. Actualización de la Base de Datos
    # 🔴 CAMBIO: Marcar el movimiento original como "venta_anulada"
    movimiento_original.tipo = "venta_anulada"
    db.add(movimiento_original)

    # Creamos un movimiento de caja negativo para reflejar la devolución
    movimiento_caja_nc = CajaMovimiento(
        id_caja_sesion=movimiento_original.id_caja_sesion,
        id_usuario=usuario_actual.id,
        tipo="NOTA_CREDITO",
        concepto=f"Anulación Factura N° {venta_original.datos_factura.get('numero_comprobante', 'S/N')}",
        monto=-venta_original.total,
        metodo_pago=movimiento_original.metodo_pago,
        id_venta=venta_original.id
    )
    db.add(movimiento_caja_nc)
    
    # Marcamos la venta original como anulada
    venta_original.estado = "ANULADA"
    
    # Obtenemos el diccionario actual de datos_factura (si existe) o creamos uno nuevo
    datos_factura_actuales = venta_original.datos_factura or {}
    
    # Añadimos una nueva clave 'nota_credito' al diccionario con los datos de la NC
    datos_factura_actuales['nota_credito'] = resultado_afip_nc
    
    # Volvemos a asignar el diccionario modificado al campo JSON
    venta_original.datos_factura = datos_factura_actuales
    
    db.add(venta_original)

    # --- FIN DE LA CORRECCIÓN CLAVE ---

    # --- 5. Devolución de Stock por Nota de Crédito ---
    # Recorremos los items de la venta original para devolverlos al stock
    if venta_original.items:
        for item in venta_original.items:
            articulo = item.articulo
            if articulo and articulo.activo:
                stock_anterior = articulo.stock_actual
                articulo.stock_actual += item.cantidad
                stock_nuevo = articulo.stock_actual
                
                mov_stock = StockMovimiento(
                    tipo="NOTA_CREDITO",
                    cantidad=item.cantidad,
                    stock_anterior=stock_anterior,
                    stock_nuevo=stock_nuevo,
                    id_articulo=articulo.id,
                    id_usuario=usuario_actual.id,
                    id_venta_detalle=item.id,
                    id_empresa=usuario_actual.id_empresa
                )
                db.add(mov_stock)
                db.add(articulo)

    # El commit se hará en el router que llama a esta función.
    return resultado_afip_nc


def anular_comprobante_no_fiscal(
    db: Session,
    usuario_actual: Usuario,
    id_movimiento_a_anular: int
) -> Dict[str, Any]:
    """
    Anula un comprobante no fiscal (ej. recibo/remito/presupuesto), revierte stock
    y registra un movimiento de caja negativo. No invoca AFIP.
    """

    movimiento_original = db.get(CajaMovimiento, id_movimiento_a_anular)

    if not (movimiento_original and movimiento_original.venta and movimiento_original.venta.id_empresa == usuario_actual.id_empresa):
        raise ValueError("El movimiento a anular es inválido o no pertenece a su empresa.")

    venta_original = movimiento_original.venta

    if venta_original.facturada:
        raise ValueError("La venta es fiscal. Use la anulación con Nota de Crédito.")

    if venta_original.estado == "ANULADA":
        raise ValueError("Esta venta ya fue anulada previamente.")

    # 🔴 CAMBIO: Marcar el movimiento original como "venta_anulada"
    movimiento_original.tipo = "venta_anulada"
    db.add(movimiento_original)

    # Movimiento de caja negativo para reflejar la devolución de dinero
    mov_nc = CajaMovimiento(
        id_caja_sesion=movimiento_original.id_caja_sesion,
        id_usuario=usuario_actual.id,
        tipo="ANULACION_COMPROBANTE",
        concepto=f"Anulación comprobante no fiscal ID mov {movimiento_original.id}",
        monto=-venta_original.total,
        metodo_pago=movimiento_original.metodo_pago,
        id_venta=venta_original.id
    )
    db.add(mov_nc)

    # Marcar venta como anulada y guardar rastro
    venta_original.estado = "ANULADA"
    datos_factura = venta_original.datos_factura or {}
    datos_factura["anulado_no_fiscal"] = {
        "motivo": "anulacion_comprobante",
        "timestamp": datetime.utcnow().isoformat()
    }
    venta_original.datos_factura = datos_factura
    db.add(venta_original)

    # Devolver stock
    if venta_original.items:
        for item in venta_original.items:
            articulo = item.articulo
            if articulo and articulo.activo:
                stock_anterior = articulo.stock_actual
                articulo.stock_actual += item.cantidad
                stock_nuevo = articulo.stock_actual

                mov_stock = StockMovimiento(
                    tipo="ANULACION_COMPROBANTE",
                    cantidad=item.cantidad,
                    stock_anterior=stock_anterior,
                    stock_nuevo=stock_nuevo,
                    id_articulo=articulo.id,
                    id_usuario=usuario_actual.id,
                    id_venta_detalle=item.id,
                    id_empresa=usuario_actual.id_empresa
                )
                db.add(mov_stock)
                db.add(articulo)

        ticket_html = _render_ticket_anulacion_no_fiscal(
            db=db,
            empresa=usuario_actual.empresa,
            venta=venta_original,
            movimiento=mov_nc
        )

        return {
                "status": "success",
                "mensaje": "Comprobante no fiscal anulado y stock revertido.",
                "venta_id": venta_original.id,
                "movimiento_anulacion_id": mov_nc.id,
                "ticket_html": ticket_html
        }


def _render_ticket_anulacion_no_fiscal(
    db: Session,
    empresa: Usuario.empresa.__class__,
    venta: Venta,
    movimiento: CajaMovimiento
) -> str:
    """Renderiza la anulación usando la plantilla de ticket existente (recibo/remito/presupuesto)."""

    def _resolver_template(tipo_comprobante: str) -> str:
        tipo = (tipo_comprobante or "").lower()
        if tipo in {"remito", "presupuesto", "recibo"}:
            return tipo
        if tipo == "factura" or tipo == "ticket":
            return "comprobante"
        return "recibo"

    # Buscar configuración de la empresa para completar datos visuales
    config_empresa = getattr(empresa, "configuracion", None)
    if not config_empresa and getattr(empresa, "id", None):
        config_empresa = db.query(ConfiguracionEmpresa).filter(ConfiguracionEmpresa.id_empresa == empresa.id).first()

    emisor_ctx = {
        "razon_social": getattr(config_empresa, "nombre_negocio", None) or getattr(empresa, "nombre_legal", None) or getattr(empresa, "nombre_fantasia", None) or "Empresa",
        "cuit": getattr(empresa, "cuit", "") or "",
        "domicilio": getattr(config_empresa, "direccion_negocio", None) or "",
        "condicion_iva": getattr(config_empresa, "afip_condicion_iva", None) or "",
        "punto_venta": getattr(config_empresa, "afip_punto_venta_predeterminado", None) or 0,
        "ingresos_brutos": getattr(config_empresa, "ingresos_brutos", None) or "",
        "inicio_actividades": getattr(config_empresa, "inicio_actividades", None) or "",
        "logo_url": None,
    }

    cliente = getattr(venta, "cliente", None)
    receptor_ctx = {
        "nombre_razon_social": getattr(cliente, "nombre_razon_social", None) or getattr(cliente, "nombre", None) or "Consumidor Final",
        "cuit_o_dni": getattr(cliente, "cuit", None) or getattr(cliente, "dni", None) or "0",
        "domicilio": getattr(cliente, "domicilio", None) or "",
        "condicion_iva": getattr(cliente, "condicion_iva", None) or "Consumidor Final",
    }

    items = []
    for item in venta.items or []:
        descripcion = getattr(getattr(item, "articulo", None), "descripcion", None) or "Item"
        items.append({
            "cantidad": item.cantidad,
            "descripcion": descripcion,
            "precio_unitario": item.precio_unitario,
            "subtotal": item.cantidad * item.precio_unitario,
            "descuento_especifico": getattr(item, "descuento_aplicado", 0.0) or 0.0,
            "descuento_especifico_por": 0.0,
        })

    fecha_emision = movimiento.timestamp or datetime.utcnow()

    transaccion_ctx = {
        "items": items,
        "total": venta.total,
        "subtotal": None,
        "descuento_general": getattr(venta, "descuento_total", 0.0) or 0.0,
        "descuento_general_por": 0.0,
        "observaciones": f"ANULACIÓN de comprobante - Mov {movimiento.id} - {fecha_emision.strftime('%d/%m/%Y %H:%M')}"
    }

    afip_ctx = {
        "tipo_comprobante_nombre": "ANULACION",
        "tipo_comprobante_letra": "X",
        "numero_comprobante": (venta.datos_factura or {}).get("numero_comprobante", 0) if venta.datos_factura else 0,
        "tipo_afip": None,
        "qr_base64": None,
    }

    contexto = {
        "emisor": emisor_ctx,
        "receptor": receptor_ctx,
        "transaccion": transaccion_ctx,
        "fecha_emision": fecha_emision,
        "afip": afip_ctx,
    }

    template_name = _resolver_template(getattr(venta, "tipo_comprobante_solicitado", None))

    try:
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        env.filters["date"] = format_datetime
        template = env.get_template(f"ticket/{template_name}.html")
        return template.render(contexto)
    except Exception:
        # Fallback liviano para no bloquear la anulación en caso de error de template
        fecha_str = format_datetime(fecha_emision)
        line_items = "".join([
            f"<tr><td>{it['descripcion']}</td><td style='text-align:right'>{it['cantidad']}</td><td style='text-align:right'>{it['precio_unitario']:.2f}</td><td style='text-align:right'>{it['subtotal']:.2f}</td></tr>"
            for it in items
        ])
        return f"""
        <html><body>
        <h3>{emisor_ctx['razon_social']}</h3>
        <div>ANULACIÓN DE COMPROBANTE</div>
        <div>Fecha: {fecha_str}</div>
        <table>{line_items}</table>
        <div>Total: ${venta.total:.2f}</div>
        <div>Movimiento: {movimiento.id}</div>
        </body></html>
        """
