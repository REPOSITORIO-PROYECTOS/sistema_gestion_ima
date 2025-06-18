# gestion/caja/apertura_cierre.py
import gspread
from datetime import datetime
from back.utils.sheets_google_handler import GoogleSheetsHandler
from back.config import SHEET_NAME_CAJA_SESIONES  # Usaremos este nombre de hoja configurado

# Inicializamos el handler una vez si se va a usar frecuentemente en este módulo
# O se puede instanciar dentro de cada función si se prefiere
# g_handler = GoogleSheetsHandler() # Descomentar si se define SHEET_ID y creds en .env

def abrir_caja(saldo_inicial: float, usuario: str):
    """
    Registra la apertura de caja en la hoja de cálculo.
    Asume una hoja con columnas: ID_Sesion, FechaApertura, HoraApertura, SaldoInicial, UsuarioApertura, Estado
    """
    try:
        g_handler = GoogleSheetsHandler() # Instanciar aquí para asegurar la última config
        if not g_handler.client:
            return {"status": "error", "message": "No se pudo conectar a Google Sheets."}

        # Verificar si ya hay una caja abierta (lógica a implementar)
        # Por ahora, simplemente añadimos la apertura
        # Podrías querer generar un ID_Sesion único

        now = datetime.now()
        fecha_apertura = now.strftime("%Y-%m-%d")
        hora_apertura = now.strftime("%H:%M:%S")
        estado = "ABIERTA"

        # Generar un ID de sesión simple (podrías hacerlo más robusto)
        # Por ejemplo, buscando el último ID y sumando 1, o usando un timestamp
        registros_sesiones = g_handler.get_all_records(SHEET_NAME_CAJA_SESIONES )
        ultimo_id = 0
        if registros_sesiones:
            try:
                # Asumiendo que la columna se llama 'ID_Sesion' y contiene números
                ultimo_id = max(int(r['ID_Sesion']) for r in registros_sesiones if r.get('ID_Sesion', '').isdigit())
            except (ValueError, TypeError):
                # Si hay valores no numéricos o la columna no existe en algunos registros
                print("Advertencia: No se pudo determinar el último ID_Sesion numérico. Usando timestamp.")
                ultimo_id = int(now.timestamp()) # Alternativa si falla la numeración
            except KeyError:
                print(f"Advertencia: La columna 'ID_Sesion' no existe en la hoja '{SHEET_NAME_CAJA_SESIONES }'. Usando timestamp.")
                ultimo_id = int(now.timestamp())

        id_sesion = ultimo_id + 1


        data_row = [id_sesion, fecha_apertura, hora_apertura, saldo_inicial, usuario, estado, "", "", "", ""] # Dejar espacio para cierre
        # Columnas esperadas: ID_Sesion, FechaApertura, HoraApertura, SaldoInicial, UsuarioApertura, Estado,
        #                     FechaCierre, HoraCierre, SaldoFinalContado, Diferencia

        if g_handler.append_row(SHEET_NAME_CAJA_SESIONES , data_row):
            print(f"Caja abierta por {usuario} con ${saldo_inicial:.2f}. ID Sesión: {id_sesion}")
            return {"status": "success", "id_sesion": id_sesion, "message": "Caja abierta exitosamente."}
        else:
            return {"status": "error", "message": "Error al registrar la apertura de caja en Google Sheets."}
    except Exception as e:
        print(f"Error en abrir_caja: {e}")
        return {"status": "error", "message": str(e)}


def cerrar_caja(id_sesion: int, saldo_final_contado: float, usuario_cierre: str, saldo_teorico_esperado: float = None):
    """
    Registra el cierre de caja, actualizando la fila de la sesión abierta.
    Busca la sesión por ID_Sesion y actualiza los campos de cierre y el estado.
    El token de admin se verifica ANTES de llamar a esta función.
    """
    try:
        g_handler = GoogleSheetsHandler()
        if not g_handler.client:
            return {"status": "error", "message": "No se pudo conectar a Google Sheets."}

        ws = g_handler.get_worksheet(SHEET_NAME_CAJA_SESIONES )
        if not ws:
            return {"status": "error", "message": f"Hoja '{SHEET_NAME_CAJA_SESIONES }' no encontrada."}

        # Encontrar la fila de la sesión
        # Asumiendo que 'ID_Sesion' es la primera columna (índice 1 para gspread)
        try:
            cell = ws.find(str(id_sesion), in_column=1) # gspread usa indexación base 1 para columnas/filas
        except gspread.exceptions.CellNotFound:
            return {"status": "error", "message": f"Sesión de caja con ID {id_sesion} no encontrada."}
        except Exception as e:
            return {"status": "error", "message": f"Error buscando sesión {id_sesion}: {e}"}


        if cell:
            row_index = cell.row
            # Leer saldo inicial de la fila encontrada
            # Asumiendo que SaldoInicial es la columna 4
            try:
                saldo_inicial_registrado = float(ws.cell(row_index, 4).value.replace(',', '.')) # Manejar comas decimales si es necesario
            except ValueError:
                 return {"status": "error", "message": f"Saldo inicial en sesión {id_sesion} no es un número válido."}


            now = datetime.now()
            fecha_cierre = now.strftime("%Y-%m-%d")
            hora_cierre = now.strftime("%H:%M:%S")
            estado = "CERRADA"
            if saldo_teorico_esperado is not None:
                diferencia = saldo_final_contado - saldo_teorico_esperado
            else:
                diferencia = saldo_final_contado - saldo_inicial_registrado # Cálculo simple
            # Calcular diferencia (esto es un ejemplo simple, podrías necesitar sumar ventas, etc.)
            # Por ahora, diferencia = saldo_final_contado - saldo_inicial_registrado
            # Una lógica más completa implicaría sumar todas las transacciones de esa sesión.


            updates = [
                {'range': f'F{row_index}', 'values': [[estado]]},
                {'range': f'G{row_index}', 'values': [[fecha_cierre]]},
                {'range': f'H{row_index}', 'values': [[hora_cierre]]},
                {'range': f'I{row_index}', 'values': [[saldo_final_contado]]},
                # Podrías añadir una columna para SaldoTeoricoFinal si lo calculas
                # a partir de todos los movimientos de la sesión.
                # {'range': f'J{row_index}', 'values': [[saldo_teorico_esperado]]},
                {'range': f'K{row_index}', 'values': [[diferencia]]},
                {'range': f'L{row_index}', 'values': [[usuario_cierre]]},
            ]
            ws.batch_update(updates)

            print(f"Caja (Sesión ID: {id_sesion}) cerrada por {usuario_cierre}. Saldo final: ${saldo_final_contado:.2f}, Diferencia: ${diferencia:.2f}")
            {   "status": "success",
                "id_sesion": id_sesion,
                "message": "Caja cerrada exitosamente.",
                "diferencia": diferencia
            }
        else:
            return {"status": "error", "message": f"No se encontró la sesión de caja con ID {id_sesion} para cerrar."}

    except Exception as e:
        print(f"Error en cerrar_caja: {e}")
        return {"status": "error", "message": str(e)}

def obtener_estado_caja_actual():
    """
    Verifica si hay alguna caja con estado "ABIERTA".
    Retorna la información de la sesión abierta o None si todas están cerradas.
    """
    try:
        g_handler = GoogleSheetsHandler()
        if not g_handler.client:
            print("No se pudo conectar a Google Sheets para obtener estado de caja.")
            return None

        registros = g_handler.get_all_records(SHEET_NAME_CAJA_SESIONES )
        if not registros:
            return None # No hay sesiones registradas

        # Buscar la última sesión abierta (podría haber errores si se abren varias)
        # Idealmente, se busca la que tiene estado "ABIERTA" y no tiene fecha de cierre
        for registro in reversed(registros): # Revisa desde la más reciente
            if registro.get('Estado') == 'ABIERTA':
                # Verificar si realmente está abierta (ej. no tiene fecha de cierre)
                if not registro.get('FechaCierre') and not registro.get('HoraCierre'):
                    print(f"Caja actualmente ABIERTA. Sesión ID: {registro.get('ID_Sesion')}")
                    return registro # Devuelve el diccionario del registro
        return None # Ninguna caja abierta encontrada
    except Exception as e:
        print(f"Error al obtener estado de caja: {e}")
        return None