# /home/sgi_user/proyectos/sistema_gestion_ima/back/testing/reporte_sheets_especial.py
# VERSIÓN FINAL CON CORS CORREGIDO Y PRINTS DE DEBUGGING

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
from fastapi import FastAPI, Depends, HTTPException, Security, Request # <--- AÑADIDO Request
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# --- Inicialización de la Aplicación FastAPI ---
app = FastAPI(
    title="API de Simulación con Google Sheets (MODO DEBUG)",
    description="Endpoints que usan una Hoja de Cálculo como base de datos de lectura y escritura.",
    version="2.2.0"
)

# --- INICIO DE LA CONFIGURACIÓN DE CORS (CON CORRECCIÓN) ---
origins = [
    "https://imaconsultora.netlify.app",
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",
    # CORRECCIÓN: Se elimina la URL del propio backend de esta lista.
    # La lista 'origins' es para los DOMINIOS DEL FRONTEND que tienen permiso.
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --- FIN DE LA CONFIGURACIÓN DE CORS ---


# --- Seguridad por API Key con Prints de Debugging ---
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

def get_api_key(request: Request, api_key_from_header: str = Security(api_key_header)):
    """Verifica la API Key e imprime información de debugging."""
    print("\n--- [DEBUG] INICIANDO CHEQUEO DE SEGURIDAD ---")
    print(f"--- [DEBUG] Cabeceras recibidas: {request.headers}")
    print(f"--- [DEBUG] API Key recibida en la cabecera 'x-api-key': '{api_key_from_header}'")
    
    if api_key_from_header == API_KEY:
        print("--- [DEBUG] ✅ API Key correcta. Acceso permitido.")
        return api_key_from_header
    else:
        print(f"--- [DEBUG] ❌ API Key incorrecta o no encontrada. Acceso denegado.")
        raise HTTPException(
            status_code=403, detail="Acceso no autorizado: API Key inválida o no proporcionada."
        )

# --- Conexión con Google Sheets ---
# (Sin cambios aquí, los prints que tenías ya son buenos)
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
    if not HOJA_DE_CALCULO:
        raise ConnectionError("La conexión con Google Sheets no fue establecida.")
    try:
        return HOJA_DE_CALCULO.worksheet(nombre_hoja)
    except gspread.WorksheetNotFound:
        raise ValueError(f"La pestaña '{nombre_hoja}' no se encontró en la Hoja de Cálculo.")

# --- Schemas ---
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

# ===================================================================
# === 3. ENDPOINTS DE LA API con Prints de Debugging
# ===================================================================

@app.get("/productos", response_model=List[Dict[str, Any]], dependencies=[Depends(get_api_key)], tags=["Simulación"])
def mostrar_productos_de_sheet():
    """Lee todos los datos de la pestaña 'STOCK' y los devuelve."""
    print("\n--- [DEBUG] Endpoint /productos ALCANZADO ---")
    try:
        print("--- [DEBUG] Intentando obtener hoja 'STOCK'...")
        hoja_stock = _obtener_hoja("STOCK")
        print("--- [DEBUG] Hoja 'STOCK' obtenida. Leyendo todos los registros...")
        productos = hoja_stock.get_all_records()
        print(f"--- [DEBUG] ✅ Éxito. Se obtuvieron {len(productos)} registros de la hoja. Enviando respuesta...")
        return productos
    except Exception as e:
        print(f"--- [DEBUG] ❌ ERROR en endpoint /productos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ocurrió un error al leer la hoja 'STOCK': {str(e)}")


@app.post("/registrar-movimiento", dependencies=[Depends(get_api_key)], tags=["Simulación"])
def registrar_movimiento_y_actualizar_stock(venta_data: VentaCreate):
    """Recibe una venta, la registra y actualiza el stock en Google Sheets."""
    print("\n--- [DEBUG] Endpoint /registrar-movimiento ALCANZADO ---")
    print(f"--- [DEBUG] Datos recibidos: {venta_data.model_dump_json()}")
    try:
        # (La lógica interna ya está bien, no añadimos más prints para no saturar)
        hoja_movimientos = _obtener_hoja("MOVIMIENTOS")
        hoja_stock = _obtener_hoja("STOCK")
        
        productos_en_stock = hoja_stock.get_all_records()
        stock_dict = {prod["id producto"]: prod for prod in productos_en_stock}

        filas_para_movimientos, actualizaciones_stock = [], []
        
        for item in venta_data.items:
            producto = stock_dict.get(item.id_producto)
            if not producto:
                raise HTTPException(status_code=404, detail=f"Producto con ID {item.id_producto} no encontrado.")
            
            stock_actual = float(producto["cantidad"])
            if stock_actual < item.cantidad:
                raise HTTPException(status_code=400, detail=f"Stock insuficiente para '{producto['nombre']}'.")
            
            monto = item.cantidad * float(str(producto["precio"]).replace("$","").replace(".","").replace(",","."))
            filas_para_movimientos.append(["", "", "", "", "", "", datetime.now().strftime('%Y-%m-%d'), "Cliente Simulado", "", "", "VENTA", "", producto["Descripción"], monto, "", "API Sim."])
            
            nuevo_stock = stock_actual - item.cantidad
            fila_a_actualizar = productos_en_stock.index(producto) + 2
            actualizaciones_stock.append({ 'range': f'G{fila_a_actualizar}', 'values': [[nuevo_stock]] })

        if filas_para_movimientos:
            hoja_movimientos.append_rows(filas_para_movimientos, value_input_option='USER_ENTERED')
        if actualizaciones_stock:
            hoja_stock.batch_update(actualizaciones_stock)

        print("--- [DEBUG] ✅ Éxito. Venta registrada y stock actualizado en Sheets.")
        return {"status": "success", "message": "Movimiento registrado y stock actualizado en Google Sheets."}

    except Exception as e:
        print(f"--- [DEBUG] ❌ ERROR en endpoint /registrar-movimiento: {str(e)}")
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=f"Ocurrió un error en la simulación: {str(e)}")