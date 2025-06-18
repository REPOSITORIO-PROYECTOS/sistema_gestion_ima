# main.py
import sys
import time # para el bucle principal
from datetime import datetime

from gestion.caja import apertura_cierre, registro_caja, cliente_publico
from gestion import auth # Importamos nuestro módulo de autenticación y token
# from gestion import fiscal # Para la impresora fiscal
from gestion.caja.registro_caja import calcular_vuelto # Import directo para la calculadora
from config import GOOGLE_SHEET_ID, SHEET_NAME_CONFIG_HORARIOS, CURRENT_USER_FILE # y otras configs
from utils.sheets_google_handler import GoogleSheetsHandler


# --- Variables Globales de Sesión de la Aplicación ---
current_user = None
current_session_id = None # ID de la sesión de caja actual

def display_header():
    print("\n===================================")
    print("    SISTEMA DE GESTIÓN DE CAJA    ")
    print("===================================")
    if current_user:
        print(f"Usuario Actual: {current_user}")
    if current_session_id:
        print(f"ID Sesión Caja Activa: {current_session_id}")
    print("-----------------------------------")

def set_current_user():
    global current_user
    display_header()
    print("\n--- Identificación de Usuario ---")
    
    # Intentar cargar el último usuario conocido para esta PC
    last_user = auth.obtener_usuario_actual_local()
    if last_user:
        print(f"Último usuario en esta terminal: {last_user}")
        usar_ultimo = input(f"¿Continuar como {last_user}? (s/n): ").lower()
        if usar_ultimo == 's':
            # Aquí deberías validar si 'last_user' es un usuario válido del sistema
            # Por ahora, lo aceptamos.
            current_user = last_user
            print(f"Usuario actual: {current_user}")
            return

    while not current_user:
        username = input("Ingrese su nombre de usuario: ").strip()
        if not username:
            print("El nombre de usuario no puede estar vacío.")
            continue
        # Aquí deberías validar si 'username' existe en tu sistema de usuarios
        # (ej. en una hoja 'Usuarios' de Google Sheets).
        # Por ahora, aceptamos cualquier nombre.
        current_user = username
        auth.guardar_usuario_actual_local(current_user) # Guardar para la próxima vez
        print(f"Usuario actual establecido: {current_user}")


def check_active_cash_session():
    global current_session_id
    display_header()
    print("\nVerificando estado de caja...")
    sesion_abierta = apertura_cierre.obtener_estado_caja_actual()
    if sesion_abierta:
        current_session_id = int(sesion_abierta.get('ID_Sesion')) # Asegurar int
        print(f"Hay una caja abierta. Sesión ID: {current_session_id}")
        print(f"  Abierta por: {sesion_abierta.get('UsuarioApertura')} el {sesion_abierta.get('FechaApertura')} a las {sesion_abierta.get('HoraApertura')}")
        print(f"  Saldo Inicial: {sesion_abierta.get('SaldoInicial')}")
    else:
        current_session_id = None
        print("No hay ninguna caja abierta actualmente.")


def menu_abrir_caja():
    global current_session_id
    if not current_user:
        print("Error: Debe identificarse un usuario primero.")
        set_current_user()
        if not current_user: return

    display_header()
    if current_session_id:
        print(f"Error: Ya hay una caja abierta (Sesión ID: {current_session_id}). No se puede abrir otra.")
        return

    print("\n--- Abrir Caja ---")
    try:
        saldo_inicial_str = input("Ingrese el saldo inicial de caja: ")
        saldo_inicial = float(saldo_inicial_str.replace(',', '.'))
        if saldo_inicial < 0:
            print("El saldo inicial no puede ser negativo.")
            return
    except ValueError:
        print("Error: Saldo inicial inválido. Debe ser un número.")
        return

    resultado = apertura_cierre.abrir_caja(saldo_inicial=saldo_inicial, usuario=current_user)
    print(resultado.get("message"))
    if resultado["status"] == "success":
        current_session_id = resultado["id_sesion"]


def menu_registrar_venta():
    if not current_user:
        print("Error: Debe identificarse un usuario primero."); set_current_user();
        if not current_user: return
    if not current_session_id:
        print("Error: No hay una caja abierta. Abra una caja primero."); return

    display_header()
    print("\n--- Registrar Venta ---")
    
    # Selección de cliente
    id_cliente = input("Ingrese ID o nombre del cliente (dejar vacío para Público General): ")
    cliente_nombre = cliente_publico.obtener_cliente_para_venta(id_cliente if id_cliente else None)
    print(f"Cliente seleccionado: {cliente_nombre}")

    articulos_vendidos = []
    continuar_agregando = True
    while continuar_agregando:
        print(f"\nAgregando artículo {len(articulos_vendidos) + 1}:")
        id_articulo = input("  ID Artículo: ")
        # Aquí podrías tener una función que busque el artículo y su precio en la hoja de Stock
        # Por ahora, pedimos los datos manualmente
        nombre_articulo = input("  Nombre Artículo: ")
        try:
            cantidad = int(input("  Cantidad: "))
            precio_unitario = float(input("  Precio Unitario: ").replace(',', '.'))
            if cantidad <= 0 or precio_unitario < 0:
                print("Cantidad y precio deben ser positivos.")
                continue
        except ValueError:
            print("Cantidad o precio inválido.")
            continue
        
        subtotal = cantidad * precio_unitario
        articulos_vendidos.append({
            "id_articulo": id_articulo,
            "nombre": nombre_articulo, # Idealmente se obtiene del stock
            "cantidad": cantidad,
            "precio_unitario": precio_unitario,
            "subtotal": subtotal
        })
        if input("¿Agregar otro artículo? (s/n): ").lower() != 's':
            continuar_agregando = False

    if not articulos_vendidos:
        print("No se agregaron artículos. Venta cancelada.")
        return

    total_venta = sum(item['subtotal'] for item in articulos_vendidos)
    print(f"\nTotal de la Venta: ${total_venta:.2f}")

    metodo_pago = input("Método de pago (EJ: EFECTIVO, TARJETA, TRANSFERENCIA): ").upper()
    monto_recibido_str = input(f"Monto recibido ({metodo_pago}): ")
    try:
        monto_recibido = float(monto_recibido_str.replace(',', '.'))
    except ValueError:
        print("Monto recibido inválido.")
        return

    # Calculadora de vuelto
    vuelto = calcular_vuelto(total_venta, monto_recibido, metodo_pago)
    if vuelto is None and metodo_pago == "EFECTIVO" and monto_recibido < total_venta : # Si es None porque faltó dinero
        print("Pago insuficiente. Venta no registrada.")
        return
    
    confirmar = input("¿Confirmar y registrar esta venta? (s/n): ").lower()
    if confirmar == 's':
        resultado = registro_caja.registrar_venta(
            id_sesion_caja=current_session_id,
            articulos_vendidos=articulos_vendidos,
            cliente=cliente_nombre,
            metodo_pago=metodo_pago,
            usuario=current_user,
            total_venta=total_venta
        )
        print(resultado.get("message"))
    else:
        print("Venta cancelada por el usuario.")

def menu_registrar_movimiento_caja(tipo_movimiento: str):
    if not current_user:
        print("Error: Debe identificarse un usuario primero."); set_current_user();
        if not current_user: return
    if not current_session_id:
        print("Error: No hay una caja abierta. Abra una caja primero."); return

    display_header()
    print(f"\n--- Registrar {tipo_movimiento.capitalize()} de Caja ---")
    descripcion = input(f"Descripción del {tipo_movimiento}: ")
    try:
        monto_str = input(f"Monto del {tipo_movimiento}: ")
        monto = float(monto_str.replace(',', '.'))
        if monto <= 0:
            print("El monto debe ser positivo.")
            return
    except ValueError:
        print("Monto inválido.")
        return

    resultado = registro_caja.registrar_movimiento(
        id_sesion_caja=current_session_id,
        tipo_movimiento=tipo_movimiento.upper(),
        descripcion=descripcion,
        monto=monto,
        usuario=current_user
    )
    print(resultado.get("message"))


def menu_cerrar_caja():
    global current_session_id
    if not current_user:
        print("Error: Debe identificarse un usuario primero."); set_current_user();
        if not current_user: return
    if not current_session_id:
        print("Error: No hay una caja abierta para cerrar."); return

    display_header()
    print("\n--- Cerrar Caja ---")
    print("¡ATENCIÓN! Para cerrar la caja se requiere TOKEN DE ADMINISTRADOR.")

    if not auth.solicitar_y_verificar_admin_token():
        print("Autorización fallida. No se puede cerrar la caja.")
        return

    try:
        saldo_final_str = input("Ingrese el SALDO FINAL CONTADO en caja (dinero real): ")
        saldo_final_contado = float(saldo_final_str.replace(',', '.'))
        if saldo_final_contado < 0:
            print("El saldo final no puede ser negativo.")
            return
    except ValueError:
        print("Saldo final inválido.")
        return

    # Opcional: Calcular saldo teórico esperado sumando movimientos de la sesión
    # Esto es más complejo y requiere leer todos los registros de la sesión actual.
    # saldo_teorico = calcular_saldo_teorico(current_session_id) # Función a implementar

    resultado = apertura_cierre.cerrar_caja(
        id_sesion=current_session_id,
        saldo_final_contado=saldo_final_contado,
        usuario_cierre=current_user # Quién está operando el sistema al cerrar
        # saldo_teorico_esperado=saldo_teorico # Si lo calculas
    )
    print(resultado.get("message"))
    if resultado["status"] == "success":
        current_session_id = None # La caja ya no está activa

def menu_configurar_horarios_caja():
    if not current_user:
        print("Error: Debe identificarse un usuario primero."); set_current_user();
        if not current_user: return

    display_header()
    print("\n--- Configurar Horarios de Apertura/Cierre Automático ---")
    print("¡ATENCIÓN! Esta acción requiere TOKEN DE ADMINISTRADOR.")

    if not auth.solicitar_y_verificar_admin_token():
        print("Autorización fallida.")
        return

    # Lógica para configurar horarios (guardar en SHEET_NAME_CONFIG_HORARIOS)
    # Por ejemplo: Lunes-Apertura: 08:00, Lunes-Cierre: 20:00, etc.
    print("Configuración de horarios (funcionalidad placeholder):")
    try:
        g_handler = GoogleSheetsHandler()
        ws_config = g_handler.get_worksheet(SHEET_NAME_CONFIG_HORARIOS)
        if not ws_config:
            print(f"Creando hoja '{SHEET_NAME_CONFIG_HORARIOS}' para configuración...")
            # g_handler.sheet.add_worksheet(title=SHEET_NAME_CONFIG_HORARIOS, rows="10", cols="5")
            # ws_config = g_handler.get_worksheet(SHEET_NAME_CONFIG_HORARIOS)
            # ws_config.append_row(["Dia", "Tipo", "Hora", "Activado"]) # Cabeceras
            print("Hoja de configuración de horarios no existe y la creación automática no está implementada aquí.")
            print("Por favor, cree la hoja manualmente con columnas: Dia, Tipo (Apertura/Cierre), Hora (HH:MM), Activado (SI/NO)")
            return

        print("Horarios actuales (si existen):")
        records = ws_config.get_all_records()
        for rec in records:
            print(f"  - {rec.get('Dia')} {rec.get('Tipo')}: {rec.get('Hora')} (Activado: {rec.get('Activado')})")

        dia = input("Día (Lunes, Martes, ..., Domingo, TODOS): ").capitalize()
        tipo_op = input("Tipo (Apertura/Cierre): ").capitalize()
        hora = input("Hora (HH:MM, ej. 08:00): ")
        activado = input("¿Activar este horario? (SI/NO): ").upper()

        # Validaciones básicas (puedes expandir)
        if dia not in ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo", "Todos"]:
            print("Día inválido."); return
        if tipo_op not in ["Apertura", "Cierre"]:
            print("Tipo de operación inválido."); return
        try:
            datetime.strptime(hora, "%H:%M")
        except ValueError:
            print("Formato de hora inválido."); return
        if activado not in ["SI", "NO"]:
            print("Valor para 'Activado' inválido."); return

        # Aquí buscarías si ya existe una configuración para ese día y tipo para actualizarla,
        # o agregar una nueva fila.
        # Por simplicidad, solo agregamos:
        ws_config.append_row([dia, tipo_op, hora, activado])
        print("Horario guardado/actualizado.")
        print("NOTA: La ejecución automática de estos horarios requiere un programador de tareas externo.")

    except Exception as e:
        print(f"Error configurando horarios: {e}")


def menu_imprimir_facturas_dia():
    # from gestion import fiscal # Mover import aquí para evitar error si el módulo no existe aún
    # Este import se movió al inicio del archivo `main.py` para que esté disponible
    # pero se comenta si el módulo `fiscal` aún no está completamente definido o da problemas.
    # Asegúrate de crear `gestion/fiscal.py` con las funciones `obtener_facturas_del_dia_para_imprimir` y `enviar_facturas_a_impresora_fiscal`.
    # Si no está listo, puedes comentar esta opción del menú o la llamada.
    try:
        from gestion import fiscal
    except ImportError:
        print("Módulo 'fiscal' no encontrado o con errores. Función no disponible.")
        return

    if not current_user:
        print("Error: Debe identificarse un usuario primero."); set_current_user();
        if not current_user: return
    if not current_session_id:
        print("Error: No hay una sesión de caja activa para obtener facturas."); return

    display_header()
    print("\n--- Imprimir Facturas del Día (Sesión Actual) ---")
    # No requiere token de admin para imprimir, pero sí para reimprimir o anular (no implementado)

    facturas = fiscal.obtener_facturas_del_dia_para_imprimir(current_session_id)
    if facturas:
        print(f"Se encontraron {len(facturas)} facturas.")
        confirmar = input("¿Desea enviarlas a la impresora fiscal? (s/n): ").lower()
        if confirmar == 's':
            resultado = fiscal.enviar_facturas_a_impresora_fiscal(facturas)
            print(resultado.get("message"))
    else:
        print("No se encontraron facturas para la sesión actual para imprimir.")


def menu_admin_operaciones():
    display_header()
    print("\n--- Operaciones de Administrador ---")
    print("¡ATENCIÓN! Estas acciones requieren TOKEN DE ADMINISTRADOR.")

    if not auth.solicitar_y_verificar_admin_token():
        print("Autorización fallida.")
        return

    while True:
        display_header() # Mostrar usuario y sesión
        print("\n--- Menú Administrador ---")
        print("1. Forzar generación de nuevo Token de Administrador")
        print("2. Eliminar registro de caja (¡PELIGROSO!)")
        # print("3. Modificar horario de apertura/cierre (ya en menú principal con token)")
        print("0. Volver al menú principal")
        
        op_admin = input("Seleccione una opción de administrador: ")

        if op_admin == '1':
            nuevo_token = auth.generar_y_guardar_admin_token(forzar_nuevo=True)
            print(f"Se ha generado un nuevo token de administrador: {nuevo_token}")
            print("El token anterior ya no es válido.")
            input("Presione Enter para continuar...")
        elif op_admin == '2':
            print("Eliminar registro de caja (Funcionalidad NO IMPLEMENTADA AÚN)")
            print("Esta acción es muy delicada y requiere cuidado.")
            # Lógica:
            # 1. Pedir ID del registro a eliminar (de la hoja CajaRegistros)
            # 2. Confirmar fuertemente la acción.
            # 3. g_handler.delete_row(SHEET_NAME_CAJA_MOVIMIENTOS, row_index) o similar
            # 4. Registrar esta eliminación en un log de auditoría.
            input("Presione Enter para continuar...")
        elif op_admin == '0':
            break
        else:
            print("Opción no válida.")

def main_loop():
    global current_user, current_session_id

    # Generar/cargar token de admin al inicio (solo para que exista, el admin lo "conoce")
    auth.generar_y_guardar_admin_token()

    set_current_user()
    check_active_cash_session() # Verificar si ya hay una caja abierta al iniciar

    while True:
        display_header()
        print("\n--- Menú Principal ---")
        if not current_session_id:
            print("1. Abrir Caja")
        else:
            print(f"AVISO: Caja ABIERTA (Sesión ID: {current_session_id})")
            print("2. Registrar Venta")
            print("3. Registrar Ingreso de Caja")
            print("4. Registrar Egreso de Caja")
            print("5. Cerrar Caja")
            print("6. Imprimir Facturas del Día (Sesión Actual)")

        print("7. Cambiar Usuario")
        print("8. Configurar Horarios de Apertura/Cierre (Admin)")
        print("9. Operaciones de Administrador (Admin)")
        print("0. Salir")
        
        opcion = input("Seleccione una opción: ")

        if opcion == '1' and not current_session_id:
            menu_abrir_caja()
        elif opcion == '2' and current_session_id:
            menu_registrar_venta()
        elif opcion == '3' and current_session_id:
            menu_registrar_movimiento_caja("INGRESO")
        elif opcion == '4' and current_session_id:
            menu_registrar_movimiento_caja("EGRESO")
        elif opcion == '5' and current_session_id:
            menu_cerrar_caja()
        elif opcion == '6' and current_session_id:
            menu_imprimir_facturas_dia()
        elif opcion == '7':
            set_current_user()
            # Al cambiar de usuario, no cambiamos la sesión de caja si está abierta,
            # ya que la caja pertenece a la apertura, no al usuario que la opera momentáneamente.
            # Las operaciones se registrarán con el nuevo 'current_user'.
        elif opcion == '8':
            menu_configurar_horarios_caja()
        elif opcion == '9':
            menu_admin_operaciones()
        elif opcion == '0':
            print("Saliendo del sistema...")
            break
        else:
            print("Opción no válida. Intente de nuevo.")
        
        if opcion not in ['7', '8', '9', '0']: # Para no recargar estado de caja innecesariamente
            check_active_cash_session() # Actualizar estado de la sesión por si cambió

        input("\nPresione Enter para continuar...")


if __name__ == "__main__":
    if not GOOGLE_SHEET_ID:
        print("Error Crítico: GOOGLE_SHEET_ID no está configurado en .env o config.py")
        print("El sistema no puede funcionar sin esto.")
        sys.exit(1)
    try:
        # Intento de conexión inicial para verificar credenciales y Sheet ID
        print("Verificando conexión inicial a Google Sheets...")
        g_handler_test = GoogleSheetsHandler()
        if not g_handler_test.client:
            print("Fallo en la conexión inicial a Google Sheets. Verifique credenciales y Sheet ID.")
            sys.exit(1)
        print("Conexión a Google Sheets verificada.")
        # Aquí también podrías verificar la existencia de las hojas principales.
    except FileNotFoundError as fnf_error:
        print(f"Error de archivo de credenciales: {fnf_error}")
        sys.exit(1)
    except ValueError as val_error:
        print(f"Error de configuración: {val_error}")
        sys.exit(1)
    except Exception as e:
        print(f"Error inesperado durante la inicialización: {e}")
        # sys.exit(1) # Podrías salir, o intentar continuar si no es crítico

    main_loop()