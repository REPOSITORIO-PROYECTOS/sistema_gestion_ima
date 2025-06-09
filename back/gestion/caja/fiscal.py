# gestion/fiscal.py
import win32com.client # Para interactuar con OCX en Windows
import time
import pywintypes # Para manejar errores COM

# ProgID del OCX de Epson. ¡DEBES OBTENER EL CORRECTO DE LA DOCUMENTACIÓN DE EPSON!
# Estos son solo ejemplos comunes, pueden variar.
# EPSON_OCX_PROGID = "EPSONFiscalDriver.Printer"
EPSON_OCX_PROGID = "IFiscal.EpsonFiscal" # Otro ProgID que ha sido usado por Epson

# Estado de conexión global para el objeto de la impresora
epson_printer_obj = None

def conectar_epson_fiscal(puerto_com="COM1", velocidad_baudios=9600):
    """
    Establece la conexión con la impresora fiscal Epson TM-T900FA.
    Los parámetros de puerto y velocidad pueden variar o ser manejados por el driver.
    Consulta la documentación de Epson para los métodos exactos y sus parámetros.
    """
    global epson_printer_obj
    if epson_printer_obj:
        print("Ya existe una conexión con la impresora Epson.")
        return epson_printer_obj

    try:
        print(f"Intentando conectar a Epson Fiscal con ProgID: {EPSON_OCX_PROGID}")
        epson_printer_obj = win32com.client.Dispatch(EPSON_OCX_PROGID)
        print("Objeto OCX Epson creado.")

        # --- Métodos de Conexión (EJEMPLOS - VERIFICAR CON DOCUMENTACIÓN EPSON) ---
        # Algunas versiones del driver Epson manejan el puerto automáticamente o
        # lo configuras en la utilidad de configuración del driver.
        # Otras pueden requerir que especifiques el puerto.

        # Ejemplo 1: Si el OCX tiene un método Connect o OpenPort
        # epson_printer_obj.OpenPort(puerto_com, velocidad_baudios) # Nombre y parámetros ficticios
        # print(f"Puerto {puerto_com} abierto a {velocidad_baudios} baudios.")

        # Ejemplo 2: Si el OCX requiere inicializar
        # epson_printer_obj.Initialize() # Nombre ficticio

        # Ejemplo 3: O simplemente al crearlo ya está listo y se configura el puerto
        # desde el panel de control del driver fiscal Epson.
        # Este es a menudo el caso: el driver se encarga de la comunicación de bajo nivel.

        # Verificar estado (método ficticio, consultar documentación Epson)
        # status_code = epson_printer_obj.GetPrinterStatus()
        # print(f"Estado inicial de la impresora: {status_code}")
        # if status_code != 0: # Asumiendo 0 es OK
        #     raise Exception(f"Impresora Epson no lista. Estado: {status_code} - {epson_printer_obj.GetLastErrorMessage()}")

        print("Conexión con impresora fiscal Epson establecida (o lista para usar).")
        return epson_printer_obj
    except pywintypes.com_error as e:
        print(f"Error COM al instanciar o usar el OCX Epson: {e}")
        print(f"Verifica que el driver fiscal Epson esté instalado y el ProgID '{EPSON_OCX_PROGID}' sea correcto.")
        epson_printer_obj = None
        return None
    except Exception as e:
        print(f"Error al conectar con la impresora fiscal Epson: {e}")
        epson_printer_obj = None
        return None

def desconectar_epson_fiscal():
    """Cierra la conexión con la impresora fiscal Epson."""
    global epson_printer_obj
    if epson_printer_obj:
        try:
            # --- Métodos de Desconexión (EJEMPLOS - VERIFICAR CON DOCUMENTACIÓN EPSON) ---
            # epson_printer_obj.ClosePort() # Nombre ficticio
            # epson_printer_obj.Finalize() # Nombre ficticio
            print("Conexión con impresora fiscal Epson cerrada.")
        except Exception as e:
            print(f"Error al desconectar la impresora Epson: {e}")
        finally:
            epson_printer_obj = None # Liberar el objeto
    else:
        print("No había conexión activa con la impresora Epson para cerrar.")


def emitir_factura_epson(factura_data: dict):
    """
    Emite una factura utilizando el OCX de la Epson TM-T900FA.
    factura_data: Diccionario con los datos de la factura.
    ¡LOS NOMBRES DE LOS MÉTODOS Y PARÁMETROS SON EJEMPLOS! DEBES USAR LOS REALES DE EPSON.
    """
    global epson_printer_obj
    if not epson_printer_obj:
        print("Error: Impresora Epson no conectada. Llama a conectar_epson_fiscal() primero.")
        return False

    try:
        # --- TIPO DE COMPROBANTE ---
        # Los códigos de tipo de comprobante los define AFIP y el driver Epson.
        # Ej: "T" (Ticket), "B" (Factura B), "A" (Factura A), "NDB", "NDC", etc.
        tipo_comprobante_epson = "T" # Por defecto Ticket (Consumidor Final)
        if factura_data.get("tipo_afip", "").upper() == "FACTURA_B": # Suponiendo que tienes un campo así
            tipo_comprobante_epson = "B"
        elif factura_data.get("tipo_afip", "").upper() == "FACTURA_A":
            tipo_comprobante_epson = "A"
        # ... otros tipos

        # epson_printer_obj.OpenFiscalReceipt(tipo_comprobante_epson)
        # O métodos más específicos como:
        # epson_printer_obj.AbrirComprobante("TICKETFACTURA","B") # Parámetros ficticios

        # --- DATOS DEL CLIENTE (si no es consumidor final anónimo) ---
        # epson_printer_obj.SetCustomerData(
        #     factura_data.get('cliente_nombre', 'Consumidor Final'),
        #     factura_data.get('cliente_cuit_o_dni', '0'), # CUIT, DNI, o "0"
        #     factura_data.get('cliente_iva_condicion', 'CONSUMIDOR_FINAL'), # Ej: "RESPONSABLE_INSCRIPTO"
        #     factura_data.get('cliente_domicilio', 'S/D')
        # )

        # --- ITEMS ---
        for item in factura_data.get('items', []):
            # epson_printer_obj.PrintLineItem(
            #     item.get('nombre', 'Producto'),
            #     item.get('cantidad', 1.0),
            #     item.get('precio_unitario', 0.0), # Precio unitario SIN IVA o CON IVA según pida el driver
            #     item.get('tasa_iva', 21.00), # Ej: 21.00 para 21%, 10.50 para 10.5%, 0.00 para exento
            #     "Unidad", # Unidad de medida
            #     "M", # "M" para monto, "B" para bonificación (ver doc Epson)
            #     0.0, # Impuestos internos (si aplica)
            #     item.get('codigo_interno', '')
            # )
            print(f"  DEBUG (Epson): Imprimiendo Item: {item.get('nombre')}, Cant: {item.get('cantidad')}, Precio: {item.get('precio_unitario')}, IVA: {item.get('tasa_iva', 21.0)}")
            time.sleep(0.1) # Pequeña pausa, a veces ayuda

        # --- SUBTOTALES Y DESCUENTOS (si los hay y el driver lo maneja así) ---
        # epson_printer_obj.PrintSubtotal()
        # epson_printer_obj.GeneralDiscount("Descuento general", 10.00, "M") # Monto o porcentaje

        # --- PAGOS ---
        # El driver Epson usualmente permite múltiples formas de pago.
        # epson_printer_obj.AddPayment(
        #     factura_data.get('metodo_pago_descripcion', 'Efectivo'), # Descripción para el ticket
        #     factura_data.get('total', 0.0), # Monto del pago
        #     factura_data.get('metodo_pago_codigo_epson', '0') # Código de forma de pago según Epson
        # )
        print(f"  DEBUG (Epson): Agregando Pago: {factura_data.get('metodo_pago', 'EFECTIVO')}, Monto: {factura_data.get('total', 0.0)}")

        # --- CERRAR COMPROBANTE ---
        # epson_printer_obj.CloseFiscalReceipt()
        print("  DEBUG (Epson): Cerrando comprobante fiscal.")

        # Manejo de errores específico del OCX
        # if epson_printer_obj.GetLastFiscalError() != 0:
        #    error_msg = epson_printer_obj.GetLastFiscalErrorMessage()
        #    raise Exception(f"Error fiscal Epson: {error_msg}")

        print(f"Factura para {factura_data.get('cliente', 'Consumidor Final')} (simulada para Epson) enviada.")
        return True

    except pywintypes.com_error as e:
        print(f"Error COM durante la emisión de factura Epson: {e}")
        # Intentar cancelar el comprobante si es posible
        # try: epson_printer_obj.CancelDocument() # Método ficticio
        # except: pass
        return False
    except Exception as e:
        print(f"Error al emitir factura con Epson: {e}")
        return False

def obtener_estado_impresora_epson():
    """Obtiene y muestra el estado de la impresora fiscal Epson."""
    global epson_printer_obj
    if not epson_printer_obj:
        print("Impresora Epson no conectada.")
        return None
    try:
        # --- MÉTODO PARA OBTENER ESTADO (EJEMPLO - VERIFICAR CON DOC EPSON) ---
        # status_code_printer = epson_printer_obj.GetPrinterStatus()
        # status_code_fiscal = epson_printer_obj.GetFiscalStatus()
        # status_message = epson_printer_obj.GetStatusDescription(status_code_printer) # Ficticio

        # print(f"Estado Impresora Epson: Código Printer={status_code_printer}, Código Fiscal={status_code_fiscal}")
        # print(f"Mensaje Estado: {status_message}")
        # return {"printer_status": status_code_printer, "fiscal_status": status_code_fiscal, "message": status_message}
        print("DEBUG (Epson): Obteniendo estado (simulado).")
        return {"printer_status": 0, "fiscal_status": 0, "message": "OK (Simulado)"}

    except Exception as e:
        print(f"Error al obtener estado de la impresora Epson: {e}")
        return None

# La función `obtener_facturas_del_dia_para_imprimir()` que ya tenías, se mantiene igual.
# ... (tu función existente) ...

def enviar_facturas_a_impresora_fiscal(lista_facturas_del_dia: list):
    """
    Función principal para enviar una lista de facturas a la Epson TM-T900FA.
    """
    print("\n--- Enviando Facturas a Impresora Fiscal Epson TM-T900FA ---")
    if not lista_facturas_del_dia:
        print("No hay facturas para imprimir.")
        return {"status": "warning", "message": "No hay facturas."}

    # Conectar solo una vez al inicio
    if not epson_printer_obj:
        if not conectar_epson_fiscal(): # Intenta conectar
            return {"status": "error", "message": "Fallo al conectar con la impresora Epson."}

    # Verificar estado antes de empezar
    estado_inicial = obtener_estado_impresora_epson()
    if estado_inicial and (estado_inicial.get("printer_status") != 0 or estado_inicial.get("fiscal_status") != 0):
         print(f"Impresora Epson no está lista. Estado: {estado_inicial.get('message')}")
         # desconectar_epson_fiscal() # Desconectar si no se pudo operar
         return {"status": "error", "message": f"Impresora no lista: {estado_inicial.get('message')}"}


    exitos = 0
    errores = 0
    for i, factura_data in enumerate(lista_facturas_del_dia):
        print(f"\nProcesando factura {i+1}/{len(lista_facturas_del_dia)} para {factura_data.get('cliente')} - Total: ${factura_data.get('total'):.2f}")
        
        # Adaptar `factura_data` si es necesario para que coincida con lo que espera `emitir_factura_epson`
        # Por ejemplo, si necesitas el CUIT para Factura A, asegúrate de que esté en `factura_data`.
        # También, el precio unitario podría necesitar ser enviado SIN IVA, y el OCX calcula el IVA. ¡VER DOC!

        if emitir_factura_epson(factura_data):
            exitos += 1
            print("Factura emitida correctamente.")
        else:
            errores += 1
            print(f"Error al emitir factura para {factura_data.get('cliente')}. Verifique la impresora y el log.")
            # Opcional: Preguntar si continuar o abortar
            # if input("Hubo un error. ¿Continuar con las siguientes facturas? (s/n): ").lower() != 's':
            #     print("Proceso de impresión abortado por el usuario.")
            #     break
        
        # Es buena práctica verificar el estado de la impresora después de cada operación
        # estado_actual = obtener_estado_impresora_epson()
        # if estado_actual and (estado_actual.get("printer_status") != 0 or estado_actual.get("fiscal_status") != 0):
        #    print(f"Error en impresora después de la factura {i+1}. Estado: {estado_actual.get('message')}")
        #    break # Detener si la impresora entra en error

        time.sleep(1) # Pausa entre facturas

    # Desconectar al final si todas las operaciones terminaron o si se usó de forma transaccional
    # Si la conexión es persistente durante la ejecución del programa, no desconectar aquí.
    # Por ahora, la dejamos conectada si se logró conectar, para el próximo uso.
    # desconectar_epson_fiscal()

    if errores > 0:
        message = f"{exitos} facturas enviadas. {errores} facturas con error."
        status = "partial_success" if exitos > 0 else "error"
    else:
        message = f"Todas las {exitos} facturas enviadas exitosamente a Epson."
        status = "success"
    
    return {"status": status, "message": message}