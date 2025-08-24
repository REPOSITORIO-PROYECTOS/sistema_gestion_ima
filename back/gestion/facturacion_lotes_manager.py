# back/gestion/facturacion_lotes_manager.py
# VERSIÓN FINAL COMPLETA

import requests
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from typing import List, Dict, Any

# --- Módulos del Proyecto ---
from back.modelos import ConfiguracionEmpresa, Usuario, Tercero, Venta, CajaMovimiento, VentaDetalle, Articulo
# Importamos el especialista de AFIP refactorizado
from back.gestion.facturacion_afip import generar_factura_para_venta, generar_nota_credito_para_venta
# Importamos los schemas que vamos a construir
from back.schemas.comprobante_schemas import EmisorData, ReceptorData, TransaccionData, ItemData
# Importamos la configuración para obtener las URLs y API Keys
from back.config import URL_BOVEDA, API_KEY_INTERNA

# Límite para Consumidor Final
LIMITE_CONSUMIDOR_FINAL = 200000.00

def facturar_lote_de_ventas(
    db: Session,
    usuario_actual: Usuario,
    ids_movimientos: List[int],
    id_cliente_final: int = None
) -> Dict[str, Any]:
    """
    Orquesta la facturación de un lote de ventas:
    1. Valida los movimientos y consolida los datos.
    2. Obtiene credenciales de la Bóveda.
    3. Llama al especialista de facturación.
    4. Actualiza la base de datos de forma atómica.
    """
    # --- FASE 1: BÚSQUEDA Y VALIDACIONES ---
    # Usamos selectinload para cargar eficientemente todas las relaciones que necesitaremos
    consulta = (
        select(CajaMovimiento)
        .where(CajaMovimiento.id.in_(ids_movimientos))
        .options(
            selectinload(CajaMovimiento.venta).selectinload(Venta.items).selectinload(VentaDetalle.articulo)
        )
    )
    movimientos = db.exec(consulta).all()

    if len(movimientos) != len(ids_movimientos):
        raise ValueError("Algunos IDs de movimientos no fueron encontrados.")

    total_a_facturar = 0.0
    ventas_a_actualizar: List[Venta] = []
    items_consolidados: List[ItemData] = []
    
    for mov in movimientos:
        if not mov.venta or mov.venta.facturada or mov.tipo != "VENTA" or mov.venta.id_empresa != usuario_actual.id_empresa:
            raise ValueError(f"El movimiento ID {mov.id} es inválido, ya fue facturado o no pertenece a tu empresa.")
        
        total_a_facturar += mov.venta.total
        ventas_a_actualizar.append(mov.venta)
        for detalle in mov.venta.items:
            items_consolidados.append(ItemData(
                cantidad=detalle.cantidad,
                descripcion=detalle.articulo.descripcion,
                precio_unitario=detalle.precio_unitario,
                subtotal=detalle.cantidad * detalle.precio_unitario
            ))
            
    # --- FASE 2: VALIDACIÓN DE CLIENTE Y LÍMITES ---
    cliente_db = None
    if id_cliente_final:
        cliente_db = db.get(Tercero, id_cliente_final)
        if not cliente_db or cliente_db.id_empresa != usuario_actual.id_empresa:
            raise ValueError("El cliente final especificado es inválido.")
    elif total_a_facturar > LIMITE_CONSUMIDOR_FINAL:
        raise ValueError(f"El monto total (${total_a_facturar:,.2f}) supera el límite para Consumidor Final.")

    # --- FASE 3: OBTENCIÓN DE CREDENCIALES Y PREPARACIÓN DE DATOS ---
    # 3.1. Obtener credenciales de la Bóveda de Secretos
    try:
        cuit_emisor = usuario_actual.empresa.cuit
        headers = {"X-API-KEY": API_KEY_INTERNA}
        respuesta_boveda = requests.get(f"{URL_BOVEDA}/secretos/{cuit_emisor}", headers=headers, timeout=10)
        respuesta_boveda.raise_for_status()
        credenciales = respuesta_boveda.json()
    except requests.RequestException as e:
        raise RuntimeError(f"No se pudo comunicar con la Bóveda de Secretos: {e}")

    # 3.2. Construir los schemas para el especialista de facturación
    emisor_data = EmisorData(
        cuit=cuit_emisor,
        razon_social=usuario_actual.empresa.nombre_legal,
        domicilio="Domicilio de la Empresa", # Este dato debería estar en el modelo Empresa/ConfiguracionEmpresa
        punto_venta=1, # Este dato debería venir de ConfiguracionEmpresa
        condicion_iva="Monotributo", # Este dato debería venir de ConfiguracionEmpresa
        afip_certificado=credenciales.get("certificado"),
        afip_clave_privada=credenciales.get("clave_privada")
    )
    
    receptor_data = ReceptorData.model_validate(cliente_db) if cliente_db else ReceptorData(
        nombre_razon_social="Consumidor Final",
        cuit_o_dni="0",
        domicilio="",
        condicion_iva="Consumidor Final"
    )
    

    venta_consolidada_para_afip = Venta(total=total_a_facturar)

    # 4. Llamar al especialista con la firma CORRECTA
    resultado_afip = generar_factura_para_venta(
        db=db, # Le pasamos la sesión de la base de datos
        venta_a_facturar=venta_consolidada_para_afip, # Le pasamos la venta "virtual"
        total=total_a_facturar,
        cliente_data=receptor_data,
        emisor_data=emisor_data
    )

    if not resultado_afip or not resultado_afip.get("cae"):
        raise RuntimeError("La facturación en AFIP falló. La operación ha sido cancelada.")

    # 5. ACTUALIZACIÓN DE LA BASE DE DATOS
    # Ahora que tenemos el resultado de AFIP, lo aplicamos a TODAS las ventas del lote.
    for venta in ventas_a_actualizar:
        venta.facturada = True
        venta.datos_factura = resultado_afip # Guardamos el mismo resultado en todas las ventas
        db.add(venta)

    # El commit se hará en el router, después de que esta función termine exitosamente.
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

    # El commit se hará en el router que llama a esta función.
    return resultado_afip_nc