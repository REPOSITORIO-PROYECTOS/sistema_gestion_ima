import os

from requests import Session
from back.modelos import Articulo, ConfiguracionEmpresa
from back.schemas.caja_schemas import ArticuloVendido
import gspread
from google.oauth2.service_account import Credentials
from sqlmodel import Session as DBSession
from typing import List, Dict, Any, Optional, Tuple
# Importar las VARIABLES PYTHON definidas en config.py
from back.config import (
    GOOGLE_SHEET_ID, GOOGLE_SERVICE_ACCOUNT_FILE,
    CONFIGURACION_GLOBAL_SHEET, USUARIOS_SHEET, TERCEROS_SHEET, ARTICULOS_SHEET,
    CAJA_SESIONES_SHEET, CAJA_MOVIMIENTOS_SHEET, STOCK_MOVIMIENTOS_SHEET,
    COMPRAS_CABECERA_SHEET, COMPRAS_DETALLE_SHEET,
    # Descomenta estas si las defines en config.py y .env para hojas de venta separadas
    # VENTAS_CABECERA_SHEET, VENTAS_DETALLE_SHEET, VENTAS_PAGOS_SHEET,
    # Descomenta estas si las defines y usas:
    # ADMIN_TOKEN_SHEET, # Aunque ahora podría ir en CONFIGURACION_GLOBAL_SHEET
    # STOCK_LISTAS_CONFIG_SHEET,
    # CONTABILIDAD_PLAN_SHEET, CONTABILIDAD_ASIENTOS_SHEET,
)
import uuid
from datetime import datetime

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file']
gspread_client: Optional[gspread.Client] = None

datos_clientes: List[Dict] = []

class TablasHandler:
    def __init__(self, id_empresa: int, db: DBSession):
        self.db = db  
        self.id_empresa = id_empresa
        self.google_sheet_id = self.obtener_google_sheet_id()
        self.client = self._init_client()


    
    def obtener_google_sheet_id(self) -> str:
        config = self.db.get(ConfiguracionEmpresa, self.id_empresa)
        if config and config.link_google_sheets:
            return config.link_google_sheets.strip()
        if GOOGLE_SHEET_ID:
            print(f"ADVERTENCIA: Usando GOOGLE_SHEET_ID global como fallback para empresa {self.id_empresa}")
            return GOOGLE_SHEET_ID.strip()
        raise ValueError(f"No se encontró link_google_sheets para la empresa ID {self.id_empresa} y no hay GOOGLE_SHEET_ID global configurado.")





    def _init_client(self) -> Optional[gspread.Client]:
        global gspread_client
        if gspread_client is None:
            try:
                back_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                credential_path = os.path.join(back_dir, GOOGLE_SERVICE_ACCOUNT_FILE)
                gspread_client = gspread.service_account(filename=credential_path, scopes=SCOPES)
            except Exception as e:
                print(f"Error al inicializar gspread: {e}")
                gspread_client = None
        return gspread_client

    

    def cargar_clientes(self):
        print("Intentando cargar/recargar datos de Clientes...")
        if self.client:
            try:
                sheet = self.client.open_by_key(self.google_sheet_id)
                worksheet = sheet.worksheet("clientes") 
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
    

    def cargar_proveedores(self):
        print("Intentando cargar/recargar datos de proveedores...")
        if self.client:
            try:
                sheet = self.client.open_by_key(self.google_sheet_id)
                worksheet = sheet.worksheet("proveedores") 
                datos_proveedores = worksheet.get_all_records()
                return datos_proveedores
            except gspread.exceptions.WorksheetNotFound:
                print("❌ ERROR: La hoja de cálculo no tiene una pestaña llamada 'proveedores'.")
            except Exception as e:
                # ¡IMPRIME EL ERROR REAL!
                print(f"❌ Error detallado al cargar datos de proveedores: {type(e).__name__} - {e}")
        else:
            print("Cliente de Google Sheets no disponible.")
        return [] # Devuelve lista vacía en caso de cualquier error
    



    def registrar_movimiento(self, datos_venta: Dict[str, Any]) -> bool:
        if not self.client:
            print("ERROR: Cliente de Google Sheets no disponible.")
            return False

        try:
            hoja = self.client.open_by_key(self.google_sheet_id).worksheet("MOVIMIENTOS")

            id_movimiento = str(uuid.uuid4())[:8]
            fecha_actual = datetime.now().strftime("%d-%m-%Y")
            fecha_hora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

            fila = [
                id_movimiento,
                datos_venta.get("id_cliente", ""),
                datos_venta.get("id_ingresos", ""),
                datos_venta.get("id_repartidor", ""),
                datos_venta.get("Repartidor", ""),
                fecha_hora,
                fecha_actual,
                datos_venta.get("cliente", ""),
                datos_venta.get("cuit", ""),
                datos_venta.get("razon_social", ""),
                datos_venta.get("Tipo_movimiento", ""),
                datos_venta.get("nro_comprobante", ""),
                datos_venta.get("descripcion", ""),
                f"${datos_venta.get('monto', 0):,.2f}".replace(",", "@").replace(".", ",").replace("@", "."),
                datos_venta.get("foto_comprobante", ""),
                datos_venta.get("observaciones", "")
            ]

            hoja.append_row(fila, value_input_option="USER_ENTERED")
            print(f"✅ Movimiento registrado correctamente en hoja 'MOVIMIENTOS' con ID: {id_movimiento}")
            return True

        except Exception as e:
            print(f"❌ Error al registrar movimiento en Google Sheets: {e}")
            return False
        


    def restar_stock(self, db: DBSession, lista_items: List[ArticuloVendido]) -> bool:
        if not self.client:
            print("❌ ERROR [STOCK]: Cliente de Google Sheets no disponible.")
            return False

        print("🔄 [STOCK] Iniciando proceso de actualización de stock en Google Sheets...")
        try:
            sheet = self.client.open_by_key(self.google_sheet_id)
            worksheet = sheet.worksheet("stock")
            datos_stock = worksheet.get_all_records()
            
            if not datos_stock:
                print("❌ ERROR [STOCK]: La hoja 'stock' está vacía.")
                return False
            
            # Obtener encabezados y detectar columnas flexiblemente
            encabezados = list(datos_stock[0].keys()) if datos_stock else []
            print(f"📋 [STOCK] Columnas detectadas en hoja: {encabezados}")
            
            # Buscar columna de código (ID del producto)
            columna_id = self._encontrar_columna(
                encabezados, 
                ['codigo_interno', 'codigo', 'código', 'code', 'Código']
            )
            
            # Buscar columna de stock
            columna_stock = self._encontrar_columna(
                encabezados,
                ['stock_actual', 'stock', 'cantidad', 'existencia', 'cantidad_disponible']
            )
            
            if not columna_id:
                print(f"❌ ERROR [STOCK]: No se encontró columna de código en la hoja. Columnas disponibles: {encabezados}")
                return False
                
            if not columna_stock:
                print(f"❌ ERROR [STOCK]: No se encontró columna de stock en la hoja. Columnas disponibles: {encabezados}")
                return False
            
            print(f"✅ [STOCK] Usando columnas: ID='{columna_id}', Stock='{columna_stock}'")

            for item_a_restar in lista_items:
                id_producto = db.get(Articulo, item_a_restar.id_articulo).codigo_interno
                cantidad_a_restar = item_a_restar.cantidad

                if not id_producto or cantidad_a_restar is None:
                    print(f"⚠️ ADVERTENCIA [STOCK]: Item inválido en la lista, saltando: {item_a_restar}")
                    continue

                print(f"  -> Procesando ID: {id_producto}, Cantidad a restar: {cantidad_a_restar}")
                encontrado = False
                for i, fila in enumerate(datos_stock):
                    if str(fila.get(columna_id)) == str(id_producto):
                        encontrado = True
                        numero_fila_gspread = i + 2  # +2 por encabezado y base 1
                        
                        # Limpiar valor de stock (puede tener formato de moneda o texto)
                        valor_stock = fila.get(columna_stock, 0)
                        try:
                            stock_actual = float(str(valor_stock).replace(',', '.').replace('$', '').strip())
                        except (ValueError, AttributeError):
                            stock_actual = 0.0

                        if stock_actual < cantidad_a_restar:
                            print(f"❌ ERROR [STOCK]: Stock insuficiente para ID {id_producto}. Stock actual: {stock_actual}, se necesita: {cantidad_a_restar}. Abortando.")
                            return False

                        nuevo_stock = stock_actual - cantidad_a_restar
                        encabezados_raw = worksheet.row_values(1)
                        letra_columna_stock = gspread.utils.rowcol_to_a1(1, encabezados_raw.index(columna_stock) + 1)[0]
                        celda_a_actualizar = f"{letra_columna_stock}{numero_fila_gspread}"

                        print(f"     Stock actual: {stock_actual}. Actualizando celda {celda_a_actualizar} a {nuevo_stock}")
                        worksheet.update_acell(celda_a_actualizar, nuevo_stock)

                        fila[columna_stock] = nuevo_stock
                        break

                if not encontrado:
                    print(f"❌ ERROR [STOCK]: Producto con ID {id_producto} no encontrado en hoja 'stock'. Abortando.")
                    return False

            print("✅ [STOCK] Stock actualizado correctamente en Google Sheets.")
            return True

        except gspread.WorksheetNotFound:
            print("❌ ERROR [STOCK]: Hoja 'stock' no encontrada en el documento.")
            return False
        except Exception as e:
            print(f"❌ ERROR [STOCK]: Error inesperado al actualizar stock: {e}")
            import traceback
            traceback.print_exc()
            return False
        

  
    def _normalizar_nombre_columna(self, nombre: str) -> str:
        """Normaliza nombres de columnas para comparación flexible."""
        return nombre.strip().lower().replace('ó', 'o').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ú', 'u').replace(' ', '_').replace('-', '_')
    
    def _encontrar_columna(self, encabezados: List[str], variantes: List[str]) -> Optional[str]:
        """Busca una columna por múltiples variantes de nombre (flexible)."""
        variantes_norm = [self._normalizar_nombre_columna(v) for v in variantes]
        for encabezado in encabezados:
            encab_norm = self._normalizar_nombre_columna(encabezado)
            if encab_norm in variantes_norm:
                return encabezado
        return None
    
    def _limpiar_precio(self, valor: Any) -> float:
        """Limpia y convierte un valor a precio (float)."""
        if valor is None or valor == '':
            return 0.0
        
        # Convertir a string si no lo es
        valor_str = str(valor).strip()
        
        if not valor_str or valor_str.lower() in ['nan', 'none', 'null']:
            return 0.0
        
        # Remover símbolos de moneda y espacios
        valor_str = valor_str.replace('$', '').replace('€', '').replace('ARS', '').strip()
        
        # Manejar separadores de miles y decimales
        # Formato: 20.000,00 (punto para miles, coma para decimales)
        if ',' in valor_str and '.' in valor_str:
            # Tiene ambos: asumir formato 20.000,00 (punto=miles, coma=decimal)
            valor_str = valor_str.replace('.', '').replace(',', '.')
        elif ',' in valor_str:
            # Solo coma: puede ser 20,00 (coma como decimal)
            if valor_str.count(',') == 1 and len(valor_str.split(',')[1]) <= 2:
                # Es un decimal, reemplazar coma por punto
                valor_str = valor_str.replace(',', '.')
            else:
                # Es un separador de miles
                valor_str = valor_str.replace(',', '')
        
        try:
            return float(valor_str)
        except ValueError:
            return 0.0
    
    def _mapear_fila(self, fila: Dict[str, Any], encabezados: List[str]) -> Dict[str, Any]:
        """
        Mapea automáticamente una fila a campos estándar.
        Detecta flexiblemente: código, descripción, precio_venta, precio_costo, stock, categoría, marca, ubicación.
        """
        mapeada = {}
        
        # Mapeo de código
        col_codigo = self._encontrar_columna(encabezados, ['codigo_interno', 'codigo', 'código', 'code'])
        if col_codigo:
            mapeada['codigo_interno'] = fila.get(col_codigo)
        
        # Mapeo de descripción
        col_desc = self._encontrar_columna(encabezados, ['descripcion', 'descripción', 'nombre', 'name', 'descripción_corta'])
        if col_desc:
            mapeada['descripcion'] = fila.get(col_desc)
        
        # Mapeo de precio de venta - intenta múltiples fuentes
        col_precio_venta = None
        # Primero intenta "Costo 1" (que tiene el valor real)
        col_precio_venta = self._encontrar_columna(encabezados, ['costo 1', 'costo_1', 'precio negocio', 'precio_negocio', 'precio_venta', 'precio', 'precio_cliente', 'pvp', 'valor_venta'])
        
        if col_precio_venta:
            mapeada['precio_venta'] = self._limpiar_precio(fila.get(col_precio_venta, 0))
        else:
            mapeada['precio_venta'] = 0.0
        
        # Mapeo de precio de costo
        col_precio_costo = self._encontrar_columna(encabezados, ['precio_costo', 'costo', 'precio_compra', 'costo_unitario', 'costo_1'])
        if col_precio_costo:
            mapeada['precio_costo'] = self._limpiar_precio(fila.get(col_precio_costo, 0))
        else:
            mapeada['precio_costo'] = 0.0
        
        # Mapeo de precio negocio (precio de cliente especial/mayorista)
        col_venta_negocio = self._encontrar_columna(encabezados, ['venta_negocio', 'precio_negocio', 'precio_mayorista', 'precio_cliente', 'precio_especial', 'precio_wholesale'])
        if col_venta_negocio:
            mapeada['venta_negocio'] = self._limpiar_precio(fila.get(col_venta_negocio, 0))
        else:
            mapeada['venta_negocio'] = 0.0
        
        # Mapeo de stock
        col_stock = self._encontrar_columna(encabezados, ['stock_actual', 'stock', 'cantidad', 'stock_disponible', 'existencia'])
        if col_stock:
            try:
                mapeada['stock_actual'] = float(fila.get(col_stock, 0) or 0)
            except:
                mapeada['stock_actual'] = 0.0
        
        # Mapeo de IVA
        col_iva = self._encontrar_columna(encabezados, ['tasa_iva', 'iva', 'alicuota_iva', 'impuesto'])
        if col_iva:
            try:
                mapeada['tasa_iva'] = float(fila.get(col_iva, 0.21) or 0.21)
            except:
                mapeada['tasa_iva'] = 0.21
        
        # Mapeo de categoría
        col_categoria = self._encontrar_columna(encabezados, ['categoria', 'categoría', 'category', 'tipo'])
        if col_categoria:
            mapeada['categoria'] = fila.get(col_categoria)
        
        # Mapeo de marca
        col_marca = self._encontrar_columna(encabezados, ['marca', 'brand', 'fabricante'])
        if col_marca:
            mapeada['marca'] = fila.get(col_marca)
        
        # Mapeo de ubicación
        col_ubicacion = self._encontrar_columna(encabezados, ['ubicacion', 'ubicación', 'location', 'estante', 'pasillo'])
        if col_ubicacion:
            ubicacion_valor = fila.get(col_ubicacion)
            mapeada['ubicacion'] = ubicacion_valor if ubicacion_valor else "Sin definir"
        else:
            mapeada['ubicacion'] = "Sin definir"
        
        # Mapeo de unidad
        col_unidad = self._encontrar_columna(encabezados, ['unidad', 'unidad_venta', 'unit'])
        if col_unidad:
            mapeada['unidad_venta'] = fila.get(col_unidad, 'Unidad') or 'Unidad'
        else:
            mapeada['unidad_venta'] = 'Unidad'
        
        # Copiar campos adicionales del original
        mapeada['_fila_original'] = fila
        
        return mapeada

    def cargar_articulos(self, nombre_hoja: Optional[str] = None):
        """
        Carga artículos desde Google Sheets.
        Intenta múltiples nombres de hoja si no se especifica uno.
        """
        print("📦 Cargando artículos desde Google Sheets...")
        
        if not self.client:
            print("❌ ERROR: Cliente de Google Sheets no disponible.")
            return []
        
        hojas_posibles = nombre_hoja and [nombre_hoja] or ['stock', 'articulos', 'productos', 'inventory', 'inventario', 'items']
        
        try:
            sheet = self.client.open_by_key(self.google_sheet_id)
            
            for nombre_hoja_intento in hojas_posibles:
                try:
                    print(f"  Intentando cargar hoja: '{nombre_hoja_intento}'...")
                    worksheet = sheet.worksheet(nombre_hoja_intento)
                    datos_crudos = worksheet.get_all_records()
                    
                    if not datos_crudos:
                        print(f"  ⚠️ Hoja '{nombre_hoja_intento}' vacía, intentando siguiente...")
                        continue
                    
                    # Obtener encabezados para mapeo flexible
                    encabezados = list(datos_crudos[0].keys()) if datos_crudos else []
                    print(f"  ✅ Hoja '{nombre_hoja_intento}' cargada. Columnas: {encabezados}")
                    
                    # Mapear registros a formato estándar
                    datos_mapeados = []
                    for fila in datos_crudos:
                        fila_mapeada = self._mapear_fila(fila, encabezados)
                        datos_mapeados.append(fila_mapeada)
                    
                    print(f"  ✅ {len(datos_mapeados)} registros mapeados exitosamente.")
                    return datos_mapeados
                    
                except gspread.exceptions.WorksheetNotFound:
                    print(f"  ⚠️ Hoja '{nombre_hoja_intento}' no encontrada, intentando siguiente...")
                    continue
                except Exception as e:
                    print(f"  ⚠️ Error con hoja '{nombre_hoja_intento}': {e}")
                    continue
            
            print(f"❌ ERROR: No se encontró ninguna hoja de artículos en {hojas_posibles}")
            return []
            
        except Exception as e:
            print(f"❌ ERROR al cargar datos de Artículos: {e}")
            return []
