# /home/sgi_user/proyectos/sistema_gestion_ima/back/testing/reporte_sheets_especial.py
# ARCHIVO AUTO-CONTENIDO PARA REPORTES ESPECIALES A GOOGLE SHEETS

# Esta es la "llave secreta" para acceder a esta API. El frontend de Netlify
# deberá enviar esta llave en la cabecera 'x-api-key'.
API_KEY = "12123ed2121312wdawd123ecd"

# === Configuración de Google Sheets ===
GOOGLE_SERVICE_ACCOUNT_FILE="credencial_IA.json"
TESTING_GOOGLE_SHEET_ID = "1jDd784ApjPGyI7jsFF_bwPhupsBid-yGSJ9K4hOUaqo"

# === Seguridad (JWT) ===
# Genera una clave secreta larga y aleatoria. Puedes usar un generador de contraseñas online.
SECRET_KEY_SEGURIDAD="una_clave_muy_larga_y_secreta_para_los_tokens"

import os
from datetime import datetime
from typing import List, Dict, Any

# --- Librerías de Terceros ---
import gspread
from google.oauth2.service_account import Credentials
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field

# --- Seguridad por API Key ---
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

def get_api_key(api_key: str = Security(api_key_header)):
    """Verifica que la API Key en la cabecera sea la correcta."""
    if api_key == API_KEY:
        return api_key
    else:
        raise HTTPException(
            status_code=403, detail="Acceso no autorizado: API Key inválida o no proporcionada."
        )

# --- Conexión con Google Sheets ---
HOJA_DE_CALCULO = None
try:
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    CREDENCIALES = Credentials.from_service_account_file(GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    CLIENTE_GSPREAD = gspread.authorize(CREDENCIALES)
    HOJA_DE_CALCULO = CLIENTE_GSPREAD.open_by_key(TESTING_GOOGLE_SHEET_ID)
    print("✅ Conexión con Google Sheets establecida.")
except Exception as e:
    print(f"❌ ERROR CRÍTICO AL INICIAR: No se pudo conectar a Google Sheets. Verifique las credenciales y el SHEET_ID. Error: {e}")

def _obtener_hoja(nombre_hoja: str):
    """Función de ayuda para obtener una pestaña de la hoja de cálculo."""
    if not HOJA_DE_CALCULO:
        raise ConnectionError("La conexión con Google Sheets no fue establecida.")
    try:
        return HOJA_DE_CALCULO.worksheet(nombre_hoja)
    except gspread.WorksheetNotFound:
        raise ValueError(f"La pestaña '{nombre_hoja}' no se encontró en la Hoja de Cálculo.")

# --- Schemas (Modelos de Datos para la API) ---
class ProductoSheet(BaseModel):
    id_producto: int = Field(alias="id producto")
    Codigo: str
    nombre: str
    precio: str
    precio_negocio: str = Field(alias="precio negocio")
    Descripcion: str
    cantidad: float
    unidad: str
    tipo_de_envase: str = Field(alias="tipo de envase")
    Activo: bool
    Etiqueta_Visual: str = Field(alias="Etiqueta Visual")
    Destino_Final: str = Field(alias="Destino Final")
    Observaciones: str

class ItemVenta(BaseModel):
    id_producto: int
    cantidad: float

class VentaCreate(BaseModel):
    items: List[ItemVenta]

# --- Inicialización de la Aplicación FastAPI ---
app = FastAPI(
    title="API de Simulación con Google Sheets",
    description="Endpoints que usan una Hoja de Cálculo como base de datos de lectura y escritura.",
    version="2.0.0"
)

# ===================================================================
# === 3. ENDPOINTS DE LA API
# ===================================================================

@app.get("/productos", response_model=List[Dict[str, Any]], dependencies=[Depends(get_api_key)], tags=["Simulación"])
def mostrar_productos_de_sheet():
    """
    Lee todos los datos de la pestaña 'STOCK' y los devuelve.
    La estructura de la respuesta coincide con las columnas de la hoja.
    """
    try:
        hoja_stock = _obtener_hoja("STOCK")
        return hoja_stock.get_all_records()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ocurrió un error al leer la hoja 'STOCK': {str(e)}")


@app.post("/registrar-movimiento", dependencies=[Depends(get_api_key)], tags=["Simulación"])
def registrar_movimiento_y_actualizar_stock(venta_data: VentaCreate):
    """
    Recibe una venta, la registra en la pestaña 'MOVIMIENTOS' y
    actualiza (resta) el stock en la pestaña 'STOCK' de la misma hoja.
    """
    try:
        hoja_movimientos = _obtener_hoja("MOVIMIENTOS")
        hoja_stock = _obtener_hoja("STOCK")
        
        productos_en_stock = hoja_stock.get_all_records()
        stock_dict = {prod["id producto"]: prod for prod in productos_en_stock}

        filas_para_movimientos = []
        actualizaciones_stock = []
        
        for item in venta_data.items:
            producto = stock_dict.get(item.id_producto)
            if not producto:
                raise HTTPException(status_code=404, detail=f"Producto con ID {item.id_producto} no encontrado en la hoja 'STOCK'.")
            
            stock_actual = float(producto["cantidad"])
            if stock_actual < item.cantidad:
                raise HTTPException(status_code=400, detail=f"Stock insuficiente para '{producto['nombre']}'. Stock actual: {stock_actual}, se solicitó: {item.cantidad}.")
            
            # --- Preparamos la fila para la hoja de MOVIMIENTOS ---
            # (Se omiten campos no relevantes para la simulación)
            monto = item.cantidad * float(str(producto["precio"]).replace("$",""))
            filas_para_movimientos.append([
                "", # ID Movimiento
                "", # ID Cliente
                "", # ID Ingresos
                "", # ID Repartidor
                "", # Repartidor
                "", # Fecha y Hora Entrega
                datetime.now().strftime('%Y-%m-%d'), # Fecha
                "Cliente Simulado", # Cliente
                "", # CUIT
                "", # Razon Social
                "VENTA", # Tipo de Movimiento
                "", # Nro Comprobante
                producto["Descripción"], # Descripción
                monto, # Monto
                "", # Foto Comprobante
                "Registrado por API de simulación" # Observaciones
            ])
            
            # --- Preparamos la actualización para la hoja de STOCK ---
            nuevo_stock = stock_actual - item.cantidad
            # Buscamos la fila del producto (índice + 2 porque la fila 1 es cabecera y es 1-based)
            fila_a_actualizar = productos_en_stock.index(producto) + 2
            # Gspread permite actualizar un rango de celdas, en este caso, la columna 'cantidad' (G)
            actualizaciones_stock.append({
                'range': f'G{fila_a_actualizar}',
                'values': [[nuevo_stock]],
            })

        # --- Ejecutamos las escrituras en Google Sheets ---
        if filas_para_movimientos:
            hoja_movimientos.append_rows(filas_para_movimientos, value_input_option='USER_ENTERED')
        if actualizaciones_stock:
            hoja_stock.batch_update(actualizaciones_stock)

        return {"status": "success", "message": "Movimiento registrado y stock actualizado en Google Sheets."}

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Ocurrió un error en la simulación: {str(e)}")