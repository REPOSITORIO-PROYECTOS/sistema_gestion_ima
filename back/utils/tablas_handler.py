import os
import re
from datetime import datetime, timedelta

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
    _worksheet_title_cache: Dict[str, str] = {}
    _headers_cache: Dict[str, Tuple[datetime, List[str]]] = {}

    def __init__(self, id_empresa: int, db: DBSession):
        self.db = db  
        self.id_empresa = id_empresa
        self.google_sheet_id = self.obtener_google_sheet_id()
        self.client = self._init_client()
        self.ultimo_error_sync: Optional[str] = None


    
    def obtener_google_sheet_id(self) -> str:
        config = self.db.get(ConfiguracionEmpresa, self.id_empresa)
        if config and config.link_google_sheets:
            return self._normalizar_google_sheet_key(config.link_google_sheets)
        if GOOGLE_SHEET_ID:
            print(f"ADVERTENCIA: Usando GOOGLE_SHEET_ID global como fallback para empresa {self.id_empresa}")
            return self._normalizar_google_sheet_key(GOOGLE_SHEET_ID)
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

    def _normalizar_google_sheet_key(self, valor_crudo: Any) -> str:
        """
        Admite tanto key pura como URL de Google Sheets y devuelve SIEMPRE la key.
        """
        valor = str(valor_crudo or "").strip()
        if not valor:
            raise ValueError("El identificador de Google Sheets está vacío.")

        if "docs.google.com/spreadsheets" not in valor:
            return valor

        match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", valor)
        if match and match.group(1):
            return match.group(1)

        raise ValueError(
            "No se pudo extraer el ID de la URL de Google Sheets. "
            "Use la key (ID) o una URL válida."
        )

    def _abrir_planilla(self):
        if not self.client:
            raise RuntimeError("Cliente de Google Sheets no disponible.")
        try:
            return self.client.open_by_key(self.google_sheet_id)
        except Exception as e:
            raise RuntimeError(
                f"No se pudo abrir la planilla (empresa={self.id_empresa}, sheet_id={self.google_sheet_id}): "
                f"{type(e).__name__} - {e}"
            ) from e

    def _obtener_worksheet_flexible(self, sheet, nombres_posibles: List[str]):
        """
        Busca una pestaña por variantes de nombre, ignorando mayúsculas/minúsculas.
        """
        if not nombres_posibles:
            raise ValueError("Debe indicarse al menos un nombre de hoja posible.")

        cache_key = f"{self.google_sheet_id}:{'|'.join(sorted([self._normalizar_nombre_columna(n) for n in nombres_posibles]))}"
        titulo_cacheado = self._worksheet_title_cache.get(cache_key)
        if titulo_cacheado:
            try:
                return sheet.worksheet(titulo_cacheado)
            except Exception:
                # Si el título cacheado ya no existe, refrescar resolución.
                self._worksheet_title_cache.pop(cache_key, None)

        try:
            worksheets = sheet.worksheets()
            por_titulo_norm = {
                self._normalizar_nombre_columna(ws.title): ws for ws in worksheets
            }
        except Exception as e:
            raise RuntimeError(f"No se pudo listar hojas de la planilla: {type(e).__name__} - {e}") from e

        for nombre in nombres_posibles:
            ws = por_titulo_norm.get(self._normalizar_nombre_columna(nombre))
            if ws:
                self._worksheet_title_cache[cache_key] = ws.title
                return ws

        disponibles = [ws.title for ws in worksheets]
        raise gspread.exceptions.WorksheetNotFound(
            f"No se encontró hoja con variantes {nombres_posibles}. Hojas disponibles: {disponibles}"
        )

    def _obtener_encabezados_cacheados(self, hoja) -> List[str]:
        """
        Cachea encabezados para reducir lecturas y evitar 429 por exceso.
        """
        cache_key = f"{self.google_sheet_id}:{hoja.title}"
        now = datetime.utcnow()
        cache_entry = self._headers_cache.get(cache_key)

        # TTL corto para acompañar cambios manuales de encabezados.
        if cache_entry and (now - cache_entry[0]) < timedelta(minutes=5):
            return cache_entry[1]

        encabezados = hoja.row_values(1)
        self._headers_cache[cache_key] = (now, encabezados)
        return encabezados

    

    def cargar_clientes(self):
        print("Intentando cargar/recargar datos de Clientes...")
        if self.client:
            try:
                sheet = self._abrir_planilla()
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
                sheet = self._abrir_planilla()
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
            self.ultimo_error_sync = "Cliente de Google Sheets no disponible."
            return False

        try:
            sheet = self._abrir_planilla()
            hoja = self._obtener_worksheet_flexible(
                sheet,
                ["MOVIMIENTOS", "Movimientos", "movimientos", "movimiento", "Movimiento"],
            )

            id_movimiento = str(uuid.uuid4())[:8]
            fecha_actual = datetime.now().strftime("%d-%m-%Y")
            fecha_hora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

            monto_formateado = f"${datos_venta.get('monto', 0):,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")

            # Mapeo por clave normalizada: soporta encabezados técnicos y
            # encabezados descriptivos usados en planillas existentes.
            fila_por_campo_norm = {
                "id_movimiento": id_movimiento,
                "id_cliente": datos_venta.get("id_cliente", ""),
                "id_ingresos": datos_venta.get("id_ingresos", ""),
                "id_repartidor": datos_venta.get("id_repartidor", ""),
                "repartidor": datos_venta.get("Repartidor", ""),
                "fecha_hora": fecha_hora,
                "fecha_y_hora_entrega": fecha_hora,
                "fecha_actual": fecha_actual,
                "fecha": fecha_actual,
                "cliente": datos_venta.get("cliente", ""),
                "cuit": datos_venta.get("cuit", ""),
                "razon_social": datos_venta.get("razon_social", ""),
                "tipo_movimiento": datos_venta.get("Tipo_movimiento", ""),
                "tipo_de_movimiento": datos_venta.get("Tipo_movimiento", ""),
                "nro_comprobante": datos_venta.get("nro_comprobante", ""),
                "descripcion": datos_venta.get("descripcion", ""),
                "monto": monto_formateado,
                "foto_comprobante": datos_venta.get("foto_comprobante", ""),
                "observaciones": datos_venta.get("observaciones", ""),
            }

            # Alinea por encabezado real para evitar corrimientos de columnas.
            # Se cachea para reducir lecturas (mitiga errores 429 de cuota).
            encabezados = self._obtener_encabezados_cacheados(hoja)

            # Si no hay encabezado utilizable, usamos el layout estándar A:P.
            if not encabezados:
                encabezados = [
                    "id_movimiento", "id_cliente", "id_ingresos", "id_repartidor", "Repartidor",
                    "fecha_hora", "fecha_actual", "cliente", "cuit", "razon_social",
                    "Tipo_movimiento", "nro_comprobante", "descripcion", "monto",
                    "foto_comprobante", "observaciones"
                ]

            fila = [
                fila_por_campo_norm.get(self._normalizar_nombre_columna(col), "")
                for col in encabezados
            ]

            # Escribe con append para evitar lectura de toda la hoja en cada venta.
            hoja.append_row(fila, value_input_option="USER_ENTERED")
            print(f"✅ Movimiento registrado correctamente en hoja 'MOVIMIENTOS' con ID: {id_movimiento}")
            self.ultimo_error_sync = None
            return True

        except Exception as e:
            print(f"❌ Error al registrar movimiento en Google Sheets: {e}")
            self.ultimo_error_sync = f"{type(e).__name__}: {e}"
            return False
        


    def restar_stock(self, db: DBSession, lista_items: List[ArticuloVendido]) -> bool:
        if not self.client:
            print("❌ ERROR [STOCK]: Cliente de Google Sheets no disponible.")
            self.ultimo_error_sync = "Cliente de Google Sheets no disponible para stock."
            return False

        print("🔄 [STOCK] Iniciando proceso de actualización de stock en Google Sheets...")
        try:
            sheet = self._abrir_planilla()
            worksheet = sheet.worksheet("stock")
            datos_stock = worksheet.get_all_records()
            
            if not datos_stock:
                print("❌ ERROR [STOCK]: La hoja 'stock' está vacía.")
                self.ultimo_error_sync = "La hoja 'stock' está vacía."
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
                self.ultimo_error_sync = "No se encontró columna de código en hoja stock."
                return False
                
            if not columna_stock:
                print(f"❌ ERROR [STOCK]: No se encontró columna de stock en la hoja. Columnas disponibles: {encabezados}")
                self.ultimo_error_sync = "No se encontró columna de stock en hoja stock."
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
                            self.ultimo_error_sync = f"Stock insuficiente para ID {id_producto}."
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
                    self.ultimo_error_sync = f"Producto {id_producto} no encontrado en hoja stock."
                    return False

            print("✅ [STOCK] Stock actualizado correctamente en Google Sheets.")
            self.ultimo_error_sync = None
            return True

        except gspread.WorksheetNotFound:
            print("❌ ERROR [STOCK]: Hoja 'stock' no encontrada en el documento.")
            self.ultimo_error_sync = "Hoja 'stock' no encontrada."
            return False
        except Exception as e:
            print(f"❌ ERROR [STOCK]: Error inesperado al actualizar stock: {e}")
            import traceback
            traceback.print_exc()
            self.ultimo_error_sync = f"{type(e).__name__}: {e}"
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
        """Convierte valores como '$ 2.900,00' o '1200.00' a float."""
        if valor is None:
            return 0.0

        valor_str = str(valor).replace('$', '').strip()
        if not valor_str:
            return 0.0

        try:
            if '.' in valor_str and ',' in valor_str:
                valor_str = valor_str.replace('.', '').replace(',', '.')
            elif ',' in valor_str:
                valor_str = valor_str.replace(',', '.')
            return float(valor_str)
        except ValueError:
            return 0.0

    def _limpiar_numero(self, valor: Any) -> float:
        """Convierte números con formato local/internacional a float sin perder decimales."""
        if valor is None:
            return 0.0

        valor_str = str(valor).strip().replace('$', '')
        if not valor_str:
            return 0.0

        # Mantener solo caracteres numéricos relevantes
        valor_str = ''.join(ch for ch in valor_str if ch.isdigit() or ch in [',', '.', '-'])
        if not valor_str:
            return 0.0

        try:
            if '.' in valor_str and ',' in valor_str:
                # Formato 1.234,56
                valor_str = valor_str.replace('.', '').replace(',', '.')
            elif ',' in valor_str:
                # Formato 1234,56
                valor_str = valor_str.replace(',', '.')
            # Si solo hay '.', se asume decimal estándar y no se toca
            return float(valor_str)
        except ValueError:
            return 0.0
    
    def _mapear_fila(self, fila: Dict[str, Any], encabezados: List[str]) -> Dict[str, Any]:
        """
        Mapea automáticamente una fila a campos estándar.
        Detecta flexiblemente: código, descripción, precio_venta, precio_costo, stock, categoría, marca, ubicación.
        """
        mapeada = {}
        
        col_codigo = self._encontrar_columna(encabezados, ['Código', 'codigo', 'codigo_interno'])
        col_id = self._encontrar_columna(encabezados, ['id producto', 'id_producto'])

        codigo_valor = str(fila.get(col_codigo, '')).strip() if col_codigo else ''
        if not codigo_valor:
            codigo_valor = str(fila.get(col_id, '')).strip() if col_id else ''
        if not codigo_valor:
            return {}

        mapeada['codigo_interno'] = codigo_valor
        mapeada['Código'] = codigo_valor

        col_nombre = self._encontrar_columna(encabezados, ['nombre'])
        col_desc = self._encontrar_columna(encabezados, ['Descripción', 'descripcion'])
        valor_nombre = str(fila.get(col_nombre, '')).strip() if col_nombre else ''
        valor_desc = str(fila.get(col_desc, '')).strip() if col_desc else ''
        mapeada['descripcion'] = valor_nombre or valor_desc or 'Sin Descripción'

        col_precio = self._encontrar_columna(encabezados, ['precio', 'precio venta'])
        mapeada['precio_venta'] = self._limpiar_precio(fila.get(col_precio)) if col_precio else 0.0

        col_negocio = self._encontrar_columna(encabezados, ['precio negocio'])
        mapeada['venta_negocio'] = self._limpiar_precio(fila.get(col_negocio)) if col_negocio else 0.0

        col_costo = self._encontrar_columna(encabezados, ['Costo 1', 'costo'])
        mapeada['precio_costo'] = self._limpiar_precio(fila.get(col_costo)) if col_costo else 0.0

        col_stock = self._encontrar_columna(encabezados, ['cantidad', 'stock'])
        if col_stock:
            try:
                mapeada['stock_actual'] = self._limpiar_numero(fila.get(col_stock, 0))
            except Exception:
                mapeada['stock_actual'] = 0.0
        else:
            mapeada['stock_actual'] = 0.0

        col_activo = self._encontrar_columna(encabezados, ['Activo'])
        activo_val = str(fila.get(col_activo, 'TRUE')).strip().upper() if col_activo else 'TRUE'
        mapeada['Activo'] = activo_val

        col_barras = self._encontrar_columna(encabezados, ['Codigo de barras', 'Barras'])
        mapeada['Codigo de barras'] = str(fila.get(col_barras, '')).strip() if col_barras else ''

        col_ubicacion = self._encontrar_columna(encabezados, ['ubicacion'])
        mapeada['ubicacion'] = str(fila.get(col_ubicacion, '')).strip() if col_ubicacion else 'Sin definir'

        col_unidad = self._encontrar_columna(encabezados, ['unidad'])
        mapeada['unidad_venta'] = str(fila.get(col_unidad, 'Unidad')).strip() if col_unidad else 'Unidad'

        col_categoria = self._encontrar_columna(encabezados, ['Categoria', 'categoria'])
        mapeada['categoria'] = str(fila.get(col_categoria, '')).strip() if col_categoria else ''

        col_marca = self._encontrar_columna(encabezados, ['Marca', 'marca'])
        mapeada['marca'] = str(fila.get(col_marca, '')).strip() if col_marca else ''

        mapeada['_fila_original'] = fila

        return mapeada if mapeada.get('codigo_interno') else {}

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
            sheet = self._abrir_planilla()
            
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
