# test_general_flujos.py

import sys
from datetime import datetime, timedelta

# --- Importaciones de Módulos de Caja ---
from gestion.caja import apertura_cierre as caja_ap_ci
from gestion.caja import registro_caja as caja_reg
from gestion.caja import cliente_publico as caja_cli
from gestion import auth as auth_module # Para el token de admin si es necesario

# --- Importaciones de Módulos de Compras ---
from gestion.compra import proveedores_compra
from gestion.compra import registro_compra as compra_reg
from gestion.stock import articulos as stock_articulos # Para artículos simulados

# --- Importaciones de Configuración y Utils ---
from config import (
    GOOGLE_SHEET_ID,
    # Hojas de Caja
    SHEET_NAME_CAJA_APERTURAS, SHEET_NAME_CAJA_REGISTROS,
    # Hojas de Compras
    SHEET_NAME_PROVEEDORES, SHEET_NAME_ORDENES_COMPRA,
    SHEET_NAME_ITEMS_OC, SHEET_NAME_ARTICULOS,
    # Hojas de Auth/Config (si se usan desde sheets)
    SHEET_NAME_ADMIN_TOKEN, SHEET_NAME_CONFIG_HORARIOS
)
from utils.sheets_google_handler import GoogleSheetsHandler


# ---- Variables Globales de Prueba ----
USUARIO_PRUEBA_CAJA = "cajero_maestro_01"
USUARIO_PRUEBA_COMPRAS = "comprador_sistema_01"
current_test_user = USUARIO_PRUEBA_CAJA # Usuario por defecto para algunas operaciones

# Artículos simulados que usaremos (deben coincidir con los de gestion/stock/articulos.py)
ARTICULO_VENTA_1 = "PROD001" # Coca Cola 600ml
ARTICULO_VENTA_2 = "PROD002" # Galletas Oreo
ARTICULO_COMPRA_1 = "PROD001" # Coca Cola 600ml (para reponer)
ARTICULO_COMPRA_2 = "MATPRIMA01" # Harina 000 1kg

# Para guardar IDs generados entre pruebas
id_proveedor_test_global = None
id_oc_test_global = None
id_sesion_caja_test_global = None


def verificar_conexion_y_hojas_requeridas():
    """Verifica la conexión a Google Sheets y la existencia de hojas clave."""
    print("Verificando pre-requisitos...")
    if not GOOGLE_SHEET_ID:
        print("Error Crítico: GOOGLE_SHEET_ID no está configurado.")
        return False
    
    try:
        g_handler = GoogleSheetsHandler()
        if not g_handler.client:
            print("Fallo en la conexión a Google Sheets.")
            return False
        print("Conexión a Google Sheets: OK.")

        # Lista de todas las hojas que deberían existir para las pruebas
        required_sheets = [
            SHEET_NAME_CAJA_APERTURAS, SHEET_NAME_CAJA_REGISTROS,
            SHEET_NAME_PROVEEDORES, SHEET_NAME_ORDENES_COMPRA,
            SHEET_NAME_ITEMS_OC, SHEET_NAME_ARTICULOS,
            # Opcional: SHEET_NAME_ADMIN_TOKEN, SHEET_NAME_CONFIG_HORARIOS (si los usas desde sheets)
        ]
        missing_sheets = []
        for sheet_name in required_sheets:
            if not sheet_name: # Si alguna variable de config no está seteada
                print(f"Advertencia: Nombre de hoja no configurado para una de las hojas requeridas (variable vacía).")
                continue
            if not g_handler.get_worksheet(sheet_name):
                missing_sheets.append(sheet_name)
        
        if missing_sheets:
            print(f"Error: Faltan las hojas: {', '.join(missing_sheets)}")
            print("Por favor, créalas en tu Google Spreadsheet con las cabeceras esperadas.")
            return False
        print("Hojas de cálculo requeridas: OK.")
        return True
        
    except Exception as e:
        print(f"Error durante la verificación de pre-requisitos: {e}")
        return False

# ==================================================
# =========== FUNCIONES DE PRUEBA DE CAJA ==========
# ==================================================
def test_flujo_completo_caja():
    global id_sesion_caja_test_global
    print("\n--- INICIO PRUEBA: FLUJO COMPLETO DE CAJA ---")

    # 0. Verificar si hay una caja abierta (y cerrarla si es de una prueba anterior)
    print("\n0. Verificando estado de caja actual...")
    sesion_abierta_existente = caja_ap_ci.obtener_estado_caja_actual()
    if sesion_abierta_existente:
        print(f"ADVERTENCIA: Ya hay una caja abierta (Sesión ID: {sesion_abierta_existente.get('ID_Sesion')}).")
        print("Se intentará cerrarla para continuar con la prueba (requiere token de admin).")
        if not auth_module.solicitar_y_verificar_admin_token(): # Asumiendo que tienes el módulo auth y funciona
             print("Token de admin incorrecto. No se puede cerrar la caja existente. Abortando prueba de caja.")
             return
        saldo_ficticio_cierre = float(sesion_abierta_existente.get('SaldoInicial', 0)) + 10 # Un cierre simple
        caja_ap_ci.cerrar_caja(
            id_sesion=int(sesion_abierta_existente.get('ID_Sesion')),
            saldo_final_contado=saldo_ficticio_cierre,
            usuario_cierre="admin_test_cierre_auto"
        )
        print("Caja existente cerrada.")

    # 1. Abrir Caja
    print("\n1. Abriendo Caja...")
    saldo_inicial_caja = 250.75
    resultado_apertura = caja_ap_ci.abrir_caja(saldo_inicial=saldo_inicial_caja, usuario=USUARIO_PRUEBA_CAJA)
    print(f"Resultado abrir_caja: {resultado_apertura}")
    if resultado_apertura["status"] != "success":
        print("Fallo al abrir la caja. Abortando prueba de caja.")
        return
    id_sesion_caja_test_global = resultado_apertura["id_sesion"]
    print(f"Caja abierta con Sesión ID: {id_sesion_caja_test_global}")

    # 2. Registrar una Venta
    print("\n2. Registrando Venta...")
    # Obtener info de artículos simulados para la venta
    articulo_v1_info = stock_articulos.obtener_articulo_por_id_simulado(ARTICULO_VENTA_1)
    articulo_v2_info = stock_articulos.obtener_articulo_por_id_simulado(ARTICULO_VENTA_2)
    if not articulo_v1_info or not articulo_v2_info:
        print(f"Artículos de prueba para venta ({ARTICULO_VENTA_1}, {ARTICULO_VENTA_2}) no encontrados en simulación.")
        return

    articulos_para_venta = [
        {"id_articulo": ARTICULO_VENTA_1, "nombre": articulo_v1_info.get("Descripcion"), "cantidad": 2, "precio_unitario": articulo_v1_info.get("PrecioVenta", 1.50), "subtotal": 2 * articulo_v1_info.get("PrecioVenta", 1.50)},
        {"id_articulo": ARTICULO_VENTA_2, "nombre": articulo_v2_info.get("Descripcion"), "cantidad": 1, "precio_unitario": articulo_v2_info.get("PrecioVenta", 0.80), "subtotal": 1 * articulo_v2_info.get("PrecioVenta", 0.80)},
    ]
    total_venta_calculado = sum(item['subtotal'] for item in articulos_para_venta)
    
    resultado_venta = caja_reg.registrar_venta(
        id_sesion_caja=id_sesion_caja_test_global,
        articulos_vendidos=articulos_para_venta,
        cliente=caja_cli.obtener_cliente_para_venta(), # Público General
        metodo_pago="EFECTIVO",
        usuario=USUARIO_PRUEBA_CAJA,
        total_venta=total_venta_calculado
    )
    print(f"Resultado registrar_venta: {resultado_venta}")

    # 3. Registrar un Ingreso Adicional
    print("\n3. Registrando Ingreso Adicional...")
    monto_ingreso = 15.50
    resultado_ingreso = caja_reg.registrar_ingreso_efectivo(
        id_sesion_caja=id_sesion_caja_test_global,
        concepto="Servicio extra",
        monto=monto_ingreso,
        usuario=USUARIO_PRUEBA_CAJA
    )
    print(f"Resultado registrar_ingreso_efectivo: {resultado_ingreso}")

    # 4. Registrar un Egreso
    print("\n4. Registrando Egreso...")
    monto_egreso = 5.25
    resultado_egreso = caja_reg.registrar_egreso_efectivo(
        id_sesion_caja=id_sesion_caja_test_global,
        concepto="Compra menor",
        monto=monto_egreso,
        usuario=USUARIO_PRUEBA_CAJA
    )
    print(f"Resultado registrar_egreso_efectivo: {resultado_egreso}")

    # 5. Cerrar Caja
    print("\n5. Cerrando Caja...")
    print("Para cerrar la caja, se simulará la solicitud de token de administrador.")
    # Simulación de obtención de token:
    # En un entorno real, el admin ingresaría el token. Aquí, lo "generamos" y "verificamos"
    # auth_module.generar_y_guardar_admin_token(forzar_nuevo=True) # Asegura que hay un token
    # token_valido_para_prueba = auth_module.generar_y_guardar_admin_token()
    # if not auth_module.verificar_admin_token(token_valido_para_prueba):
    if not auth_module.solicitar_y_verificar_admin_token(): # Esto pedirá input
        print("Simulación de token de admin fallida. No se puede cerrar la caja.")
        return

    saldo_final_esperado_teorico = saldo_inicial_caja + total_venta_calculado + monto_ingreso - monto_egreso
    # Supongamos que contamos exactamente eso, o con una pequeña diferencia
    saldo_final_contado_real = saldo_final_esperado_teorico + 0.10 # Una pequeña diferencia de 10 centavos

    resultado_cierre = caja_ap_ci.cerrar_caja(
        id_sesion=id_sesion_caja_test_global,
        saldo_final_contado=saldo_final_contado_real,
        usuario_cierre=USUARIO_PRUEBA_CAJA,
        # saldo_teorico_esperado=saldo_final_esperado_teorico # Si la función lo soporta
    )
    print(f"Resultado cerrar_caja: {resultado_cierre}")
    if resultado_cierre["status"] == "success":
        id_sesion_caja_test_global = None # Limpiar el ID global
        print(f"Diferencia de caja registrada: ${resultado_cierre.get('diferencia', 0.0):.2f}")

    print("\n--- FIN PRUEBA: FLUJO COMPLETO DE CAJA ---")


# =====================================================
# ========= FUNCIONES DE PRUEBA DE COMPRAS ============
# =====================================================
# (Reutilizamos las funciones de test_compras.py, adaptándolas un poco)

def test_flujo_proveedores_interno():
    global id_proveedor_test_global
    print("\n--- INICIO PRUEBA INTERNA: GESTIÓN DE PROVEEDORES ---")
    razon_social_test = f"Prov Test General {int(datetime.now().timestamp())}"
    cuit_test = f"30-{int(datetime.now().timestamp()) % 100000000:08d}-{(int(datetime.now().timestamp()) % 10)}"
    
    resultado_add = proveedores_compra.agregar_proveedor(razon_social_test, cuit_test, "Dir Test", "111")
    print(f"Resultado agregar_proveedor: {resultado_add}")
    id_proveedor_test_global = resultado_add.get("id_proveedor") if resultado_add["status"] == "success" else None
    
    if id_proveedor_test_global:
        print(f"Proveedor de prueba creado con ID: {id_proveedor_test_global}")
        # Se pueden añadir más sub-pruebas aquí (buscar, modificar, desactivar) como en test_compras.py
    else:
        print("Fallo al crear proveedor de prueba.")
    print("--- FIN PRUEBA INTERNA: GESTIÓN DE PROVEEDORES ---")
    return id_proveedor_test_global


def test_flujo_orden_de_compra_interno(id_proveedor_para_oc):
    global id_oc_test_global
    print("\n--- INICIO PRUEBA INTERNA: ÓRDENES DE COMPRA ---")
    if not id_proveedor_para_oc:
        print("ID de proveedor no disponible. Abortando OC.")
        return None

    articulo_c1_info = stock_articulos.obtener_articulo_por_id_simulado(ARTICULO_COMPRA_1)
    articulo_c2_info = stock_articulos.obtener_articulo_por_id_simulado(ARTICULO_COMPRA_2)
    if not articulo_c1_info or not articulo_c2_info:
        print("Artículos de prueba para compra no encontrados en simulación.")
        return None

    items_para_oc = [
        {"id_articulo": ARTICULO_COMPRA_1, "cantidad_pedida": 12, "costo_estimado": articulo_c1_info.get("CostoUltimo", 0.70)},
        {"id_articulo": ARTICULO_COMPRA_2, "cantidad_pedida": 6, "costo_estimado": articulo_c2_info.get("CostoUltimo", 0.40)},
    ]
    
    resultado_crear_oc = compra_reg.crear_orden_de_compra(
        id_proveedor=id_proveedor_para_oc,
        usuario_creador=USUARIO_PRUEBA_COMPRAS,
        items_oc=items_para_oc
    )
    print(f"Resultado crear_orden_de_compra: {resultado_crear_oc}")
    id_oc_test_global = resultado_crear_oc.get("id_orden_compra") if resultado_crear_oc["status"] == "success" else None
    
    if id_oc_test_global:
        print(f"OC de prueba creada con ID: {id_oc_test_global}")
    else:
        print("Fallo al crear OC de prueba.")
    print("--- FIN PRUEBA INTERNA: ÓRDENES DE COMPRA ---")
    return id_oc_test_global


def test_flujo_recepcion_mercaderia_interno(id_oc_para_recepcion):
    print("\n--- INICIO PRUEBA INTERNA: RECEPCIÓN DE MERCADERÍA ---")
    if not id_oc_para_recepcion:
        print("ID de OC no disponible. Abortando recepción.")
        return

    # Recepción completa en una sola vez para simplificar esta prueba combinada
    items_recibidos_total = [
        {"id_articulo": ARTICULO_COMPRA_1, "cantidad_recibida": 12, "costo_unitario_real": 0.72},
        {"id_articulo": ARTICULO_COMPRA_2, "cantidad_recibida": 6, "costo_unitario_real": 0.41},
    ]
    
    resultado_recepcion = compra_reg.registrar_recepcion_mercaderia(
        id_orden_compra=id_oc_para_recepcion,
        items_recibidos=items_recibidos_total,
        usuario_receptor=USUARIO_PRUEBA_COMPRAS,
        nro_remito=f"R-TEST-{int(datetime.now().timestamp())%1000}",
        nro_factura_proveedor=f"F-TEST-{int(datetime.now().timestamp())%1000}"
    )
    print(f"Resultado recepción total: {resultado_recepcion}")
    print("--- FIN PRUEBA INTERNA: RECEPCIÓN DE MERCADERÍA ---")


def test_flujo_completo_compras():
    print("\n--- INICIO PRUEBA: FLUJO COMPLETO DE COMPRAS ---")
    id_prov = test_flujo_proveedores_interno()
    if id_prov:
        id_oc = test_flujo_orden_de_compra_interno(id_prov)
        if id_oc:
            test_flujo_recepcion_mercaderia_interno(id_oc)
    print("\n--- FIN PRUEBA: FLUJO COMPLETO DE COMPRAS ---")


# =====================================================
# =================== MENÚ PRINCIPAL ==================
# =====================================================
def mostrar_menu_pruebas():
    print("\n========= MENÚ DE PRUEBAS GENERALES =========")
    print("1. Ejecutar Flujo Completo de CAJA")
    print("2. Ejecutar Flujo Completo de COMPRAS")
    print("3. Ejecutar AMBOS Flujos (Caja y luego Compras)")
    print("---------------------------------------------")
    print("Sub-pruebas de Caja (individuales):")
    print("  c1. Abrir Caja")
    print("  c2. Registrar Venta (requiere caja abierta)")
    print("  c3. Cerrar Caja (requiere caja abierta y token)")
    print("Sub-pruebas de Compras (individuales):")
    print("  p1. Crear Proveedor")
    print("  p2. Crear Orden de Compra (requiere proveedor)")
    print("  p3. Registrar Recepción (requiere OC)")
    print("---------------------------------------------")
    print("0. Salir")
    return input("Seleccione una opción: ")

if __name__ == "__main__":
    print("INICIANDO PRUEBAS GENERALES DE CAJA Y COMPRAS...")
    print("===============================================")

    # Generar token de admin al inicio para que las pruebas que lo necesiten puedan simularlo
    # Esto es solo para que el archivo del token exista y tenga un valor.
    # La prueba de caja pedirá input para el token de todas formas.
    print("Inicializando token de administrador (si no existe)...")
    auth_module.generar_y_guardar_admin_token() 
    # print(f"Token de administrador actual para referencia (NO USAR DIRECTO EN PRUEBA): {auth_module._cargar_token_data().get('token')}")


    if not verificar_conexion_y_hojas_requeridas():
        print("\nLas pruebas no pueden continuar debido a errores de configuración o conexión.")
        sys.exit(1)
    
    print("\nPre-requisitos de conexión y hojas verificados.")

    while True:
        opcion = mostrar_menu_pruebas()

        if opcion == '1':
            test_flujo_completo_caja()
        elif opcion == '2':
            test_flujo_completo_compras()
        elif opcion == '3':
            print("\nEjecutando Flujo de Caja...")
            test_flujo_completo_caja()
            input("Flujo de Caja completado. Presione Enter para continuar con Flujo de Compras...")
            print("\nEjecutando Flujo de Compras...")
            test_flujo_completo_compras()
        
        # Opciones individuales (requieren manejo de estado entre ellas, ej. id_sesion_caja_test_global)
        elif opcion == 'c1': # Abrir Caja
            if id_sesion_caja_test_global:
                print(f"Ya hay una sesión de caja abierta (ID: {id_sesion_caja_test_global}). Ciérrela primero o reinicie la prueba completa.")
            else:
                 resultado_apertura = caja_ap_ci.abrir_caja(saldo_inicial=100.0, usuario=USUARIO_PRUEBA_CAJA)
                 print(resultado_apertura)
                 if resultado_apertura.get("status") == "success":
                     id_sesion_caja_test_global = resultado_apertura.get("id_sesion")
        elif opcion == 'c2': # Registrar Venta
            if not id_sesion_caja_test_global: print("Abra una caja primero (opción c1 o 1).")
            else:
                # (Copiar lógica de creación de 'articulos_para_venta' y 'total_venta_calculado' de test_flujo_completo_caja)
                articulo_v1_info = stock_articulos.obtener_articulo_por_id_simulado(ARTICULO_VENTA_1)
                articulos_para_venta = [{"id_articulo": ARTICULO_VENTA_1, "nombre": articulo_v1_info.get("Descripcion"), "cantidad": 1, "precio_unitario": articulo_v1_info.get("PrecioVenta", 1.50), "subtotal": 1 * articulo_v1_info.get("PrecioVenta", 1.50)}]
                total_venta_calculado = sum(item['subtotal'] for item in articulos_para_venta)
                resultado_venta = caja_reg.registrar_venta(id_sesion_caja_test_global, articulos_para_venta, "Cliente Test Indiv", "EFECTIVO", USUARIO_PRUEBA_CAJA, total_venta_calculado)
                print(resultado_venta)
        elif opcion == 'c3': # Cerrar Caja
            if not id_sesion_caja_test_global: print("Abra una caja primero (opción c1 o 1).")
            else:
                if not auth_module.solicitar_y_verificar_admin_token(): print("Token admin inválido.")
                else:
                    resultado_cierre = caja_ap_ci.cerrar_caja(id_sesion_caja_test_global, 100.0, USUARIO_PRUEBA_CAJA) # Saldo simple
                    print(resultado_cierre)
                    if resultado_cierre.get("status") == "success": id_sesion_caja_test_global = None
        
        elif opcion == 'p1': # Crear Proveedor
            test_flujo_proveedores_interno() # Esto ya actualiza id_proveedor_test_global
        elif opcion == 'p2': # Crear OC
            if not id_proveedor_test_global: test_flujo_proveedores_interno() # Crear uno si no existe
            if id_proveedor_test_global:
                test_flujo_orden_de_compra_interno(id_proveedor_test_global)
            else: print("No se pudo crear/obtener proveedor para la OC.")
        elif opcion == 'p3': # Registrar Recepción
            if not id_oc_test_global: print("Cree una OC primero (opción p2 o 2).")
            else:
                test_flujo_recepcion_mercaderia_interno(id_oc_test_global)

        elif opcion == '0':
            print("Saliendo del menú de pruebas.")
            break
        else:
            print("Opción no válida.")
        
        if opcion != '0':
            input("\nPresione Enter para volver al menú de pruebas...")

    print("\n===============================================")
    print("FIN DE LAS PRUEBAS GENERALES.")