# C:\Users\ticia\SISTEMAS\sistema_gestion_ima\back\utils\sheets_google_handler.py
import gspread
from google.oauth2.service_account import Credentials
import datetime
import uuid
# Importar los NUEVOS nombres de hojas desde config
from config import (
    GOOGLE_SHEET_ID, GOOGLE_SERVICE_ACCOUNT_FILE,
    SHEET_NAME_TERCEROS,
    SHEET_NAME_DOC_VENTA_CABECERA, SHEET_NAME_DOC_VENTA_DETALLE, SHEET_NAME_DOC_VENTA_PAGOS,
    SHEET_NAME_DOC_COMPRA_DETALLE, SHEET_NAME_DOC_COMPRA_DETALLE,
    SHEET_NAME_ARTICULOS, SHEET_NAME_STOCK_CONFIG_LISTAS,
    SHEET_NAME_CAJA_SESIONES, SHEET_NAME_CAJA_MOVIMIENTOS, SHEET_NAME_STOCK_MOVIMIENTOS,
    SHEET_NAME_CONTABILIDAD_PLAN_CONFIG, SHEET_NAME_CONTABILIDAD_ASIENTOS,
    SHEET_NAME_ADMIN_TOKEN, SHEET_NAME_USUARIOS, SHEET_NAME_CONFIG_HORARIOS_CAJA
)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file']

class GoogleSheetsHandler:
    def __init__(self, sheet_id=None):
        self.creds = Credentials.from_service_account_file(GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        self.client = gspread.authorize(self.creds)
        self.sheet_id = sheet_id or GOOGLE_SHEET_ID
        if not self.sheet_id:
            raise ValueError("GOOGLE_SHEET_ID no está configurado.")
        try:
            self.spreadsheet = self.client.open_by_key(self.sheet_id) # CORREGIDO
        except gspread.exceptions.SpreadsheetNotFound:
            print(f"Error: Spreadsheet con ID '{self.sheet_id}' no encontrado.")
            self.spreadsheet = None; self.client = None
        except Exception as e:
            print(f"Error conectando a Google Sheets: {e}");
            self.spreadsheet = None; self.client = None

    def get_worksheet(self, sheet_name_value): # sheet_name_value es el string del nombre de la hoja
        if not self.spreadsheet: return None
        try:
            return self.spreadsheet.worksheet(sheet_name_value)
        except gspread.exceptions.WorksheetNotFound:
            print(f"Advertencia: Hoja '{sheet_name_value}' no encontrada. Creándola...")
            headers = self.get_default_headers(sheet_name_value) # Usar el string
            if not headers:
                print(f"Error Crítico: No se pudieron obtener cabeceras para la nueva hoja '{sheet_name_value}'. No se creará.")
                return None
            worksheet = self.spreadsheet.add_worksheet(title=sheet_name_value, rows="1", cols=len(headers) + 2)
            worksheet.update('A1', [headers], value_input_option='USER_ENTERED')
            worksheet.freeze(rows=1)
            print(f"Hoja '{sheet_name_value}' creada con cabeceras.")
            return worksheet
        except Exception as e:
            print(f"Error obteniendo/creando la hoja '{sheet_name_value}': {e}")
            return None

    def get_default_headers(self, sheet_name_value): # sheet_name_value es el string del nombre de la hoja
        # Comparar con los VALORES de las constantes importadas
        if sheet_name_value == SHEET_NAME_TERCEROS:
            return [
                "ID_Tercero", "TipoTercero", "NombreApellido_RazonSocial", "IdentificacionFiscal",
                "TipoIdentificacion", "DireccionCompleta", "Ciudad", "Provincia_Estado", "Pais",
                "CodigoPostal", "TelefonoPrincipal", "TelefonoAlternativo", "EmailPrincipal",
                "EmailFacturacion", "ContactoPrincipalNombre", "CondicionIVA", "Estado",
                "FechaAlta", "NotasAdicionales", "SaldoCuentaCorriente", "LimiteCredito", "DiasPlazoPagoHabitual"
            ]
        elif sheet_name_value == SHEET_NAME_DOC_VENTA_CABECERA:
            return [
                "ID_DocVenta", "TipoDocumentoVenta", "ID_VentaOriginal_NC_ND", "ID_Cliente", "NombreCliente",
                "ID_SesionCaja", "FechaEmision", "HoraEmision", "PuntoVenta", "NumeroComprobante",
                "CAE_Autorizacion", "FechaVencimientoCAE", "Moneda", "SubtotalNeto", "MontoDescuentoGlobal",
                "PorcentajeDescuentoGlobal", "BaseImponibleIVA", "MontoIVA_General", "MontoIVA_Reducido",
                "OtrosImpuestos", "TotalDocumento", "EstadoDocumento", "UsuarioVendedor", "Notas"
            ]
        elif sheet_name_value == SHEET_NAME_DOC_VENTA_DETALLE:
            return [
                "ID_DetalleVenta", "ID_DocVenta", "ID_Articulo", "CodigoArticulo", "DescripcionArticulo",
                "Cantidad", "PrecioUnitarioNeto", "PorcentajeDescuentoItem", "MontoDescuentoItem",
                "AlicuotaIVAItem", "MontoIVAItem", "SubtotalItemConImpuestos", "CostoArticuloVendido"
            ]
        elif sheet_name_value == SHEET_NAME_DOC_VENTA_PAGOS:
            return [
                "ID_Pago", "ID_DocVenta", "FechaPago", "MetodoPago", "ImportePagado",
                "ReferenciaPago", "Banco", "NumeroCuotas", "InteresCuotas"
            ]
        elif sheet_name_value == SHEET_NAME_DOC_COMPRA_DETALLE:
            return [
                "ID_DocCompra", "TipoDocumentoCompra", "ID_CompraOriginal_NC_ND", "ID_OrdenCompra_Asociada",
                "ID_Proveedor", "NombreProveedor", "FechaEmision", "FechaRecepcionEstimada_Real",
                "NumeroRemitoProveedor", "NumeroFacturaProveedor", "Moneda", "SubtotalNeto", "MontoIVA",
                "OtrosImpuestosCompra", "TotalDocumento", "EstadoDocumento", "UsuarioCreador_Receptor",
                "CondicionesPago", "Notas"
            ]
        elif sheet_name_value == SHEET_NAME_DOC_COMPRA_DETALLE:
            return [
                "ID_DetalleCompra", "ID_DocCompra", "ID_Articulo", "CodigoArticuloProveedor", "DescripcionArticulo",
                "CantidadPedida_Recibida", "UnidadMedidaCompra", "CostoUnitarioNeto", "AlicuotaIVAItemCompra",
                "MontoIVAItemCompra", "SubtotalItemConImpuestosCompra", "Lote", "FechaVencimientoLote"
            ]
        elif sheet_name_value == SHEET_NAME_ARTICULOS:
            return [
                "ID_Articulo", "CodigoInterno", "SKU_CodigoBarras", "DescripcionPrincipal", "DescripcionAmpliada",
                "ID_Categoria_StockConfig", "NombreCategoria", "ID_Marca_StockConfig", "NombreMarca",
                "ID_UnidadMedidaCompra_StockConfig", "ID_UnidadMedidaVenta_StockConfig", "FactorConversionCompraVenta",
                "StockActual", "StockMinimoAdvertencia", "StockMaximoSugerido", "CostoUltimaCompra",
                "CostoPromedioPonderado", "PrecioVentaMinorista_Base", "AlicuotaIVA_Venta",
                "PrecioVentaMinorista_Final", "ID_ProveedorPreferido_Terceros", "Perecedero", "DiasVidaUtil",
                "ManejaLote", "ManejaNumeroSerie", "EstadoArticulo", "FechaCreacion", "FechaUltimaModificacion",
                "ID_UbicacionDefault_StockConfig", "Notas", "ImagenURL"
            ]
        elif sheet_name_value == SHEET_NAME_STOCK_CONFIG_LISTAS:
            return [
                "ID_Lista", "TipoLista", "Nombre", "Codigo", "DescripcionAdicional", "Activo"
            ]
        elif sheet_name_value == SHEET_NAME_CAJA_SESIONES: # Antes SHEET_NAME_CAJA_APERTURAS
            return [
                "ID_Sesion", "FechaApertura", "HoraApertura", "UsuarioApertura", "SaldoInicial",
                "FechaCierre", "HoraCierre", "UsuarioCierre", "SaldoFinalContado",
                "SaldoFinalTeorico", "Diferencia", "Estado", "Notas"
            ]
        elif sheet_name_value == SHEET_NAME_CAJA_MOVIMIENTOS: # Antes SHEET_NAME_CAJA_MOVIMIENTOS
            return [
                "ID_MovimientoCaja",        # Corresponde a ID_Registro
                "ID_SesionCaja",            # Corresponde a ID_Sesion
                "Timestamp",                # Puede usarse para Fecha y Hora
                "TipoRegistro",             # Corresponde a Tipo_Movimiento (VENTA, INGRESO, EGRESO)
                "Concepto_Descripcion",     # Se mantiene
                "ID_Articulo_Venta",        # Corresponde a ID_Articulo (solo para ventas)
                "NombreArticulo_Venta",     # Corresponde a Nombre_Articulo (solo para ventas)
                "Cantidad_Venta",           # Corresponde a Cantidad (solo para ventas)
                "PrecioUnitario_Venta",     # Corresponde a PrecioUnitario (solo para ventas)
                "Subtotal_Venta",           # Corresponde a Subtotal (solo para ventas)
                "MontoMovimiento",          # Corresponde a MontoTotalMovimiento (para Ingreso/Egreso) o Total Venta
                "MetodoPago",               # Corresponde a Metodo_Pago
                "ID_Cliente_Venta",         # Corresponde a ID_Cliente (solo para ventas)
                "UsuarioResponsable",       # Corresponde a Usuario
                "ID_ReferenciaExterna",     # Ej. ID_DocVenta si una venta es un solo movimiento aquí
                "Notas"
            ]
        elif sheet_name_value == SHEET_NAME_STOCK_MOVIMIENTOS:
            return [
                "ID_MovimientoStock", "Timestamp", "ID_Articulo", "DescripcionArticulo", "TipoMovimiento",
                "Cantidad", "StockAnterior", "StockNuevo", "ID_ReferenciaDocumento",
                "Usuario", "Notas", "CostoUnitarioMovimiento"
            ]
        elif sheet_name_value == SHEET_NAME_CONTABILIDAD_PLAN_CONFIG:
            return [
                "ID_CuentaConfig", "TipoElemento", "CodigoCuenta", "NombreCuenta_DescripcionConcepto",
                "TipoCuentaContable", "NivelJerarquia", "AdmiteImputaciones", "CuentaPadre_Codigo",
                "AlicuotaPorcentaje", "CuentaContableAsociadaDebe", "CuentaContableAsociadaHaber", "Activo"
            ]
        elif sheet_name_value == SHEET_NAME_CONTABILIDAD_ASIENTOS:
            return [
                "ID_AsientoResumido", "ID_AsientoAgrupador", "FechaContable", "TipoAsiento",
                "DescripcionGeneralAsiento", "ModuloOrigen", "ID_ReferenciaOrigen", "CodigoCuentaImputada",
                "NombreCuentaImputada", "ConceptoDetalleLinea", "Debe", "Haber", "CentroCosto_ID",
                "UsuarioRegistro", "TimestampRegistro"
            ]
        elif sheet_name_value == SHEET_NAME_ADMIN_TOKEN:
            return ["token", "fecha_generacion", "fecha_expiracion", "usuario_generador"]
        elif sheet_name_value == SHEET_NAME_USUARIOS:
            return ["ID_Usuario", "NombreUsuario", "NombreCompleto", "Rol", "PasswordHash", "Activo", "FechaCreacion", "Email"]
        elif sheet_name_value == SHEET_NAME_CONFIG_HORARIOS_CAJA:
            return ["ID_ConfigHorario", "DiaSemana", "HoraAperturaPermitida", "HoraCierrePermitida", "Activo", "Notas"]
        
        print(f"ADVERTENCIA (get_default_headers): No hay cabeceras definidas para la hoja '{sheet_name_value}'")
        return []

    # ... (resto de los métodos de GoogleSheetsHandler: get_all_records, append_row, etc.)
    # Estos no deberían necesitar cambios si usan sheet_name_value como parámetro.
    # Solo la lógica de get_next_id podría necesitar ajustes si los nombres de columna de ID cambian.

    def get_all_records(self, sheet_name_value):
        ws = self.get_worksheet(sheet_name_value)
        if ws:
            try: return ws.get_all_records()
            except Exception as e: print(f"Error en get_all_records para '{sheet_name_value}': {e}"); return []
        return []

    def append_row(self, sheet_name_value, data_row_list):
        ws = self.get_worksheet(sheet_name_value)
        if ws:
            try: ws.append_row(data_row_list, value_input_option='USER_ENTERED'); return True
            except Exception as e: print(f"Error en append_row para '{sheet_name_value}': {e}"); return False
        return False

    def get_row_by_id(self, sheet_name_value, id_value, id_column_name="ID"): # Asegúrate que id_column_name sea el correcto para cada hoja
        ws = self.get_worksheet(sheet_name_value)
        if not ws: return None, -1
        try:
            records = ws.get_all_records()
            for i, record in enumerate(records):
                if str(record.get(id_column_name)) == str(id_value):
                    return record, i + 2 # i + 2 porque gspread es 1-indexed y hay cabecera
            return None, -1
        except Exception as e:
            print(f"Error en get_row_by_id para '{sheet_name_value}', ID '{id_value}', Columna '{id_column_name}': {e}")
            return None, -1

    def update_row(self, sheet_name_value, row_index, data_row_list):
        ws = self.get_worksheet(sheet_name_value)
        if ws:
            try: ws.update(f'A{row_index}', [data_row_list], value_input_option='USER_ENTERED'); return True
            except Exception as e: print(f"Error en update_row para '{sheet_name_value}', fila {row_index}: {e}"); return False
        return False
        
    def update_cell(self, sheet_name_value, row, col, value_to_update):
        ws = self.get_worksheet(sheet_name_value)
        if ws:
            try: ws.update_cell(row, col, value_to_update); return True
            except Exception as e: print(f"Error actualizando celda ({row},{col}) en '{sheet_name_value}': {e}"); return False
        return False

    def _get_column_index(self, sheet_name_value, column_name):
        ws = self.get_worksheet(sheet_name_value)
        if not ws: return None
        try:
            headers = ws.row_values(1) # Asume que las cabeceras están en la fila 1
            return headers.index(column_name) + 1 # +1 porque es 1-indexed
        except ValueError: # Columna no encontrada
            # print(f"Advertencia: Columna '{column_name}' no encontrada en la hoja '{sheet_name_value}'.")
            return None
        except Exception as e:
            print(f"Error obteniendo índice de columna '{column_name}' en '{sheet_name_value}': {e}")
            return None

    def get_next_id(self, sheet_name_value, id_column_name): # id_column_name es el nombre exacto de la columna ID
        records = self.get_all_records(sheet_name_value)
        if not records: return 1
        max_id = 0
        # Asumir que todos los IDs son numéricos para este método simplificado
        for record in records:
            try:
                current_id = int(record.get(id_column_name, 0))
                if current_id > max_id: max_id = current_id
            except (ValueError, TypeError): pass # Ignorar si no es un número o está vacío
        return max_id + 1