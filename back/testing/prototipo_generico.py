# /home/sgi_user/proyectos/sistema_gestion_ima/back/testing/reporte_sheets_especial.py
# VERSIÓN FINAL CON EL ROUTER Y PREFIJO CORRECTAMENTE IMPLEMENTADOS

# ===================================================================
# === 1. CONFIGURACIÓN
# ===================================================================

API_KEY = "12123ed2121312wdawd123ecd"
GOOGLE_SERVICE_ACCOUNT_FILE = "back/credencial_IA.json" 
TESTING_GOOGLE_SHEET_ID = "1jDd784ApjPGyI7jsFF_bwPhupsBid-yGSJ9K4hOUaqo"

# ===================================================================
# === 2. IMPORTACIONES Y CÓDIGO DEL SERVIDOR
# ===================================================================

from datetime import datetime
from typing import List, Dict, Any

import gspread
from google.oauth2.service_account import Credentials
# --- CORRECCIÓN: Importamos APIRouter ---
from fastapi import FastAPI, Depends, HTTPException, Security, APIRouter
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# --- Inicialización de la Aplicación FastAPI ---
app = FastAPI(
    title="API de Simulación con Google Sheets",
    description="Endpoints que usan una Hoja de Cálculo como base de datos.",
    version="3.0.0"
)

# --- Configuración de CORS ---
origins = [
    "https://imaconsultora.netlify.app",
    "http://localhost", "http://localhost:3000", "http://localhost:5173",
]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- Seguridad por API Key ---
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)
def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY: return api_key
    else: raise HTTPException(status_code=403, detail="Acceso no autorizado.")

# --- Lógica de Google Sheets (sin cambios) ---
HOJA_DE_CALCULO = None
try:
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    CREDENCIALES = Credentials.from_service_account_file(GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    CLIENTE_GSPREAD = gspread.authorize(CREDENCIALES)
    HOJA_DE_CALCULO = CLIENTE_GSPREAD.open_by_key(TESTING_GOOGLE_SHEET_ID)
    print("✅ Conexión con Google Sheets establecida.")
except Exception as e:
    print(f"❌ ERROR CRÍTICO AL INICIAR: {e}")

def _obtener_hoja(nombre_hoja: str):
    if not HOJA_DE_CALCULO: raise ConnectionError("Conexión con Sheets no establecida.")
    try: return HOJA_DE_CALCULO.worksheet(nombre_hoja)
    except gspread.WorksheetNotFound: raise ValueError(f"Pestaña '{nombre_hoja}' no encontrada.")

# --- Schemas (sin cambios) ---
class ItemVenta(BaseModel): id_producto: int; cantidad: float
class VentaCreate(BaseModel): items: List[ItemVenta]

# ===================================================================
# === 3. ENDPOINTS DE LA API (AHORA USANDO EL ROUTER)
# ===================================================================

# Creamos el Router con nuestro prefijo
router = APIRouter(
    prefix="/prototipo",
    dependencies=[Depends(get_api_key)],
    tags=["Prototipo"]
)

# --- CORRECCIÓN: Usamos '@router.get' en lugar de '@app.get' ---
@router.get("/productos", response_model=List[Dict[str, Any]])
def mostrar_productos_de_sheet():
    """Lee y devuelve los datos de la pestaña 'STOCK'."""
    try:
        return _obtener_hoja("STOCK").get_all_records()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- CORRECCIÓN: Usamos '@router.post' en lugar de '@app.post' ---
@router.post("/registrar-movimiento")
def registrar_movimiento_y_actualizar_stock(venta_data: VentaCreate):
    """Registra una venta en 'MOVIMIENTOS' y actualiza el stock en 'STOCK'."""
    try:
        hoja_movimientos = _obtener_hoja("MOVIMIENTOS")
        hoja_stock = _obtener_hoja("STOCK")
        
        productos_en_stock = hoja_stock.get_all_records()
        stock_dict = {prod["id producto"]: prod for prod in productos_en_stock}

        filas_para_movimientos, actualizaciones_stock = [], []
        
        for item in venta_data.items:
            producto = stock_dict.get(item.id_producto)
            if not producto: raise HTTPException(status_code=404, detail=f"Producto con ID {item.id_producto} no encontrado.")
            stock_actual = float(producto["cantidad"])
            if stock_actual < item.cantidad: raise HTTPException(status_code=400, detail=f"Stock insuficiente para '{producto['nombre']}'.")
            
            monto = item.cantidad * float(str(producto["precio"]).replace("$","").replace(".","").replace(",","."))
            filas_para_movimientos.append(["", "", "", "", "", "", datetime.now().strftime('%Y-%m-%d'), "Cliente Simulado", "", "", "VENTA", "", producto["Descripción"], monto, "", "API Sim."])
            
            nuevo_stock = stock_actual - item.cantidad
            fila_a_actualizar = productos_en_stock.index(producto) + 2
            actualizaciones_stock.append({ 'range': f'G{fila_a_actualizar}', 'values': [[nuevo_stock]] })

        if filas_para_movimientos: hoja_movimientos.append_rows(filas_para_movimientos, value_input_option='USER_ENTERED')
        if actualizaciones_stock: hoja_stock.batch_update(actualizaciones_stock)

        return {"status": "success", "message": "Movimiento registrado y stock actualizado."}
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))

# --- CORRECCIÓN: Incluimos el router en la aplicación principal ---
app.include_router(router)