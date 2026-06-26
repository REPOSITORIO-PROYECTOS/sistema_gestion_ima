# back/gestion/caja/registro_caja.py

from datetime import datetime
from requests import session
from sqlmodel import Session, select
from typing import List, Tuple, Dict, Any
from datetime import datetime
from back.gestion.caja.cliente_publico import obtener_cliente_por_id
# Importa todos tus modelos. Asegúrate de que las rutas sean correctas.
from back.modelos import Usuario, Venta, VentaDetalle, Articulo, CajaMovimiento, Tercero, CajaSesion, ConfiguracionEmpresa
from back.schemas.caja_schemas import ArticuloVendido, RegistrarVentaRequest, TipoMovimiento, PagoMultiple
from back.gestion.contabilidad.clientes_contabilidad import manager as clientes_manager
from back.gestion.sync_nube_queue_manager import (
    encolar_sync_nube_pendiente,
    OPERACION_REGISTRAR_MOVIMIENTO,
    OPERACION_RESTAR_STOCK,
)

#ACA TENGO QUE REGISTRAR CUANDO ENTRA Y CUANDO SALE PLATA, MODIFICA LA TABLA MOVIMIENTOS


def _agregar_evento_sync_nube(
    db: Session,
    operacion: str,
    estado: str,
    mensaje: str,
    requiere_reintento: bool = False,
) -> None:
    """Registra eventos de sincronización externa para exponerlos en la respuesta API."""
    eventos = db.info.setdefault("protocolo_sync_nube", [])
    eventos.append(
        {
            "operacion": operacion,
            "estado": estado,
            "mensaje": mensaje,
            "requiere_reintento": requiere_reintento,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )

def _sincroniza_con_sheets(db: Session, id_empresa: int) -> bool:
    config = db.get(ConfiguracionEmpresa, id_empresa)
    if config and getattr(config, "modo_especial_habilitado", False):
        return False
    return True


def _encolar_movimiento_pendiente(
    db: Session,
    id_empresa: int,
    datos_para_sheets: Dict[str, Any],
    id_venta: int | None = None,
) -> None:
    if not _sincroniza_con_sheets(db, id_empresa):
        return
    encolar_sync_nube_pendiente(
        db=db,
        id_empresa=id_empresa,
        id_venta=id_venta,
        operacion=OPERACION_REGISTRAR_MOVIMIENTO,
        payload=datos_para_sheets,
    )


def _construir_datos_movimiento_manual_sheets(
    *,
    usuario_actual: Usuario,
    movimiento: CajaMovimiento,
    tipo: str,
    concepto: str,
    monto: float,
    metodo_pago: str,
) -> Dict[str, Any]:
    metodo = (metodo_pago or "EFECTIVO").upper()
    tipo_upper = tipo.upper()
    return {
        "id_cliente": "0",
        "id_ingresos": str(movimiento.id),
        "id_repartidor": "",
        "Repartidor": usuario_actual.nombre_usuario,
        "cliente": "cliente final",
        "cuit": "-",
        "razon_social": "-",
        "Tipo_movimiento": f"[{tipo_upper}] en {metodo}",
        "nro_comprobante": "",
        "descripcion": concepto,
        "monto": monto,
        "foto_comprobante": "",
        "observaciones": "",
    }

def _encolar_stock_pendiente(
    db: Session,
    id_empresa: int,
    id_venta: int,
    articulos_vendidos: List[ArticuloVendido],
) -> None:
    if not _sincroniza_con_sheets(db, id_empresa):
        return
    payload = {
        "articulos_vendidos": [
            {
                "id_articulo": item.id_articulo,
                "cantidad": item.cantidad,
                "precio_unitario": item.precio_unitario,
            }
            for item in articulos_vendidos
        ]
    }
    encolar_sync_nube_pendiente(
        db=db,
        id_empresa=id_empresa,
        id_venta=id_venta,
        operacion=OPERACION_RESTAR_STOCK,
        payload=payload,
    )


def _construir_descripcion_venta_sheets(
    db: Session,
    articulos_vendidos: List[ArticuloVendido],
) -> str:
    partes: List[str] = []
    for item in articulos_vendidos:
        articulo = db.get(Articulo, item.id_articulo)
        codigo = articulo.codigo_interno if articulo else str(item.id_articulo)
        partes.append(f"(articulo id = {codigo}, cantidad = {item.cantidad})")
    return f"Venta de {', '.join(partes)}"


def _resolver_datos_cliente_para_sheets(
    db: Session,
    id_empresa: int,
    id_cliente_normalizado: int | None,
) -> tuple[Any, str, str, str]:
    if id_cliente_normalizado is not None:
        cliente = clientes_manager.obtener_cliente_por_id(id_empresa, db, id_cliente_normalizado)
        cliente_sheets_data = (
            obtener_cliente_por_id(db, id_empresa=id_empresa, id_cliente=cliente.codigo_interno)
            if cliente
            else None
        )
        if cliente_sheets_data:
            return (
                id_cliente_normalizado,
                cliente_sheets_data.get("nombre-usuario", "Cliente sin nombre"),
                cliente_sheets_data.get("CUIT-CUIL", "N/A"),
                cliente_sheets_data.get("Nombre de Contacto", "N/A"),
            )
        return (id_cliente_normalizado, "Público General", "N/A", "N/A")
    return ("0", "cliente final", "-", "-")


def _encolar_sync_sheets_post_venta(
    db: Session,
    *,
    usuario_actual: Usuario,
    nueva_venta: Venta,
    articulos_vendidos: List[ArticuloVendido],
    tipo_comprobante_solicitado: str | None,
    id_cliente_normalizado: int | None,
    afectar_stock: bool,
    pagos: List[tuple[str, float]],
) -> None:
    """
    Encola movimiento(s) y stock para Google Sheets.
    Se procesa después del commit de la venta (background), sin bloquear MySQL.
    """
    id_cliente_payload, nombre_cliente, cuit_cliente, razon_social = _resolver_datos_cliente_para_sheets(
        db,
        usuario_actual.id_empresa,
        id_cliente_normalizado,
    )
    descripcion = _construir_descripcion_venta_sheets(db, articulos_vendidos)

    for metodo_pago, monto in pagos:
        datos_para_sheets = {
            "id_cliente": id_cliente_payload,
            "id_ingresos": str(nueva_venta.id),
            "id_repartidor": "",
            "Repartidor": usuario_actual.nombre_usuario,
            "cliente": nombre_cliente,
            "cuit": cuit_cliente,
            "razon_social": razon_social,
            "Tipo_movimiento": f"[{tipo_comprobante_solicitado}] Venta en {metodo_pago}",
            "nro_comprobante": "",
            "descripcion": descripcion,
            "monto": monto,
            "foto_comprobante": "",
            "observaciones": "",
        }
        _encolar_movimiento_pendiente(
            db=db,
            id_empresa=usuario_actual.id_empresa,
            datos_para_sheets=datos_para_sheets,
            id_venta=nueva_venta.id,
        )

    if afectar_stock and articulos_vendidos:
        _encolar_stock_pendiente(
            db=db,
            id_empresa=usuario_actual.id_empresa,
            id_venta=nueva_venta.id,
            articulos_vendidos=articulos_vendidos,
        )

    if _sincroniza_con_sheets(db, usuario_actual.id_empresa):
        _agregar_evento_sync_nube(
            db,
            operacion="sync_nube_venta",
            estado="pendiente",
            mensaje=(
                f"Sincronización con Google Sheets encolada "
                f"({len(pagos)} movimiento(s)"
                f"{', stock' if afectar_stock and articulos_vendidos else ''}). "
                "Se procesará en segundo plano."
            ),
            requiere_reintento=True,
        )

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
    id_cliente: int = None,
    pago_separado:bool = None,
    detalles_pago_separado: str = None,
    tipo_comprobante_solicitado: str = None,
    omitir_stock: bool = False,
    propina: float = 0.0,
    descuento_total: float = 0.0,
    crear_movimiento_caja: bool = True  # <-- NUEVO: Controla si se crea o no el movimiento
) -> Tuple[Venta, CajaMovimiento]:
    """
    Registra una Venta, aplica recargos dinámicos según la configuración
    de la empresa, y encola la sincronización con Google Sheets para después del commit.
    """
    # --- 1. VALIDACIÓN DE ARTÍCULOS Y STOCK (Sin Cambios) ---
    for item in articulos_vendidos:
        # Validar que el ID sea válido (no ser 0 o negativo)
        if not item.id_articulo or item.id_articulo <= 0:
            raise ValueError(f"ID de artículo inválido: {item.id_articulo}. Debe ser un número positivo.")
        
        articulo_db = db.get(Articulo, item.id_articulo)
        if not articulo_db:
            raise ValueError(f"El artículo con ID {item.id_articulo} no existe en la base de datos.")
        if articulo_db.id_empresa != usuario_actual.id_empresa:
            raise ValueError(f"El artículo '{articulo_db.descripcion}' no pertenece a la empresa.")
        # Stock: se permite vender sin stock (el saldo puede quedar negativo).
        # precio_manual y omitir_stock no descuentan stock más adelante en este flujo.

    id_cliente_normalizado = id_cliente if id_cliente and id_cliente > 0 else None

    # --- 2. LÓGICA DE RECARGO DINÁMICO ---
    total_final_con_recargo = total_venta
    monto_recargo = 0.0
    metodo_pago_upper = metodo_pago.upper()


    # PASO A: Buscamos la configuración específica de la empresa del usuario actual.
    print(f"Buscando configuración para la Empresa ID: {usuario_actual.id_empresa}...")
    config_empresa = db.get(ConfiguracionEmpresa, usuario_actual.id_empresa)
    if not config_empresa:
        # Si no hay configuración, no aplicamos recargos. Podríamos lanzar un error si fuera un requisito estricto.
        print(f"ADVERTENCIA: No se encontró configuración para la empresa ID {usuario_actual.id_empresa}.")
        porcentaje_recargo = 0.0
    else:
        # PASO B: Recargo solo si está habilitado en configuración (el toggle de gestión de negocio).
        porcentaje_recargo = 0.0
        if metodo_pago_upper == "TRANSFERENCIA":
            if getattr(config_empresa, "recargo_transferencia_habilitado", False):
                porcentaje_recargo = config_empresa.recargo_transferencia
        elif metodo_pago_upper == "BANCARIO":
            if getattr(config_empresa, "recargo_banco_habilitado", False):
                porcentaje_recargo = config_empresa.recargo_banco
    
    # PASO C: Calculamos el recargo solo si el porcentaje obtenido de la base de datos es mayor a cero.
    if porcentaje_recargo > 0 and total_venta > 0:
        monto_recargo = total_venta * (porcentaje_recargo / 100.0)
        total_final_con_recargo = total_venta + monto_recargo
        print(f"Recargo DINÁMICO del {porcentaje_recargo}% aplicado. Monto a distribuir: {monto_recargo:.2f}")
        
    # --- 3. CREACIÓN DE LA VENTA PRINCIPAL ---
    nueva_venta = Venta(
        total=total_final_con_recargo, # El total de la Venta SÍ incluye el recargo
        descuento_total=descuento_total,
        id_cliente=id_cliente_normalizado,
        id_usuario=usuario_actual.id,
        id_caja_sesion=id_sesion_caja,
        id_empresa=usuario_actual.id_empresa,
        pago_separado=pago_separado,
        detalles_pago_separado=detalles_pago_separado,
        tipo_comprobante_solicitado=tipo_comprobante_solicitado,
    )
    db.add(nueva_venta)
    db.flush()

    # ===================================================================
    # === INICIO DE LA LÓGICA CONDICIONAL DE CONTROL (EL "GUARDIÁN") ===
    # ===================================================================
    
    afectar_stock = False
    afectar_caja = False

    tipo_lower = (tipo_comprobante_solicitado or "").strip().lower()
    if tipo_lower == "comprobante":
        tipo_lower = "recibo"
    # El front envía factura_a / factura_b; antes no entraban al guardián y no impactaban caja ni Sheets.
    if tipo_lower in ("factura_a", "factura_b", "factura_c") or tipo_lower.startswith("factura"):
        tipo_lower = "factura"

    if tipo_lower in ["factura", "recibo", "comprobante interno", "ticket", "comprobante"]:
        print("   -> DECISIÓN: Afectar STOCK y CAJA.")
        afectar_stock = True
        afectar_caja = True
    elif tipo_lower == "remito":
        print("   -> DECISIÓN: Afectar SÓLO STOCK.")
        afectar_stock = True
        afectar_caja = False
    elif tipo_lower == "presupuesto":
        print("   -> DECISIÓN: NO afectar ni Stock ni Caja.")
        afectar_stock = False
        afectar_caja = False
    else:
        # Si no se reconoce el tipo, por seguridad, no hacemos nada.
        # Podríamos lanzar un error si quisiéramos ser más estrictos.
        print(f"   -> ADVERTENCIA: Tipo '{tipo_comprobante_solicitado}' no reconocido para lógica de stock/caja.")

    # Override si se solicita omitir stock (ej: desde módulo Mesas donde ya se descontó)
    if omitir_stock:
        print("   -> OVERRIDE: Omitir descuento de STOCK solicitado.")
        afectar_stock = False
    
    for item in articulos_vendidos:
        articulo_a_actualizar = db.get(Articulo, item.id_articulo)
        
        precio_original_subtotal = item.precio_unitario * item.cantidad
        precio_unitario_final = item.precio_unitario # Por defecto, el precio no cambia
        
        # --- CÁLCULO DE DESCUENTOS POR ÍTEM ---
        descuento_item_total = 0.0
        if item.descuento_especifico or item.descuento_especifico_por:
             monto_desc_porc = precio_original_subtotal * ((item.descuento_especifico_por or 0.0) / 100.0)
             monto_desc_nominal = item.descuento_especifico or 0.0
             descuento_item_total = monto_desc_porc + monto_desc_nominal
             
             # Reducimos el precio unitario final proporcionalmente
             if item.cantidad > 0:
                 descuento_unitario = descuento_item_total / item.cantidad
                 precio_unitario_final -= descuento_unitario

        if monto_recargo > 0 and total_venta > 0:
            # Calculamos la proporción (el "peso") que este ítem tiene en la venta original
            # Usamos el precio ya descontado para la proporción si se quiere, o el original.
            # Usualmente el recargo financiero es sobre el total a pagar.
            # El total_venta que viene YA tiene descuentos aplicados.
            # Así que la proporción debería ser sobre el precio neto de este item.
            
            subtotal_neto_item = (precio_unitario_final * item.cantidad)
            proporcion_del_item = subtotal_neto_item / total_venta if total_venta > 0 else 0
            
            # A este ítem le corresponde esa misma proporción del recargo total
            recargo_para_este_item = monto_recargo * proporcion_del_item
            # Distribuimos el recargo del ítem en su precio unitario
            if item.cantidad > 0:
                precio_unitario_final += (recargo_para_este_item / item.cantidad)

        detalle = VentaDetalle(
            id_venta=nueva_venta.id,
            id_articulo=item.id_articulo,
            cantidad=item.cantidad,
            precio_unitario=precio_unitario_final, # <-- Precio final pagado (con descuentos y recargos)
            descuento_aplicado=descuento_item_total # <-- Para auditoría
        )
        db.add(detalle)
        if afectar_stock:
            articulo_a_actualizar = db.get(Articulo, item.id_articulo)
            if articulo_a_actualizar and not getattr(articulo_a_actualizar, "precio_manual", False):
                print(f"      -> Descontando {item.cantidad} de stock para '{articulo_a_actualizar.descripcion}'")
                articulo_a_actualizar.stock_actual -= item.cantidad
                db.add(articulo_a_actualizar)

    movimiento_principal = None # Inicializamos como None
    
    # Solo crear movimiento si afectar_caja es True Y crear_movimiento_caja es True
    if afectar_caja and crear_movimiento_caja:
        print("   -> Registrando movimiento en caja...")
        monto_total_caja = total_final_con_recargo + propina
        concepto_movimiento = f"Venta ({tipo_comprobante_solicitado}) ID: {nueva_venta.id}"
        if propina > 0:
            concepto_movimiento += f" (Incluye Propina: ${propina:.2f})"

        movimiento_principal = CajaMovimiento(
            tipo=TipoMovimiento.VENTA.value,
            concepto=concepto_movimiento,
            monto=monto_total_caja,
            metodo_pago=metodo_pago,
            id_caja_sesion=id_sesion_caja,
            id_usuario=usuario_actual.id,
            id_venta=nueva_venta.id,
        )
        db.add(movimiento_principal)
    else:
        if not crear_movimiento_caja:
            print("   -> OMITIDO: No se crea movimiento de caja (se gestionará externamente).")
        else:
            print("   -> OMITIDO: No se registra movimiento en caja según configuración.")
        
    db.flush()

    # --- 4. SYNC GOOGLE SHEETS: encolar para procesar después del commit (no bloquea MySQL) ---
    if (afectar_stock or afectar_caja) and crear_movimiento_caja:
        print("[SYNC] Encolando sincronización con Google Sheets (post-commit)...")
        _encolar_sync_sheets_post_venta(
            db=db,
            usuario_actual=usuario_actual,
            nueva_venta=nueva_venta,
            articulos_vendidos=articulos_vendidos,
            tipo_comprobante_solicitado=tipo_comprobante_solicitado,
            id_cliente_normalizado=id_cliente_normalizado,
            afectar_stock=afectar_stock,
            pagos=[(metodo_pago, total_final_con_recargo)],
        )
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
    usuario_actual: Usuario,
    id_sesion_caja: int,
    concepto: str,
    monto: float,
    tipo: str,
    metodo_pago: str,
) -> CajaMovimiento:
    """
    Registra un ingreso o egreso simple en caja y encola sync con Google Sheets.
    'tipo' debe ser 'INGRESO' o 'EGRESO'. El monto siempre es positivo.
    El commit lo realiza el router que invoca esta función.
    """
    print(f"\n--- [TRACE: REGISTRAR MOVIMIENTO] ---")
    print(f"1. Solicitud de {tipo} para Sesión ID: {id_sesion_caja}, Monto: {monto}")

    tipo_upper = tipo.upper()
    if tipo_upper not in ("INGRESO", "EGRESO"):
        raise ValueError("Tipo de movimiento no válido. Debe ser 'INGRESO' o 'EGRESO'.")

    if monto <= 0:
        raise ValueError("El monto del movimiento debe ser un número positivo.")

    metodo = (metodo_pago or "EFECTIVO").upper()

    nuevo_movimiento = CajaMovimiento(
        id_caja_sesion=id_sesion_caja,
        id_usuario=usuario_actual.id,
        tipo=tipo_upper,
        concepto=concepto,
        monto=monto,
        metodo_pago=metodo,
    )
    db.add(nuevo_movimiento)
    db.flush()

    datos_para_sheets = _construir_datos_movimiento_manual_sheets(
        usuario_actual=usuario_actual,
        movimiento=nuevo_movimiento,
        tipo=tipo_upper,
        concepto=concepto,
        monto=monto,
        metodo_pago=metodo,
    )
    _encolar_movimiento_pendiente(
        db=db,
        id_empresa=usuario_actual.id_empresa,
        datos_para_sheets=datos_para_sheets,
    )
    if _sincroniza_con_sheets(db, usuario_actual.id_empresa):
        _agregar_evento_sync_nube(
            db,
            operacion="sync_nube_movimiento_manual",
            estado="pendiente",
            mensaje=f"Movimiento {tipo_upper} encolado para Google Sheets (ID local: {nuevo_movimiento.id}).",
            requiere_reintento=True,
        )

    print(f"   -> Movimiento preparado con ID: {nuevo_movimiento.id} (pendiente de commit)")
    print("--- [FIN TRACE] ---\n")
    return nuevo_movimiento


def registrar_venta_y_movimientos_caja_multiples(
    db: Session,
    usuario_actual: Usuario,
    id_sesion_caja: int,
    total_venta: float,
    pagos_multiples: List[PagoMultiple],
    articulos_vendidos: List[ArticuloVendido],
    id_cliente: int = None,
    pago_separado: bool = None,
    detalles_pago_separado: str = None,
    tipo_comprobante_solicitado: str = None,
    omitir_stock: bool = False,
    propina: float = 0.0,
    descuento_total: float = 0.0
) -> Tuple[Venta, List[CajaMovimiento]]:
    """
    Registra una Venta con MÚLTIPLES MEDIOS DE PAGO.
    Crea un CajaMovimiento para cada medio de pago con su monto correspondiente.
    
    Valida que la suma de pagos_multiples sea igual a total_venta.
    """
    print(f"\n--- [REGISTRO VENTA CON MÚLTIPLES PAGOS] ---")
    print(f"Total esperado: ${total_venta:.2f}")
    print(f"Pagos: {[(p.metodo_pago, p.monto) for p in pagos_multiples]}")
    
    id_cliente_normalizado = id_cliente if id_cliente and id_cliente > 0 else None

    # --- 1. VALIDAR SUMA DE PAGOS ---
    suma_pagos = sum(p.monto for p in pagos_multiples)
    if abs(suma_pagos - total_venta) > 0.01:  # Tolerancia por redondeo
        raise ValueError(f"La suma de pagos (${suma_pagos:.2f}) no coincide con el total (${total_venta:.2f})")
    
    # --- 2. REUTILIZAR LÓGICA DE VALIDACIÓN Y CREACIÓN DE VENTA ---
    # NO creamos movimiento de caja aquí, solo la venta y descuento de stock
    nueva_venta, _ = registrar_venta_y_movimiento_caja(
        db=db,
        usuario_actual=usuario_actual,
        id_sesion_caja=id_sesion_caja,
        total_venta=total_venta,
        metodo_pago="MÚLTIPLE",  # Marcamos como múltiple (pero no se usará para crear movimiento)
        articulos_vendidos=articulos_vendidos,
        id_cliente=id_cliente_normalizado,
        pago_separado=pago_separado,
        detalles_pago_separado=detalles_pago_separado,
        tipo_comprobante_solicitado=tipo_comprobante_solicitado,
        omitir_stock=omitir_stock,
        propina=propina,
        descuento_total=descuento_total,
        crear_movimiento_caja=False  # <-- CLAVE: No crear movimiento aquí
    )
    
    # --- 3. CREAR UN MOVIMIENTO DE CAJA POR CADA MEDIO DE PAGO ---
    movimientos = []
    for pago in pagos_multiples:
        concepto = f"Venta ({tipo_comprobante_solicitado}) ID: {nueva_venta.id} - Pago por {pago.metodo_pago}"
        
        movimiento = CajaMovimiento(
            tipo=TipoMovimiento.VENTA.value,
            concepto=concepto,
            monto=pago.monto,
            metodo_pago=pago.metodo_pago.upper(),
            id_caja_sesion=id_sesion_caja,
            id_usuario=usuario_actual.id,
            id_venta=nueva_venta.id,
        )
        db.add(movimiento)
        movimientos.append(movimiento)
        print(f"  -> Movimiento registrado: {pago.metodo_pago} - ${pago.monto:.2f}")
    
    db.flush()
    
    # --- 4. SYNC GOOGLE SHEETS: encolar para procesar después del commit ---
    tipo_lower = (tipo_comprobante_solicitado or "").strip().lower()
    if tipo_lower == "comprobante":
        tipo_lower = "recibo"
    if tipo_lower in ("factura_a", "factura_b", "factura_c") or tipo_lower.startswith("factura"):
        tipo_lower = "factura"
    afectar_stock_multiples = tipo_lower in [
        "factura", "recibo", "comprobante interno", "ticket", "comprobante", "remito"
    ]
    if omitir_stock:
        afectar_stock_multiples = False

    print("[SYNC] Encolando desglose de pagos múltiples para Google Sheets (post-commit)...")
    _encolar_sync_sheets_post_venta(
        db=db,
        usuario_actual=usuario_actual,
        nueva_venta=nueva_venta,
        articulos_vendidos=articulos_vendidos,
        tipo_comprobante_solicitado=tipo_comprobante_solicitado,
        id_cliente_normalizado=id_cliente_normalizado,
        afectar_stock=afectar_stock_multiples,
        pagos=[(p.metodo_pago.upper(), p.monto) for p in pagos_multiples],
    )
    
    print(f"--- [FIN REGISTRO VENTA CON MÚLTIPLES PAGOS] ---\n")
    
    return nueva_venta, movimientos

