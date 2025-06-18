# back/utils/setup_sheets.py
import sys
import os
import gspread

# --- Configuración del Path para importaciones ---
current_dir = os.path.dirname(os.path.abspath(__file__))
back_dir = os.path.dirname(current_dir)
project_root_dir = os.path.dirname(back_dir)
if project_root_dir not in sys.path:
    sys.path.insert(0, project_root_dir)
# --- Fin Configuración del Path ---

try:
    # Importar las variables de config.py que definen los NOMBRES de las hojas
    from back.config import (
        CONFIGURACION_GLOBAL_SHEET, USUARIOS_SHEET, TERCEROS_SHEET, ARTICULOS_SHEET,
        CAJA_SESIONES_SHEET, CAJA_MOVIMIENTOS_SHEET, STOCK_MOVIMIENTOS_SHEET,
        COMPRAS_CABECERA_SHEET, COMPRAS_DETALLE_SHEET,
        # VENTAS_CABECERA_SHEET, VENTAS_DETALLE_SHEET, VENTAS_PAGOS_SHEET, # Si las usas
        # ADMIN_TOKEN_SHEET, # Si la usas
        # STOCK_LISTAS_CONFIG_SHEET, # Si la usas
        # CONTABILIDAD_PLAN_SHEET, CONTABILIDAD_ASIENTOS_SHEET, # Si la usas
    )
    from back.utils.sheets_google_handler import GoogleSheetsHandler
except ImportError as e:
    print(f"Error al importar módulos necesarios: {e}")
    print("Asegúrate de que config.py y sheets_google_handler.py estén correctos y accesibles.")
    sys.exit(1)
except FileNotFoundError as e:
    print(f"Error crítico de configuración al iniciar (FileNotFound): {e}")
    sys.exit(1)
except ValueError as e:
    print(f"Error crítico de configuración al iniciar (ValueError): {e}")
    sys.exit(1)
except Exception as e_general_import:
    print(f"Error general durante la importación: {e_general_import}")
    sys.exit(1)


def crear_hojas_y_cabeceras_propuestas():
    print("Iniciando la creación/verificación de hojas de cálculo según la estructura propuesta...")
    try:
        handler = GoogleSheetsHandler()
        if not handler.client or not handler.spreadsheet:
            print("No se pudo establecer la conexión con Google Sheets. Abortando.")
            return
    except Exception as e:
        print(f"Error al inicializar GoogleSheetsHandler: {e}")
        print("Verifica tu GOOGLE_SHEET_ID y el archivo de credenciales en .env y config.py.")
        return

    # Mapa de descripción lógica a la VARIABLE de config.py que contiene el nombre real de la hoja
    hojas_a_procesar_mapa = {
        "1. Configuración Global": CONFIGURACION_GLOBAL_SHEET,
        "2. Usuarios del Sistema": USUARIOS_SHEET,
        "3. Terceros (Clientes/Proveedores)": TERCEROS_SHEET,
        "4. Catálogo de Artículos": ARTICULOS_SHEET,
        "5. Sesiones de Caja": CAJA_SESIONES_SHEET,
        "6. Movimientos de Caja": CAJA_MOVIMIENTOS_SHEET,
        "7. Movimientos de Stock": STOCK_MOVIMIENTOS_SHEET,
        "8. Documentos de Compra (Cabeceras)": COMPRAS_CABECERA_SHEET,
        "9. Detalle de Documentos de Compra": COMPRAS_DETALLE_SHEET,
        # ---- DESCOMENTA Y AJUSTA SI LAS USAS ----
        # "10. Documentos de Venta (Cabeceras)": VENTAS_CABECERA_SHEET,
        # "11. Detalle de Documentos de Venta": VENTAS_DETALLE_SHEET,
        # "12. Pagos de Ventas": VENTAS_PAGOS_SHEET,
        # "13. Tokens de Administrador (si hoja separada)": ADMIN_TOKEN_SHEET,
        # "14. Configuración de Listas de Stock": STOCK_LISTAS_CONFIG_SHEET,
        # "15. Plan de Cuentas Contable": CONTABILIDAD_PLAN_SHEET,
        # "16. Asientos Contables": CONTABILIDAD_ASIENTOS_SHEET,
    }

    hojas_creadas_ok = 0
    hojas_existentes_ok = 0
    hojas_con_error_creacion = 0
    hojas_con_error_cabeceras = 0
    hojas_saltadas = 0

    print("\n--- Inicio del Proceso de Hojas ---")
    for descripcion_logica, nombre_hoja_real_valor in sorted(hojas_a_procesar_mapa.items()):
        print(f"\nProcesando: '{descripcion_logica}' (Nombre real target: '{nombre_hoja_real_valor}')...")

        if not nombre_hoja_real_valor or nombre_hoja_real_valor.endswith("_Default"):
            print(f"  SALTANDO: El nombre para '{descripcion_logica}' ('{nombre_hoja_real_valor}') es un default. Define la clave correspondiente en .env con el nombre real de la hoja.")
            hojas_saltadas += 1
            continue

        worksheet = None
        try:
            worksheet = handler.spreadsheet.worksheet(nombre_hoja_real_valor)
            print(f"  INFO: Hoja '{nombre_hoja_real_valor}' ya existe.")
            hojas_existentes_ok +=1
            # Verificar y añadir cabeceras si A1 está vacía
            if not worksheet.acell('A1', value_render_option='UNFORMATTED_VALUE').value: # Comprobar si A1 tiene contenido
                print(f"  INFO: Hoja '{nombre_hoja_real_valor}' existe pero A1 está vacía. Intentando añadir cabeceras...")
                headers = handler.get_default_headers(nombre_hoja_real_valor)
                if headers:
                    worksheet.update('A1', [headers], value_input_option='USER_ENTERED')
                    worksheet.freeze(rows=1)
                    print(f"  ÉXITO: Cabeceras añadidas a la hoja existente '{nombre_hoja_real_valor}'.")
                else:
                    print(f"  ADVERTENCIA: No se definieron cabeceras para '{nombre_hoja_real_valor}' en get_default_headers. No se añadieron.")
                    hojas_con_error_cabeceras +=1
            else:
                print(f"  INFO: Hoja '{nombre_hoja_real_valor}' ya tiene contenido en A1, se asume que tiene cabeceras.")

        except gspread.exceptions.WorksheetNotFound:
            print(f"  INFO: Hoja '{nombre_hoja_real_valor}' no encontrada. Creándola...")
            headers = handler.get_default_headers(nombre_hoja_real_valor)
            if not headers:
                print(f"  ERROR: No se pueden crear cabeceras para la nueva hoja '{nombre_hoja_real_valor}' (no definidas en get_default_headers). Hoja NO creada.")
                hojas_con_error_creacion += 1
                continue
            try:
                num_cols = len(headers) if headers else 20 # Mínimo 20 columnas si no hay headers definidos
                new_worksheet = handler.spreadsheet.add_worksheet(title=nombre_hoja_real_valor, rows="100", cols=str(num_cols))
                if headers: # Solo escribir si hay cabeceras
                    new_worksheet.update('A1', [headers], value_input_option='USER_ENTERED')
                    new_worksheet.freeze(rows=1)
                print(f"  ÉXITO: Hoja '{nombre_hoja_real_valor}' creada con cabeceras.")
                hojas_creadas_ok += 1
            except Exception as e_create:
                print(f"  ERROR: No se pudo crear la hoja '{nombre_hoja_real_valor}': {e_create}")
                hojas_con_error_creacion += 1
        except Exception as e_general:
            print(f"  ERROR: Error inesperado procesando la hoja '{nombre_hoja_real_valor}': {e_general}")
            hojas_con_error_creacion += 1 # Contar como error de creación si falla la verificación

    print("\n--- Resumen de Creación/Verificación de Hojas ---")
    print(f"Hojas nuevas creadas exitosamente: {hojas_creadas_ok}")
    print(f"Hojas existentes verificadas (y cabeceras añadidas si fue necesario): {hojas_existentes_ok}")
    print(f"Hojas saltadas (nombre default o no definido en .env): {hojas_saltadas}")
    print(f"Hojas con error durante la creación: {hojas_con_error_creacion}")
    print(f"Hojas existentes a las que no se pudo añadir cabeceras (si aplica): {hojas_con_error_cabeceras}")

    total_errores = hojas_con_error_creacion + hojas_con_error_cabeceras
    if total_errores > 0:
        print("\nATENCIÓN: Algunas hojas no pudieron ser configuradas correctamente. Revisa los mensajes de error.")
    elif hojas_saltadas > 0:
        print("\nADVERTENCIA: Algunas hojas fueron saltadas. Asegúrate de definirlas correctamente en tu archivo .env (quitando '_Default' de su nombre en config.py o definiendo la clave ENV correspondiente).")
    else:
        print("\n¡Proceso completado! Todas las hojas especificadas deberían estar listas en tu Google Spreadsheet.")


if __name__ == "__main__":
    print("=======================================================")
    print("=== SCRIPT DE CONFIGURACIÓN DE HOJAS DE SPREADSHEET ===")
    print("=======================================================")
    # ... (resto del if __name__ == "__main__" sin cambios) ...
    print("Este script intentará conectar a tu Google Spreadsheet y crear las hojas")
    print("definidas en 'back/config.py' con sus cabeceras por defecto si no existen.")
    print("Asegúrate de que tu archivo '.env' esté configurado con GOOGLE_SHEET_ID")
    print("y que GOOGLE_SERVICE_ACCOUNT_FILE apunte a tu 'credencial_IA.json'.")
    print("Además, las claves como 'SHEET_NAME_CAJA_SESIONES' en .env deben tener los")
    print("nombres REALES que quieres para tus pestañas en Google Sheets.")
    print("-------------------------------------------------------")
    
    confirm = input("¿Deseas continuar y crear/verificar estas hojas? (s/n): ").lower()
    if confirm == 's':
        crear_hojas_y_cabeceras_propuestas()
    else:
        print("Operación cancelada por el usuario.")