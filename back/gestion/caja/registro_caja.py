# back/gestion/caja/registro_caja.py

from datetime import datetime
from requests import session
from sqlmodel import Session, select
from typing import List, Tuple, Dict, Any
from datetime import datetime
from back.gestion.caja.cliente_publico import obtener_cliente_por_id
# Importa todos tus modelos. Asegúrate de que las rutas sean correctas.
from back.modelos import Usuario, Venta, VentaDetalle, Articulo, CajaMovimiento, Tercero, CajaSesion, ConfiguracionEmpresa
from back.schemas.caja_schemas import ArticuloVendido, RegistrarVentaRequest, TipoMovimiento
from back.utils.tablas_handler import TablasHandler

from back.gestion.contabilidad.clientes_contabilidad import manager as clientes_manager

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
    id_cliente: int = None,
    pago_separado:bool = None,
    detalles_pago_separado: str = None,
    tipo_comprobante_solicitado: str = None,
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
    metodo_pago_upper = metodo_pago.upper()

    # PASO A: Buscamos la configuración específica de la empresa del usuario actual.
    print(f"Buscando configuración para la Empresa ID: {usuario_actual.id_empresa}...")
    config_empresa = db.get(ConfiguracionEmpresa, usuario_actual.id_empresa)
    if not config_empresa:
        # Si no hay configuración, no aplicamos recargos. Podríamos lanzar un error si fuera un requisito estricto.
        print(f"ADVERTENCIA: No se encontró configuración para la empresa ID {usuario_actual.id_empresa}.")
        porcentaje_recargo = 0.0
    else:
        # PASO B: Decidimos qué recargo leer de la base de datos basándonos en el método de pago.
        porcentaje_recargo = 0.0
        if metodo_pago_upper == "TRANSFERENCIA":
            # Leemos el valor que esta empresa específica tiene en su fila de la tabla 'configuracion_empresa'.
            porcentaje_recargo = config_empresa.recargo_transferencia
        elif metodo_pago_upper == "BANCARIO":
            # Leemos el otro valor dinámico de la base de datos.
            porcentaje_recargo = config_empresa.recargo_banco
    
    # PASO C: Calculamos el recargo solo si el porcentaje obtenido de la base de datos es mayor a cero.
    if porcentaje_recargo > 0 and total_venta > 0:
        monto_recargo = total_venta * (porcentaje_recargo / 100.0)
        total_final_con_recargo = total_venta + monto_recargo
        print(f"Recargo DINÁMICO del {porcentaje_recargo}% aplicado. Monto a distribuir: {monto_recargo:.2f}")
        
    # --- 3. CREACIÓN DE LA VENTA PRINCIPAL ---
    nueva_venta = Venta(
        total=total_final_con_recargo, # El total de la Venta SÍ incluye el recargo
        id_cliente=id_cliente,
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
    
    tipo_lower = tipo_comprobante_solicitado.lower()

    if tipo_lower in ["factura", "recibo", "comprobante interno", "ticket"]:
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

    
    for item in articulos_vendidos:
        articulo_a_actualizar = db.get(Articulo, item.id_articulo)
        
        precio_original_subtotal = item.precio_unitario * item.cantidad
        precio_unitario_final = item.precio_unitario # Por defecto, el precio no cambia
        
        if monto_recargo > 0 and total_venta > 0:
            # Calculamos la proporción (el "peso") que este ítem tiene en la venta original
            proporcion_del_item = precio_original_subtotal / total_venta
            # A este ítem le corresponde esa misma proporción del recargo total
            recargo_para_este_item = monto_recargo * proporcion_del_item
            # Distribuimos el recargo del ítem en su precio unitario
            # Verificamos que la cantidad no sea cero para evitar divisiones por cero
            if item.cantidad > 0:
                precio_unitario_final = item.precio_unitario + (recargo_para_este_item / item.cantidad)

        detalle = VentaDetalle(
            id_venta=nueva_venta.id,
            id_articulo=item.id_articulo,
            cantidad=item.cantidad,
            precio_unitario=precio_unitario_final # <-- ¡Guardamos el precio unitario CON el recargo distribuido!
        )
        db.add(detalle)
        if afectar_stock:
            articulo_a_actualizar = db.get(Articulo, item.id_articulo)
            if articulo_a_actualizar:
                print(f"      -> Descontando {item.cantidad} de stock para '{articulo_a_actualizar.descripcion}'")
                articulo_a_actualizar.stock_actual -= item.cantidad
                db.add(articulo_a_actualizar)

    movimiento_principal = None # Inicializamos como None
    print("   -> Registrando movimiento en caja...")
    movimiento_principal = CajaMovimiento(
        tipo=TipoMovimiento.VENTA.value,
        concepto=f"Venta ({tipo_comprobante_solicitado}) ID: {nueva_venta.id}",
        monto=total_final_con_recargo,
        metodo_pago=metodo_pago,
        id_caja_sesion=id_sesion_caja,
        id_usuario=usuario_actual.id,
        id_venta=nueva_venta.id,
    )
    db.add(movimiento_principal)
        
    db.flush()

    # --- 4. SINCRONIZACIÓN CON GOOGLE SHEETS (TU LÓGICA ORIGINAL) ---
    # Esta parte ahora se ejecuta DENTRO de la misma función, antes del commit.
    # El router la convertirá en una tarea en segundo plano.
    if afectar_stock or afectar_caja:
        try:
                print("[DRIVE] Intentando registrar movimiento en Google Sheets...")
                cliente = clientes_manager.obtener_cliente_por_id(usuario_actual.id_empresa,db, id_cliente)
                cliente_sheets_data = obtener_cliente_por_id(db,id_empresa=usuario_actual.id_empresa,id_cliente=cliente.codigo_interno) # Asumo que esta función devuelve un dict
                print("LA DATA DE CLIENTE_SHEETS_DATA ES   :  ")
                print(cliente_sheets_data)
                nombre_cliente_para_sheets = "Público General"
                cuit_cliente_para_sheets = "N/A"
                razon_social_para_sheets = "N/A"

                # Si cliente_sheets_data NO es None (es decir, encontramos un diccionario)
                if cliente_sheets_data:
                    nombre_cliente_para_sheets = cliente_sheets_data.get("nombre-usuario", "Cliente sin nombre")
                    cuit_cliente_para_sheets = cliente_sheets_data.get("CUIT-CUIL", "N/A")
                    razon_social_para_sheets = cliente_sheets_data.get("Nombre de Contacto", "N/A")

                    datos_para_sheets = {
                        "id_cliente": id_cliente,
                        "cliente": nombre_cliente_para_sheets,
                        "cuit": cuit_cliente_para_sheets,
                        "razon_social": razon_social_para_sheets,
                        "Tipo_movimiento": f"[{tipo_comprobante_solicitado}] Venta en {metodo_pago}",
                        "descripcion": f"Venta de {', '.join(f'(articulo id = {item.id_articulo}, cantidad = {item.cantidad})' for item in articulos_vendidos)}",
                        "monto": total_final_con_recargo,
                        "Repartidor": usuario_actual.nombre_usuario
                    }
                
                    caller = TablasHandler(id_empresa=usuario_actual.id_empresa, db=db)
                    if not caller.registrar_movimiento(datos_para_sheets):
                        print("⚠️ [DRIVE] La función registrar_movimiento devolvió False.")
                    if afectar_stock and not caller.restar_stock(articulos_vendidos): # Solo resta stock si afectar_stock es True
                        print("⚠️ [DRIVE] Ocurrió un error al intentar actualizar el stock en Google Sheets.")
                    # --- FIN DE LA LÓGICA CORREGIDA ---
                    print("ESTAMOS SALIENDO DE LA FUNCION REGISTRAR_VENTA_Y _MOVIMIENTO")
                else:
                    datos_para_sheets = {
                        "id_cliente": "0",
                        "cliente": "cliente final",
                        "cuit": "-",
                        "razon_social": "-",
                         "Tipo_movimiento": f"[{tipo_comprobante_solicitado}] Venta en {metodo_pago}",
                        "descripcion": f"Venta de {', '.join(f'(articulo id = {item.id_articulo}, cantidad = {item.cantidad})' for item in articulos_vendidos)}",
                        "monto": total_final_con_recargo,
                        "Repartidor": usuario_actual.nombre_usuario
                    }
                    caller = TablasHandler(id_empresa=usuario_actual.id_empresa, db=db)
                    if not caller.registrar_movimiento(datos_para_sheets):
                        print("⚠️ [DRIVE] La función registrar_movimiento devolvió False.")
                    if afectar_stock and not caller.restar_stock(articulos_vendidos): # Solo resta stock si afectar_stock es True
                        print("⚠️ [DRIVE] Ocurrió un error al intentar actualizar el stock en Google Sheets.")

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
    usuario_actual: Usuario,
    id_sesion_caja: int,
    concepto: str,
    monto: float,
    tipo: str,
    id_usuario: int,
    facturado: bool,
    fecha_hora: datetime,
    metodo_pago:str
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
        metodo_pago=metodo_pago, # Asumimos efectivo para movimientos simples
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
                    "Tipo_movimiento": f"egreso en {metodo_pago}",
                    "descripcion": concepto,
                    "monto": monto,
            }

            caller = TablasHandler(usuario_actual.id_empresa, db=db)
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

