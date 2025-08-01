import os
from back.schemas.caja_schemas import ArticuloVendido
import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Any, Optional, Tuple
import uuid
from datetime import datetime
# Importar las VARIABLES PYTHON definidas en config.py
from back.config import (
    GOOGLE_SHEET_ID, GOOGLE_SERVICE_ACCOUNT_FILE,
)
from back.modelos import link_google_sheets

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file']
gspread_client: Optional[gspread.Client] = None

datos_clientes: List[Dict] = []

class TablasHandler:
    def __init__(self):
        self.client = self._init_client()

    def _init_client(self) -> Optional[gspread.Client]:
        global gspread_client
        if gspread_client is None:
            print("Inicializando cliente gspread...")
            try:
                back_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                
                # 2. Construir la ruta absoluta al archivo de credenciales
                credential_path = os.path.join(back_dir, GOOGLE_SERVICE_ACCOUNT_FILE)
                
                print(f"Buscando credenciales en la ruta absoluta: {credential_path}")

                # 3. Usar la ruta absoluta para inicializar el cliente
                gspread_client = gspread.service_account(filename=credential_path, scopes=SCOPES)
                print("Cliente gspread inicializado.")
            except FileNotFoundError:
                print(f"ERROR FATAL: Archivo de credenciales no encontrado en '{GOOGLE_SERVICE_ACCOUNT_FILE}'")
                gspread_client = None
            except Exception as e:
                print(f"ERROR FATAL: No se pudo inicializar el cliente gspread: {e}")
                gspread_client = None
        return gspread_client
    

    def cargar_clientes(self):
        print("Intentando cargar/recargar datos de Clientes...")
        if self.client:
            try:
                sheet = self.client.open_by_key(link_google_sheets)
                worksheet = sheet.worksheet("clientes") # <-- ¿Existe una hoja llamada "clientes"?
                datos_clientes = worksheet.get_all_records()
                return datos_clientes
            except gspread.exceptions.WorksheetNotFound:
                print("❌ ERROR: La hoja de cálculo no tiene una pestaña llamada 'clientes'.")
            except Exception as e:
                # ¡IMPRIME EL ERROR REAL!
                print(f"❌ Error detallado al cargar datos de Clientes: {type(e).__name__} - {e}")
        else:
            print("Cliente de Google Sheets no disponible.")
        return [] # Devuelve lista vacía en caso de cualquier error
    


    def registrar_movimiento(self, google_sheet_id: str, datos_venta: Dict[str, Any]) -> bool:
        
        if not self.client:
            print("ERROR: Cliente de Google Sheets no disponible.")
            return False
        if not google_sheet_id:
            print("ADVERTENCIA: No se proporcionó un ID de Google Sheet. Saltando.")
            return False

        try:
            # Ahora usa el ID que le pasaron como parámetro, no una variable global
            hoja = self.client.open_by_key(google_sheet_id).worksheet("MOVIMIENTOS")


            id_movimiento = str(uuid.uuid4())[:8]
            fecha_actual = datetime.now().strftime("%d-%m-%Y")
            fecha_hora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

            fila = [
                id_movimiento,
                datos_venta.get("id_cliente", ""),
                datos_venta.get("id_ingresos", ""),
                datos_venta.get("id_repartidor", ""),
                datos_venta.get("repartidor", ""),
                fecha_hora,
                fecha_actual,
                datos_venta.get("cliente", ""),
                datos_venta.get("cuit", ""),
                datos_venta.get("razon_social", ""),
                datos_venta.get("Tipo_movimiento", ""),  # Tipo de Movimiento
                datos_venta.get("nro_comprobante", ""),
                datos_venta.get("descripcion", ""),
                f"${datos_venta.get('monto', 0):,.2f}".replace(",", "@").replace(".", ",").replace("@", "."),
                datos_venta.get("foto_comprobante", ""),
                datos_venta.get("observaciones", "")
            ]

            hoja.append_row(fila, value_input_option="USER_ENTERED")
            print(f"Venta registrada correctamente en caja con ID: {id_movimiento}")
            return True

        except Exception as e:
            print(f"Error al registrar venta: {e}")
            return False
        


    def restar_stock(self, google_sheet_id: str, lista_items: List[Dict[str, Any]]) -> bool:
        if not self.client or not google_sheet_id:
            return False
        
        try:
            sheet = self.client.open_by_key(google_sheet_id)
            worksheet = sheet.worksheet("stock") 
            datos_stock = worksheet.get_all_records()

            columna_id = "id producto"
            columna_stock = "cantidad"

            if not datos_stock or columna_id not in datos_stock[0] or columna_stock not in datos_stock[0]:
                print(f"❌ ERROR [STOCK]: La hoja 'stock' está vacía o no tiene las columnas '{columna_id}' y '{columna_stock}'.")
                return False



            for item_a_restar in lista_items:
                id_producto = item_a_restar.id_articulo
                cantidad_a_restar = item_a_restar.cantidad

                if not id_producto or cantidad_a_restar is None:
                    print(f"⚠️ ADVERTENCIA [STOCK]: Item inválido en la lista, saltando: {item_a_restar}")
                    continue

                print(f"  -> Procesando ID: {id_producto}, Cantidad a restar: {cantidad_a_restar}")
                
                encontrado = False
                for i, fila in enumerate(datos_stock):
                    if str(fila.get(columna_id)) == str(id_producto):
                        encontrado = True
                        numero_fila_gspread = i + 2
                        stock_actual = float(fila.get(columna_stock, 0))

                        if stock_actual < cantidad_a_restar:
                            print(f"❌ ERROR [STOCK]: Stock insuficiente para ID {id_producto}. Stock actual: {stock_actual}, se necesita: {cantidad_a_restar}. Abortando operación completa.")
                    
                            return False
 
                        nuevo_stock = stock_actual - cantidad_a_restar

                        encabezados = worksheet.row_values(1)
                        letra_columna_stock = gspread.utils.rowcol_to_a1(1, encabezados.index(columna_stock) + 1)[0]
                        
                        celda_a_actualizar = f"{letra_columna_stock}{numero_fila_gspread}"
                        print(f"     Stock actual: {stock_actual}. Actualizando celda {celda_a_actualizar} a {nuevo_stock}")
                        worksheet.update_acell(celda_a_actualizar, nuevo_stock)

                        fila[columna_stock] = nuevo_stock
                        
                        break # Salimos del bucle de filas, ya encontramos el producto
                
                if not encontrado:
                    print(f"❌ ERROR [STOCK]: Producto con ID {id_producto} no encontrado en la hoja 'stock'. Abortando operación completa.")
                    return False

            print("✅ [STOCK] Proceso de actualización de stock en Google Sheets completado exitosamente.")
            return True

        except gspread.exceptions.WorksheetNotFound:
            print("❌ ERROR [STOCK]: Hoja 'stock' no encontrada en el documento.")
            return False
        except Exception as e:
            print(f"❌ ERROR [STOCK]: Ocurrió un error inesperado al actualizar el stock: {e}")
            return False
        

  
    def cargar_articulos(self):
        print("Intentando cargar/recargar datos de Artículos...")
        if self.client:
            try:
                sheet = self.client.open_by_key(link_google_sheets)
                worksheet = sheet.worksheet("stock") # Apunta a la hoja "stock"
                return worksheet.get_all_records()
            except gspread.exceptions.WorksheetNotFound:
                print("ERROR: Hoja 'stock' no encontrada.")
            except Exception as e:
                print(f"Error al cargar datos de Artículos: {e}")
        return []