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


# ===================================================================
# === 2. IMPORTACIONES Y CONFIGURACIÓN INICIAL
# ===================================================================
# Todas las librerías necesarias para que el script funcione por sí solo.
# ===================================================================
# === 2. IMPORTACIONES Y CONFIGURACIÓN INICIAL
# ===================================================================
import os
import sys
from datetime import datetime
from typing import List

# --- Librerías de Terceros ---
import gspread
from google.oauth2.service_account import Credentials
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field

# Añadimos la ruta raíz del proyecto para que el script se pueda ejecutar desde allí
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))


# ===================================================================
# === 3. SEGURIDAD (Autenticación por API Key)
# ===================================================================

api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY:
        return api_key
    else:
        raise HTTPException(
            status_code=403, detail="Acceso no autorizado: API Key inválida o no proporcionada."
        )

# ===================================================================
# === 4. LÓGICA Y CONEXIÓN CON GOOGLE SHEETS
# ===================================================================

HOJA_DE_CALCULO_SIMULACION = None
try:
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    CREDENCIALES = Credentials.from_service_account_file(GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    CLIENTE_GSPREAD = gspread.authorize(CREDENCIALES)
    HOJA_DE_CALCULO_SIMULACION = CLIENTE_GSPREAD.open_by_key(TESTING_GOOGLE_SHEET_ID)
    print("✅ Conexión con Google Sheets para simulación establecida.")
except Exception as e:
    print(f"❌ ERROR CRÍTICO: No se pudo conectar a Google Sheets. Error: {e}")

def _obtener_hoja(nombre_hoja: str):
    if not HOJA_DE_CALCULO_SIMULACION:
        raise ConnectionError("La conexión con Google Sheets no fue establecida.")
    try:
        return HOJA_DE_CALCULO_SIMULACION.worksheet(nombre_hoja)
    except gspread.WorksheetNotFound:
        raise ValueError(f"La pestaña '{nombre_hoja}' no se encontró en la Hoja de Cálculo.")

# ===================================================================
# === 5. SCHEMAS (Modelos de Datos para la API)
# ===================================================================

class ProductoSheet(BaseModel):
    ID: int
    Codigo_Interno: str = Field(alias="Codigo Interno") # Permite mapear nombres con espacios
    Descripcion: str
    Precio_Venta: float = Field(alias="Precio Venta")
    Stock_Actual: float = Field(alias="Stock Actual")

class ItemVentaSimulada(BaseModel):
    id_producto: int
    cantidad: float

class VentaSimuladaCreate(BaseModel):
    items: List[ItemVentaSimulada]

# ===================================================================
# === 6. APLICACIÓN Y ENDPOINTS DE LA API
# ===================================================================

app = FastAPI(
    title="API de Simulación de Stock y Ventas",
    description="Endpoints que usan Google Sheets como base de datos.",
    version="1.0.0"
)

# --- Endpoint para MOSTRAR los productos ---
@app.get("/productos", response_model=List[ProductoSheet], dependencies=[Depends(get_api_key)], tags=["Simulación"])
def api_mostrar_productos_desde_sheet():
    """
    Lee todos los datos de la pestaña 'Productos' y los devuelve.
    """
    try:
        hoja_productos = _obtener_hoja("Productos")
        # get_all_records() convierte la hoja en una lista de diccionarios, ideal para APIs
        productos = hoja_productos.get_all_records()
        return productos
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ocurrió un error al leer la hoja: {str(e)}")


# --- Endpoint para REGISTRAR una venta y MOVER stock ---
@app.post("/registrar-venta", dependencies=[Depends(get_api_key)], tags=["Simulación"])
def api_registrar_venta_simulada(venta_data: VentaSimuladaCreate):
    """
    Recibe una lista de productos y cantidades, los registra en la pestaña 'Ventas'
    y actualiza (resta) el stock en la pestaña 'Productos'.
    """
    try:
        hoja_ventas = _obtener_hoja("Ventas")
        hoja_productos = _obtener_hoja("Productos")
        
        # Leemos todos los productos en memoria para una simulación rápida
        productos_en_sheet = hoja_productos.get_all_records()
        # Creamos un diccionario para buscar productos por ID fácilmente
        productos_dict = {prod["ID"]: prod for prod in productos_en_sheet}

        filas_para_ventas = []
        actualizaciones_stock = []
        
        for item in venta_data.items:
            producto = productos_dict.get(item.id_producto)
            if not producto:
                raise HTTPException(status_code=404, detail=f"Producto con ID {item.id_producto} no encontrado en la hoja.")
            
            stock_actual = float(producto["Stock Actual"])
            if stock_actual < item.cantidad:
                raise HTTPException(status_code=400, detail=f"Stock insuficiente para '{producto['Descripcion']}'. Stock actual: {stock_actual}, se solicitó: {item.cantidad}.")
            
            # Preparamos la fila para la hoja de Ventas
            subtotal = item.cantidad * float(producto["Precio Venta"])
            filas_para_ventas.append([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                producto["ID"], producto["Descripcion"], item.cantidad,
                producto["Precio Venta"], subtotal
            ])
            
            # Preparamos la actualización de stock para la hoja de Productos
            nuevo_stock = stock_actual - item.cantidad
            # Buscamos la fila del producto (índice + 2 porque la fila 1 es cabecera y es 1-based)
            fila_a_actualizar = productos_en_sheet.index(producto) + 2
            # Gspread permite actualizar un rango de celdas, en este caso, una sola celda 'E{fila}'
            actualizaciones_stock.append({
                'range': f'E{fila_a_actualizar}',
                'values': [[nuevo_stock]],
            })

        # Si todas las validaciones pasaron, ejecutamos las escrituras
        if filas_para_ventas:
            hoja_ventas.append_rows(filas_para_ventas)
        if actualizaciones_stock:
            # batch_update es la forma más eficiente de actualizar múltiples celdas
            hoja_productos.batch_update(actualizaciones_stock)

        return {"status": "success", "message": "Venta simulada registrada y stock actualizado."}

    except Exception as e:
        # Si es una excepción que ya hemos lanzado nosotros, la relanzamos
        if isinstance(e, HTTPException):
            raise e
        # Para cualquier otro error (conexión, etc.)
        raise HTTPException(status_code=500, detail=f"Ocurrió un error: {str(e)}")