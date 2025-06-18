# back/main.py
from fastapi import FastAPI, HTTPException, Body, Depends, Header
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field # Para validación de datos
import sys # Para la verificación inicial
from fastapi.middleware.cors import CORSMiddleware
# --- Importaciones de Módulos del Backend ---
# (Asegúrate de que estas importaciones funcionen correctamente después de arreglar los ImportErrors en config.py y otros módulos)
try:
    from back.gestion.caja import apertura_cierre as mod_apertura_cierre
    from back.gestion.caja import registro_caja as mod_registro_caja
    from back.gestion.caja import cliente_publico as mod_cliente_publico
    from back.gestion import auth as mod_auth
    from back.config import GOOGLE_SHEET_ID, SHEET_NAME_CONFIG_HORARIOS # y otras que necesites directamente
    from back.utils.sheets_google_handler import GoogleSheetsHandler
    # from .gestion import fiscal # Descomenta cuando esté listo y lo uses
except ImportError as e:
    print(f"ERROR CRÍTICO AL IMPORTAR MÓDULOS DEL BACKEND EN main.py: {e}")
    print("La API podría no funcionar correctamente. Por favor, arregla los ImportErrors.")
    # Considera lanzar el error para detener la app si las importaciones son esenciales para el arranque
    # raise e

# --- Inicialización de FastAPI ---
app = FastAPI(
    title="API Sistema de Gestión IMA",
    description="API para interactuar con el backend del sistema de gestión.",
    version="0.2.0" # Incrementada versión
)

origins = [
    "http://localhost", # Si el frontend corre en el mismo server pero diferente puerto
    "http://localhost:3000", # Ejemplo para React/Vue/Angular en desarrollo
    "https://swingjugos.netlify.app/", # Tu frontend en producción
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Verificación Inicial (similar al if __name__ == "__main__" de tu CLI) ---
# Esto se ejecutará una vez cuando la aplicación FastAPI se inicie.
try:
    if not GOOGLE_SHEET_ID:
        raise ValueError("Error Crítico: GOOGLE_SHEET_ID no está configurado.")
    print("Verificando conexión inicial a Google Sheets para la API...")
    g_handler_test = GoogleSheetsHandler()
    if not g_handler_test.client:
        raise ConnectionError("Fallo en la conexión inicial a Google Sheets para la API.")
    print("Conexión a Google Sheets para la API verificada.")
    # Generar token de admin al inicio si no existe, para pruebas de admin
    mod_auth.generar_y_guardar_admin_token()
except Exception as e_init:
    print(f"Error fatal durante la inicialización de la API: {e_init}")
    # En un entorno de producción, podrías querer que la app no inicie si falla esta verificación.
    # Por ahora, solo imprimimos el error.
    # sys.exit(1) # Descomentar para salir si la inicialización falla


# --- Modelos Pydantic para Request/Response (Validación de Datos) ---
class RespuestaGenerica(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None

class AbrirCajaRequest(BaseModel):
    saldo_inicial: float = Field(..., gt=-0.00001) # gt=0 para asegurar que no sea negativo
    usuario: str

class AbrirCajaResponseData(BaseModel):
    id_sesion: int

class SesionInfo(BaseModel):
    ID_Sesion: Any # Puede ser int o str dependiendo de cómo se guarde/lea
    UsuarioApertura: Optional[str] = None
    FechaApertura: Optional[str] = None
    HoraApertura: Optional[str] = None
    SaldoInicial: Optional[float] = None
    # Añade más campos si los devuelve obtener_estado_caja_actual

class EstadoCajaResponse(BaseModel):
    status: str
    caja_abierta: bool
    sesion_info: Optional[SesionInfo] = None
    message: Optional[str] = None

class ArticuloVendido(BaseModel):
    id_articulo: str
    nombre: str
    cantidad: int = Field(..., gt=0)
    precio_unitario: float = Field(..., ge=0)
    subtotal: float

class RegistrarVentaRequest(BaseModel):
    id_sesion_caja: int
    articulos_vendidos: List[ArticuloVendido]
    cliente: Optional[str] = "Público General" # Asumir default si no se provee
    metodo_pago: str
    usuario: str
    total_venta: float # El frontend debería calcularlo y enviarlo
    # monto_recibido: Optional[float] = None # Para cálculo de vuelto si se hace en backend

class RegistrarVentaResponseData(BaseModel):
    id_registro_base: Any # Puede ser str o int

class MovimientoCajaRequest(BaseModel):
    id_sesion_caja: int
    # tipo_movimiento: str # Se define en la ruta del endpoint
    descripcion: str
    monto: float = Field(..., gt=0)
    usuario: str

class MovimientoCajaResponseData(BaseModel):
    id_registro: Any

class CerrarCajaRequest(BaseModel):
    id_sesion: int
    saldo_final_contado: float = Field(..., ge=0)
    usuario_cierre: str
    token_admin: str # El token de admin se envía en el cuerpo

class CerrarCajaResponseData(BaseModel):
    id_sesion: int
    diferencia: float

# --- Dependencia para Verificar Token de Administrador ---
async def verificar_token_admin_dependencia(x_admin_token: Optional[str] = Header(None)):
    """
    Dependencia para verificar el token de admin pasado en la cabecera X-Admin-Token.
    Si se pasa en el cuerpo de la request (ej. CerrarCajaRequest), esa verificación se hará en el endpoint.
    Esta dependencia es para proteger endpoints enteros.
    """
    if not x_admin_token:
        raise HTTPException(status_code=401, detail="Cabecera X-Admin-Token requerida para esta operación.")
    if not mod_auth.verificar_admin_token(x_admin_token):
        raise HTTPException(status_code=403, detail="Token de Administrador inválido o expirado.")
    return True # Token válido

# --- Endpoints de la API para Caja ---

@app.get("/", tags=["General"])
async def read_root():
    return {"message": "Bienvenido a la API del Sistema de Gestión IMA. El backend está ejecutándose."}

@app.get("/caja/estado", response_model=EstadoCajaResponse, tags=["Caja"])
async def api_obtener_estado_caja():
    """Verifica si hay una caja abierta y devuelve su información."""
    try:
        sesion_data = mod_apertura_cierre.obtener_estado_caja_actual()
        if sesion_data:
            # Convertir ID_Sesion a int si es necesario y está presente
            if 'ID_Sesion' in sesion_data and sesion_data['ID_Sesion'] is not None:
                try:
                    sesion_data['ID_Sesion'] = int(sesion_data['ID_Sesion'])
                except ValueError:
                    # Manejar caso donde ID_Sesion no es un int válido, o dejarlo como está
                    pass 
            return EstadoCajaResponse(status="success", caja_abierta=True, sesion_info=SesionInfo(**sesion_data))
        else:
            return EstadoCajaResponse(status="success", caja_abierta=False, message="No hay ninguna caja abierta actualmente.")
    except Exception as e:
        print(f"Error en api_obtener_estado_caja: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@app.post("/caja/abrir", response_model=RespuestaGenerica, tags=["Caja"])
async def api_abrir_caja(request_data: AbrirCajaRequest):
    """Abre una nueva sesión de caja."""
    try:
        # Aquí podrías añadir lógica para validar si el usuario tiene permiso para abrir caja,
        # o si está dentro de horarios permitidos (usando SHEET_NAME_CONFIG_HORARIOS).
        resultado = mod_apertura_cierre.abrir_caja(
            saldo_inicial=request_data.saldo_inicial,
            usuario=request_data.usuario
        )
        if resultado.get("status") == "success":
            return RespuestaGenerica(status="success", message=resultado.get("message"), data={"id_sesion": resultado.get("id_sesion")})
        else:
            raise HTTPException(status_code=400, detail=resultado.get("message", "Error al abrir caja."))
    except Exception as e:
        print(f"Error en api_abrir_caja: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@app.post("/caja/ventas/registrar", response_model=RespuestaGenerica, tags=["Caja - Ventas"])
async def api_registrar_venta(request_data: RegistrarVentaRequest):
    """Registra una nueva venta en la sesión de caja activa."""
    try:
        # Convertir lista de ArticuloVendido (Pydantic) a lista de dicts si la función backend espera dicts
        articulos_dict_list = [dict(art) for art in request_data.articulos_vendidos]

        # Validar si la sesión de caja está abierta (podría hacerse como dependencia o aquí)
        sesion_activa = mod_apertura_cierre.obtener_estado_caja_actual()
        if not sesion_activa or int(sesion_activa.get("ID_Sesion")) != request_data.id_sesion_caja:
             raise HTTPException(status_code=400, detail=f"La sesión de caja {request_data.id_sesion_caja} no está activa o no coincide.")

        # Obtener nombre del cliente (tu CLI lo hacía así)
        nombre_cliente = mod_cliente_publico.obtener_cliente_para_venta(request_data.cliente if request_data.cliente else None)

        resultado = mod_registro_caja.registrar_venta(
            id_sesion_caja=request_data.id_sesion_caja,
            articulos_vendidos=articulos_dict_list,
            cliente=nombre_cliente,
            metodo_pago=request_data.metodo_pago.upper(),
            usuario=request_data.usuario,
            total_venta=request_data.total_venta
        )
        # Cálculo de vuelto (si el frontend no lo hace)
        # vuelto = mod_registro_caja.calcular_vuelto(request_data.total_venta, request_data.monto_recibido, request_data.metodo_pago)

        if resultado.get("status") == "success":
            return RespuestaGenerica(status="success", message=resultado.get("message"), data={"id_registro_base": resultado.get("id_registro_base")}) #, "vuelto": vuelto
        else:
            raise HTTPException(status_code=400, detail=resultado.get("message", "Error al registrar venta."))
    except Exception as e:
        print(f"Error en api_registrar_venta: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@app.post("/caja/ingresos/registrar", response_model=RespuestaGenerica, tags=["Caja - Movimientos"])
async def api_registrar_ingreso(request_data: MovimientoCajaRequest):
    """Registra un ingreso de efectivo en la caja."""
    try:
        # Asumiendo que tu mod_registro_caja.registrar_movimiento ahora es más específico o tienes una función dedicada
        # Si registrar_movimiento ya no existe, usa registrar_ingreso_efectivo
        if hasattr(mod_registro_caja, 'registrar_ingreso_efectivo'):
            resultado = mod_registro_caja.registrar_ingreso_efectivo(
                id_sesion_caja=request_data.id_sesion_caja,
                concepto=request_data.descripcion,
                monto=request_data.monto,
                usuario=request_data.usuario
            )
        elif hasattr(mod_registro_caja, 'registrar_movimiento'): # Fallback si aún tienes registrar_movimiento genérico
             resultado = mod_registro_caja.registrar_movimiento(
                id_sesion_caja=request_data.id_sesion_caja,
                tipo_movimiento="INGRESO",
                descripcion=request_data.descripcion,
                monto=request_data.monto,
                usuario=request_data.usuario
            )
        else:
            raise HTTPException(status_code=501, detail="Función de registro de ingreso no implementada en el backend.")

        if resultado.get("status") == "success":
            return RespuestaGenerica(status="success", message=resultado.get("message"), data={"id_registro": resultado.get("id_registro")})
        else:
            raise HTTPException(status_code=400, detail=resultado.get("message", "Error al registrar ingreso."))
    except Exception as e:
        print(f"Error en api_registrar_ingreso: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@app.post("/caja/egresos/registrar", response_model=RespuestaGenerica, tags=["Caja - Movimientos"])
async def api_registrar_egreso(request_data: MovimientoCajaRequest):
    """Registra un egreso de efectivo de la caja."""
    try:
        # Similar al ingreso, usa la función específica si existe
        if hasattr(mod_registro_caja, 'registrar_egreso_efectivo'):
            resultado = mod_registro_caja.registrar_egreso_efectivo(
                id_sesion_caja=request_data.id_sesion_caja,
                concepto=request_data.descripcion,
                monto=request_data.monto,
                usuario=request_data.usuario
            )
        elif hasattr(mod_registro_caja, 'registrar_movimiento'): # Fallback
            resultado = mod_registro_caja.registrar_movimiento(
                id_sesion_caja=request_data.id_sesion_caja,
                tipo_movimiento="EGRESO",
                descripcion=request_data.descripcion,
                monto=request_data.monto,
                usuario=request_data.usuario
            )
        else:
            raise HTTPException(status_code=501, detail="Función de registro de egreso no implementada en el backend.")

        if resultado.get("status") == "success":
            return RespuestaGenerica(status="success", message=resultado.get("message"), data={"id_registro": resultado.get("id_registro")})
        else:
            raise HTTPException(status_code=400, detail=resultado.get("message", "Error al registrar egreso."))
    except Exception as e:
        print(f"Error en api_registrar_egreso: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@app.post("/caja/cerrar", response_model=RespuestaGenerica, tags=["Caja"])
async def api_cerrar_caja(request_data: CerrarCajaRequest):
    """Cierra la sesión de caja activa. Requiere token de administrador en el cuerpo."""
    try:
        # Verificar token de admin enviado en el cuerpo de la request
        if not mod_auth.verificar_admin_token(request_data.token_admin):
            raise HTTPException(status_code=403, detail="Token de Administrador inválido o expirado.")

        resultado = mod_apertura_cierre.cerrar_caja(
            id_sesion=request_data.id_sesion,
            saldo_final_contado=request_data.saldo_final_contado,
            usuario_cierre=request_data.usuario_cierre
        )
        if resultado.get("status") == "success":
            return RespuestaGenerica(status="success", message=resultado.get("message"), data={"id_sesion": resultado.get("id_sesion"), "diferencia": resultado.get("diferencia")})
        else:
            # Los errores específicos (ej: "ya cerrada", "no encontrada") deberían venir en el message
            raise HTTPException(status_code=400, detail=resultado.get("message", "Error al cerrar caja."))
    except Exception as e:
        print(f"Error en api_cerrar_caja: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


# --- Endpoints de Administración (Protegidos) ---
# Ejemplo de cómo proteger un endpoint con una dependencia
@app.post("/admin/nuevo-token", response_model=RespuestaGenerica, tags=["Administración"], dependencies=[Depends(verificar_token_admin_dependencia)])
async def api_generar_nuevo_token_admin(usuario_solicitante: str = Body(..., embed=True)):
    """Genera un nuevo token de administrador. Requiere un token de admin válido en la cabecera X-Admin-Token."""
    try:
        # El usuario_solicitante podría ser el usuario admin que está pidiendo generar el token
        # para un nuevo periodo o para otro admin (si tuvieras esa lógica).
        # Por ahora, simplemente lo usamos para el registro.
        nuevo_token = mod_auth.generar_y_guardar_admin_token(usuario_generador=usuario_solicitante, forzar_nuevo=True)
        return RespuestaGenerica(status="success", message=f"Nuevo token de admin generado para {usuario_solicitante}.", data={"nuevo_token": nuevo_token})
    except Exception as e:
        print(f"Error en api_generar_nuevo_token_admin: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


# --- Endpoints para Configuración de Horarios (Ejemplo) ---
# (La lógica de tu CLI para esto era un placeholder, necesitarías definirla mejor)
class HorarioConfigRequest(BaseModel):
    dia: str
    tipo_operacion: str # "Apertura" o "Cierre"
    hora: str # Formato HH:MM
    activado: bool

@app.post("/admin/config/horarios", tags=["Administración - Configuración"], dependencies=[Depends(verificar_token_admin_dependencia)])
async def api_configurar_horario_caja(config_data: HorarioConfigRequest):
    """Configura un horario de apertura/cierre automático (Placeholder). Requiere token de admin."""
    # Aquí iría la lógica para guardar en SHEET_NAME_CONFIG_HORARIOS
    # similar a tu menu_configurar_horarios_caja pero adaptado para API.
    # Por ahora, es un placeholder.
    print(f"Recibido para configurar horario: {config_data}")
    # g_handler = GoogleSheetsHandler()
    # ws_config = g_handler.get_worksheet(SHEET_NAME_CONFIG_HORARIOS)
    # ... (validaciones y lógica de guardado) ...
    return {"status": "info", "message": "Funcionalidad de configuración de horarios en desarrollo.", "data_recibida": dict(config_data)}


# --- CORS (Cross-Origin Resource Sharing) ---
# Descomenta y ajusta si tu frontend se sirve desde un dominio diferente
# from fastapi.middleware.cors import CORSMiddleware
# origins = [
#    "http://localhost", # Si el frontend corre en el mismo server pero diferente puerto
#    "http://localhost:3000", # Ejemplo para React/Vue/Angular en desarrollo
#    "https://tu-dominio-frontend.com", # Tu frontend en producción
# ]
# app.add_middleware(
#    CORSMiddleware,
#    allow_origins=origins,
#    allow_credentials=True,
#    allow_methods=["*"],
#    allow_headers=["*"],
# )

# Para ejecutar esta API (desde la raíz del proyecto sistema_gestion_ima/):
# Con venv activado:  uvicorn back.main:app --host 0.0.0.0 --port 8000 --reload