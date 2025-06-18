# back/utils/sheets_google_handler.py
import gspread
from google.oauth2.service_account import Credentials
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

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file']

class GoogleSheetsHandler:
    def __init__(self, sheet_id: Optional[str] = None):
        # ... (el __init__ que te di antes, sin cambios)
        self.creds = Credentials.from_service_account_file(GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        self.client = gspread.authorize(self.creds)
        self.sheet_id = sheet_id or GOOGLE_SHEET_ID
        try:
            self.spreadsheet = self.client.open_by_key(self.sheet_id)
        except gspread.exceptions.SpreadsheetNotFound:
            print(f"Error Crítico (GSheetsHandler): Spreadsheet con ID '{self.sheet_id}' no encontrado.")
            raise
        except Exception as e:
            print(f"Error Crítico (GSheetsHandler) conectando a Google Sheets: {e}")
            raise

    def get_worksheet(self, sheet_name_from_config_variable: str) -> Optional[gspread.Worksheet]:
        # ... (la función get_worksheet que te di antes, sin cambios)
        if not self.spreadsheet:
            print("Error (get_worksheet): No hay conexión al spreadsheet.")
            return None
        try:
            return self.spreadsheet.worksheet(sheet_name_from_config_variable)
        except gspread.exceptions.WorksheetNotFound:
            print(f"Advertencia (get_worksheet): Hoja '{sheet_name_from_config_variable}' no encontrada. Creándola...")
            default_headers = self.get_default_headers(sheet_name_from_config_variable)
            if not default_headers:
                print(f"Error (get_worksheet): No se definieron cabeceras para '{sheet_name_from_config_variable}'. Hoja NO creada.")
                return None
            try:
                num_cols = len(default_headers) if default_headers else 20
                worksheet = self.spreadsheet.add_worksheet(title=sheet_name_from_config_variable, rows="100", cols=str(num_cols))
                if default_headers:
                    worksheet.update('A1', [default_headers], value_input_option='USER_ENTERED')
                    worksheet.freeze(rows=1)
                print(f"Hoja '{sheet_name_from_config_variable}' creada con cabeceras.")
                return worksheet
            except Exception as e_create:
                print(f"Error (get_worksheet) creando la hoja '{sheet_name_from_config_variable}': {e_create}")
                return None
        except Exception as e_get:
            print(f"Error (get_worksheet) obteniendo la hoja '{sheet_name_from_config_variable}': {e_get}")
            return None


    def get_default_headers(self, sheet_name_value: str) -> List[str]:
        # sheet_name_value es el string con el nombre de la hoja
        # que viene de una de las variables de config.py

        if sheet_name_value == CONFIGURACION_GLOBAL_SHEET:
            return [
                "ID_Config", # PK Autoincremental o UUID
                "ConfigKey", # Clave única de la configuración (ej: "ADMIN_TOKEN_DATA", "HORARIO_LUNES_APERTURA")
                "ConfigValue", # Valor principal
                "SubValue1", # Para datos estructurados (ej: para token -> el token en sí)
                "SubValue2", # (ej: para token -> fecha_generacion)
                "SubValue3", # (ej: para token -> fecha_expiracion)
                "SubValue4", # (ej: para token -> usuario_generador)
                "TipoDato", # (ej: "STRING", "JSON", "INTEGER", "BOOLEAN")
                "Descripcion",
                "ModuloAfectado", # (ej: "AUTH", "CAJA_HORARIOS", "SISTEMA")
                "Activo", # (TRUE/FALSE)
                "FechaUltimaModificacion",
                "UsuarioUltimaModificacion"
            ]
        elif sheet_name_value == USUARIOS_SHEET:
            return [
                "ID_Usuario", # PK Autoincremental o UUID
                "NombreUsuario", # Login único
                "NombreCompleto",
                "PasswordHash", # Si se usa autenticación por contraseña
                "RolPrincipal", # (Ej: "Administrador", "Cajero", "Comprador", "Vendedor")
                "RolesSecundarios", # (Lista separada por comas si un usuario tiene múltiples roles)
                "Email",
                "Telefono",
                "Activo", # (TRUE/FALSE)
                "FechaCreacion",
                "FechaUltimaModificacion",
                "UltimoAccesoTimestamp",
                "NotasAdministrativas"
            ]
        elif sheet_name_value == TERCEROS_SHEET: # Para Clientes y Proveedores
            return [
                "ID_Tercero", # PK Autoincremental o UUID
                "CodigoInterno", # Opcional, si manejas códigos para terceros
                "TipoTercero", # "CLIENTE", "PROVEEDOR", "AMBOS"
                "NombreComercial_RazonSocial",
                "NombreFantasia",
                "IdentificacionFiscal", # CUIT/CUIL/DNI/etc.
                "TipoIdentificacion", # (Ej: "CUIT", "DNI", "PASAPORTE")
                "CondicionIVA", # (Ej: "Monotributista", "Responsable Inscripto", "Exento", "Consumidor Final")
                "DireccionCompleta",
                "Localidad",
                "Provincia_Estado",
                "CodigoPostal",
                "Pais",
                "TelefonoPrincipal",
                "TelefonoAlternativo",
                "EmailPrincipal",
                "EmailFacturacion",
                "NombreContactoPrincipal",
                "CargoContactoPrincipal",
                "TelefonoContactoPrincipal",
                "EmailContactoPrincipal",
                "ID_VendedorAsignado", # FK a Usuarios.ID_Usuario (si aplica para clientes)
                "ID_CompradorAsignado",# FK a Usuarios.ID_Usuario (si aplica para proveedores)
                "ID_ListaPreciosDefault", # Si manejas listas de precios
                "ID_CondicionPagoDefault",# Si manejas condiciones de pago
                "DiasPlazoPagoHabitual",
                "LimiteCredito",
                "SaldoCuentaCorriente", # Actualizado por transacciones
                "MonedaSaldoCC",
                "Activo", # (TRUE/FALSE)
                "FechaAlta",
                "FechaUltimaModificacion",
                "NotasGenerales"
            ]
        elif sheet_name_value == ARTICULOS_SHEET:
            return [
                "ID_Articulo", # PK (puede ser tu código PROD001 o un ID numérico)
                "CodigoBarrasEAN", # SKU, Código de Barras
                "CodigoInternoAlternativo",
                "DescripcionPrincipal",
                "DescripcionAmpliada",
                "TipoArticulo", # "PRODUCTO", "SERVICIO", "MATERIA_PRIMA", "COMBO"
                "ID_Categoria", # FK (podrías tener una hoja 'CategoriasArticulos')
                "NombreCategoria", # Denormalizado para búsquedas rápidas
                "ID_Subcategoria",
                "NombreSubcategoria",
                "ID_Marca", # FK (podrías tener una hoja 'Marcas')
                "NombreMarca", # Denormalizado
                "ID_UnidadMedidaCompra", # FK (podrías tener hoja 'UnidadesMedida')
                "NombreUnidadMedidaCompra",
                "ID_UnidadMedidaVenta",
                "NombreUnidadMedidaVenta",
                "FactorConversionCompraVenta", # Si son distintas (ej: Caja de 12 UN)
                "PrecioCostoUltimaCompra",
                "PrecioCostoPromedioPonderado",
                "MonedaCosto",
                "PrecioVentaBaseNeto", # Precio sin IVA
                "PorcentajeIVAVenta", # Ej: 21, 10.5, 0
                "MontoIVAVenta", # Calculado: PrecioVentaBaseNeto * PorcentajeIVAVenta / 100
                "PrecioVentaFinalConIVA", # Calculado: PrecioVentaBaseNeto + MontoIVAVenta
                "MonedaVenta",
                "StockActual",
                "StockMinimoAdvertencia",
                "StockMaximoSugerido",
                "StockReservado", # Para pedidos pendientes de entrega
                "StockComprometido", # Para órdenes de compra pendientes de recibir
                "UbicacionFisica", # (Ej: Estantería A, Fila 3)
                "ID_ProveedorPreferido", # FK a Terceros.ID_Tercero
                "NombreProveedorPreferido",
                "CodigoArticuloProveedor", # Código del artículo para ese proveedor
                "Activo", # (TRUE/FALSE, para discontinuar)
                "EsPerecedero", # (TRUE/FALSE)
                "DiasVidaUtil", # Si es perecedero
                "ManejaLotes", # (TRUE/FALSE)
                "ManejaSeries", # (TRUE/FALSE)
                "PesoNeto",
                "UnidadPeso", # (Ej: KG, GR, LB)
                "Volumen",
                "UnidadVolumen", # (Ej: M3, LT, CM3)
                "FechaCreacion",
                "FechaUltimaModificacion",
                "UsuarioUltimaModificacion",
                "Notas",
                "URLImagenPrincipal"
            ]
        elif sheet_name_value == CAJA_SESIONES_SHEET:
            return [
                "ID_Sesion", # PK Autoincremental
                "FechaApertura",
                "HoraApertura",
                "ID_UsuarioApertura", # FK a Usuarios.ID_Usuario
                "NombreUsuarioApertura",
                "SaldoInicialDeclarado", # Dinero contado al abrir
                "MonedaSaldoInicial",
                "FechaCierre",
                "HoraCierre",
                "ID_UsuarioCierre", # FK a Usuarios.ID_Usuario
                "NombreUsuarioCierre",
                "SaldoFinalContado", # Dinero contado al cerrar
                "TotalVentasEfectivo_Calculado",
                "TotalVentasTarjeta_Calculado",
                "TotalVentasOtrosMedios_Calculado",
                "TotalIngresosAdicionales_Calculado",
                "TotalEgresos_Calculado",
                "SaldoFinalTeorico_Calculado", # SaldoInicial + Ingresos - Egresos
                "DiferenciaCaja", # SaldoFinalContado - SaldoFinalTeorico
                "EstadoSesion", # "ABIERTA", "CERRADA", "AUDITADA"
                "ObservacionesApertura",
                "ObservacionesCierre",
                "PuntoDeVentaID" # Si tienes múltiples cajas físicas
            ]
        elif sheet_name_value == CAJA_MOVIMIENTOS_SHEET: # Unifica ventas, ingresos, egresos y detalles
            return [
                "ID_Movimiento", # PK Autoincremental
                "ID_SesionCaja", # FK a CajaSesiones.ID_Sesion
                "TimestampMovimiento", # Fecha y Hora exacta
                "ID_UsuarioOperacion", # FK a Usuarios.ID_Usuario
                "NombreUsuarioOperacion",
                "TipoRegistro", # "VENTA_ITEM", "VENTA_PAGO_TOTAL", "INGRESO_CAJA", "EGRESO_CAJA", "APERTURA_SALDO", "CIERRE_SALDO"
                "DescripcionConcepto", # Detalle del movimiento
                "ID_DocumentoVentaAsociado", # Si se genera una factura/remito separado (FK a una futura hoja VentasCabecera)
                "ID_VentaAgrupador", # Para agrupar items de una misma venta y su pago total. Podría ser un UUID o el ID_Movimiento del "VENTA_PAGO_TOTAL".
                "ID_Articulo", # FK a Articulos.ID_Articulo (solo para VENTA_ITEM)
                "CodigoArticulo", # Denormalizado
                "DescripcionArticulo", # Denormalizado
                "Cantidad", # (Para VENTA_ITEM, positivo. Podría ser negativo para devoluciones de item)
                "PrecioUnitarioOriginal", # (Para VENTA_ITEM)
                "DescuentoPorcentajeItem",
                "DescuentoMontoItem",
                "PrecioUnitarioConDescuento",
                "SubtotalItemNeto", # Cantidad * PrecioUnitarioConDescuento
                "TasaIVAItem",
                "MontoIVAItem",
                "SubtotalItemConIVA",
                "MontoMovimiento", # Para INGRESO_CAJA (+), EGRESO_CAJA (-), VENTA_PAGO_TOTAL (+)
                "MetodoPago", # (Para VENTA_PAGO_TOTAL, ej: "EFECTIVO", "TARJETA_DEBITO", "TARJETA_CREDITO", "TRANSFERENCIA", "MP")
                "ReferenciaMetodoPago", # (Ej: Últimos 4 dígitos tarjeta, ID transacción MP)
                "ID_TerceroCliente", # FK a Terceros.ID_Tercero (para VENTA_PAGO_TOTAL)
                "NombreCliente", # Denormalizado
                "ID_TerceroProveedorDestino", # FK a Terceros.ID_Tercero (para EGRESO_CAJA si es a un proveedor)
                "ComprobanteExternoReferencia", # (Ej: Nro de factura de proveedor para un egreso)
                "EstadoMovimiento", # (Ej: "CONFIRMADO", "ANULADO")
                "ID_MovimientoAnuladoOriginal", # Si este movimiento anula a otro
                "NotasAdicionales"
            ]
        elif sheet_name_value == STOCK_MOVIMIENTOS_SHEET:
            return [
                "ID_StockMov", # PK Autoincremental
                "TimestampMovimiento",
                "ID_Articulo", # FK a Articulos.ID_Articulo
                "CodigoArticulo",
                "DescripcionArticulo",
                "TipoMovimientoStock", # "INGRESO_COMPRA", "SALIDA_VENTA", "AJUSTE_POSITIVO", "AJUSTE_NEGATIVO", "DEVOLUCION_CLIENTE", "DEVOLUCION_PROVEEDOR", "TRASLADO_ENTRADA", "TRASLADO_SALIDA", "PRODUCCION_ENTRADA", "PRODUCCION_SALIDA"
                "Cantidad", # Positivo para entradas, negativo para salidas
                "UnidadMedida",
                "StockAnteriorCalculado", # Stock del artículo ANTES de este movimiento
                "StockNuevoCalculado", # Stock del artículo DESPUÉS de este movimiento
                "CostoUnitarioMovimiento", # Costo al que se mueve el stock (importante para compras, ajustes valorizados)
                "ValorTotalMovimiento", # Cantidad * CostoUnitarioMovimiento
                "ID_DocumentoReferencia", # Ej: ID_Compra, ID_Movimiento de Caja (venta), ID_Ajuste
                "TipoDocumentoReferencia", # "COMPRA", "VENTA_CAJA", "AJUSTE_MANUAL"
                "ID_AlmacenOrigen", # Si manejas múltiples almacenes
                "ID_AlmacenDestino",
                "Lote",
                "FechaVencimientoLote",
                "ID_UsuarioResponsable", # FK a Usuarios.ID_Usuario
                "NombreUsuarioResponsable",
                "Observaciones"
            ]
        elif sheet_name_value == COMPRAS_CABECERA_SHEET: # Para Órdenes de Compra y Facturas de Proveedor
            return [
                "ID_DocCompra", # PK Autoincremental
                "TipoDocumento", # "ORDEN_COMPRA", "FACTURA_PROVEEDOR", "REMITO_PROVEEDOR", "NOTA_CREDITO_PROV", "NOTA_DEBITO_PROV"
                "NumeroDocumentoInterno", # Para OC generadas por el sistema
                "NumeroDocumentoProveedor", # Para Facturas/Remitos del proveedor
                "ID_TerceroProveedor", # FK a Terceros.ID_Tercero
                "NombreProveedor",
                "FechaEmisionDocumento", # Fecha de la factura del proveedor o de creación de la OC
                "FechaRecepcionMercaderiaEstimada", # Para OC
                "FechaRecepcionMercaderiaReal",
                "SubtotalNetoGravado",
                "SubtotalNetoNoGravado",
                "DescuentoGlobalMonto",
                "DescuentoGlobalPorcentaje",
                "MontoIVA_21", # O tasas específicas que manejes
                "MontoIVA_10_5",
                "MontoIVA_Otros",
                "TotalIVA",
                "MontoPercepcionIVA",
                "MontoPercepcionIIBB",
                "OtrosImpuestosRetenciones",
                "TotalDocumento",
                "Moneda",
                "TipoCambio", # Si es en otra moneda
                "EstadoDocumento", # "BORRADOR", "EMITIDA", "ENVIADA_PROVEEDOR", "APROBADA", "RECHAZADA", "RECIBIDA_PARCIAL", "RECIBIDA_TOTAL", "FACTURADA", "PAGADA_PARCIAL", "PAGADA_TOTAL", "ANULADA"
                "ID_UsuarioCreador", # FK a Usuarios.ID_Usuario
                "NombreUsuarioCreador",
                "FechaCreacionSistema",
                "ID_UsuarioUltimaModificacion",
                "FechaUltimaModificacionSistema",
                "CondicionesPago", # (Ej: "Contado", "30 días FF")
                "MedioTransporte",
                "LugarEntrega",
                "Observaciones"
            ]
        elif sheet_name_value == COMPRAS_DETALLE_SHEET: # Ítems de los documentos de compra
            return [
                "ID_CompraDetalle", # PK Autoincremental
                "ID_DocCompra", # FK a ComprasCabecera.ID_DocCompra
                "ID_Articulo", # FK a Articulos.ID_Articulo
                "CodigoArticuloSistema",
                "CodigoArticuloProveedor", # El código que usa el proveedor para este artículo
                "DescripcionArticulo", # Puede ser la del proveedor o la tuya
                "CantidadPedida", # Para OC
                "CantidadRecibida", # Para Remitos/Facturas
                "UnidadMedidaCompra",
                "PrecioUnitarioNetoAcordado", # Costo sin IVA
                "PorcentajeDescuentoItem",
                "MontoDescuentoItem",
                "PrecioUnitarioNetoConDescuento",
                "TasaIVAItem", # Ej: 21, 10.5
                "MontoIVAItem",
                "SubtotalItemConIVA", # Cantidad * PrecioUnitarioConDescuento + MontoIVAItem
                "LoteIngresado",
                "FechaVencimientoLote",
                "NumeroSerieIngresado", # Si aplica
                "EstadoItem", # "PENDIENTE_RECIBIR", "RECIBIDO_OK", "RECIBIDO_CON_DIFERENCIA", "DEVUELTO"
                "NotasItem"
            ]

        # --- Hojas Opcionales (Descomenta y define si las vas a usar en config.py y .env) ---
        # elif sheet_name_value == VENTAS_CABECERA_SHEET:
        #     return ["ID_DocVenta", "TipoDocumento", "NumeroComprobante", "ID_TerceroCliente", "NombreCliente", "FechaEmision", "TotalNeto", "TotalIVA", "TotalGeneral", "Estado", "ID_SesionCaja", "ID_UsuarioVendedor", "CAE", "FechaVtoCAE", "Notas"]
        # elif sheet_name_value == VENTAS_DETALLE_SHEET:
        #     return ["ID_VentaDetalle", "ID_DocVenta", "ID_Articulo", "CodigoArticulo", "DescripcionArticulo", "Cantidad", "PrecioUnitarioNeto", "PorcentajeDescuento", "SubtotalNeto", "TasaIVA", "MontoIVA", "SubtotalConIVA"]
        # elif sheet_name_value == VENTAS_PAGOS_SHEET:
        #     return ["ID_VentaPago", "ID_DocVenta", "FechaPago", "MetodoPago", "MontoPagado", "ReferenciaPago", "ID_CuentaBancaria", "Notas"]
        # elif sheet_name_value == ADMIN_TOKEN_SHEET: # Si la quieres separada de ConfiguracionGlobal
        #     return ["token", "fecha_generacion", "fecha_expiracion", "usuario_generador", "activo"]
        # elif sheet_name_value == STOCK_LISTAS_CONFIG_SHEET: # Para categorías, marcas, unidades, etc.
        #     return ["ID_ItemLista", "TipoLista", "CodigoItem", "NombreItem", "DescripcionAdicional", "ValorExtra1", "Activo"]
        # elif sheet_name_value == CONTABILIDAD_PLAN_SHEET:
        #     return ["ID_CuentaContable", "CodigoCuenta", "NombreCuenta", "TipoCuenta", "Nivel", "PermiteMovimientos", "ID_CuentaPadre", "NaturalezaSaldo", "Activa"]
        # elif sheet_name_value == CONTABILIDAD_ASIENTOS_SHEET:
        #     return ["ID_Asiento", "FechaAsiento", "NumeroAsiento", "DescripcionAsiento", "EstadoAsiento", "ID_UsuarioCreacion", "TimestampCreacion", "ID_AsientoLinea", "ID_CuentaContable", "ConceptoLinea", "Debe", "Haber", "CentroCosto"]
        else:
            print(f"ADVERTENCIA (get_default_headers): No hay cabeceras definidas para la hoja '{sheet_name_value}'. Se creará vacía si no existe o no se podrán añadir cabeceras.")
            return []


    # ... (resto de tus métodos: get_all_records, append_row, etc. SIN CAMBIOS)
    def get_all_records(self, sheet_name_value: str) -> List[Dict]:
        ws = self.get_worksheet(sheet_name_value)
        if ws:
            try: return ws.get_all_records()
            except Exception as e: print(f"Error en get_all_records para '{sheet_name_value}': {e}"); return []
        return []

    def append_row(self, sheet_name_value: str, data_row_list: List[Any]) -> bool:
        ws = self.get_worksheet(sheet_name_value)
        if ws:
            try: ws.append_row(data_row_list, value_input_option='USER_ENTERED'); return True
            except Exception as e: print(f"Error en append_row para '{sheet_name_value}': {e}"); return False
        return False

    def get_row_by_id(self, sheet_name_value: str, id_value: Any, id_column_name: str) -> Tuple[Optional[Dict], int]:
        ws = self.get_worksheet(sheet_name_value)
        if not ws: return None, -1
        try:
            records = ws.get_all_records()
            for i, record in enumerate(records):
                # Asegurarse de que ambos sean string para la comparación si los IDs pueden ser numéricos o texto
                if record.get(id_column_name) is not None and str(record.get(id_column_name)) == str(id_value):
                    return record, i + 2
            return None, -1
        except Exception as e:
            print(f"Error en get_row_by_id para '{sheet_name_value}', ID '{id_value}', Columna '{id_column_name}': {e}")
            return None, -1

    def update_row(self, sheet_name_value: str, row_index: int, data_row_list: List[Any]) -> bool:
        ws = self.get_worksheet(sheet_name_value)
        if ws:
            try: ws.update(f'A{row_index}', [data_row_list], value_input_option='USER_ENTERED'); return True
            except Exception as e: print(f"Error en update_row para '{sheet_name_value}', fila {row_index}: {e}"); return False
        return False

    def update_cell(self, sheet_name_value: str, row: int, col: int, value_to_update: Any) -> bool:
        ws = self.get_worksheet(sheet_name_value)
        if ws:
            try: ws.update_cell(row, col, value_to_update); return True
            except Exception as e: print(f"Error actualizando celda ({row},{col}) en '{sheet_name_value}': {e}"); return False
        return False

    def _get_column_index(self, sheet_name_value: str, column_name: str) -> Optional[int]:
        ws = self.get_worksheet(sheet_name_value)
        if not ws: return None
        try:
            headers = ws.row_values(1)
            return headers.index(column_name) + 1
        except ValueError: # Columna no encontrada
            # print(f"Advertencia: Columna '{column_name}' no encontrada en '{sheet_name_value}'") # Puede ser muy verboso
            return None
        except Exception as e:
            print(f"Error obteniendo índice de columna '{column_name}' en '{sheet_name_value}': {e}")
            return None

    def get_next_id(self, sheet_name_value: str, id_column_name: str) -> int:
        records = self.get_all_records(sheet_name_value)
        if not records: return 1
        max_id = 0
        for record in records:
            try:
                id_val_str = record.get(id_column_name)
                if id_val_str is not None and str(id_val_str).strip() != "":
                    current_id = int(id_val_str) # Asume IDs numéricos para autoincremento simple
                    if current_id > max_id: max_id = current_id
            except (ValueError, TypeError):
                # print(f"Advertencia: ID no numérico encontrado '{id_val_str}' en {id_column_name} de {sheet_name_value}")
                pass # Ignorar si no es un número válido, podría ser un UUID o código
        return max_id + 1