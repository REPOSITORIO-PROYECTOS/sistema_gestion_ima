# back/api/caja_router.py

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional

# --- Importaciones de Lógica de Negocio ---
from back.gestion.caja import apertura_cierre as mod_apertura_cierre
from back.gestion.caja import registro_caja as mod_registro_caja
from back.security import es_cajero # Importamos nuestro guardián
from back.gestion.stock import articulos as mod_articulos

# --- Importaciones de Modelos Pydantic (los moveremos a su propio archivo después) ---
# Por ahora, los definimos aquí para que funcione.
from pydantic import BaseModel, Field
from typing import Dict, Any

router = APIRouter(
    prefix="/caja",
    tags=["Caja"],
    dependencies=[Depends(es_cajero)] # ¡TODA la sección de caja está protegida!
)

# --- Modelos Pydantic para Request/Response (esto idealmente iría en un archivo 'schemas.py') ---
class RespuestaGenerica(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None

class AbrirCajaRequest(BaseModel):
    saldo_inicial: float = Field(..., gt=-0.00001)
    usuario: str

class SesionInfo(BaseModel):
    id_sesion: int
    usuario_apertura: Optional[str] = None
    fecha_apertura: Optional[str] = None
    saldo_inicial: Optional[float] = None

class EstadoCajaResponse(BaseModel):
    status: str
    caja_abierta: bool
    sesion_info: Optional[SesionInfo] = None
    message: Optional[str] = None

class ArticuloVendido(BaseModel):
    id_articulo: str
    nombre: Optional[str] = None
    cantidad: int = Field(..., gt=0)
    precio_unitario: float = Field(..., ge=0)
    subtotal: float

class RegistrarVentaRequest(BaseModel):
    id_sesion_caja: int
    articulos_vendidos: List[ArticuloVendido]
    metodo_pago: str
    usuario: str
    total_venta: float

class MovimientoCajaRequest(BaseModel):
    id_sesion_caja: int
    concepto: str # Renombrado de 'descripcion' para coincidir con el backend
    monto: float = Field(..., gt=0)
    usuario: str

class CerrarCajaRequest(BaseModel):
    id_sesion: int
    saldo_final_contado: float = Field(..., ge=0)
    usuario_cierre: str
    # token_admin: str # El token se manejará por dependencia, no en el cuerpo

# --- Creación del Router ---
router = APIRouter(
    prefix="/caja",
    tags=["Caja"],
    responses={404: {"description": "No encontrado"}}
)

# --- Endpoints de Caja ---

@router.get("/estado", response_model=EstadoCajaResponse)
async def api_obtener_estado_caja():
    """Verifica si hay una caja abierta y devuelve su información."""
    try:
        sesion_data = mod_apertura_cierre.obtener_estado_caja_actual()
        if sesion_data:
            return EstadoCajaResponse(status="success", caja_abierta=True, sesion_info=SesionInfo(**sesion_data))
        else:
            return EstadoCajaResponse(status="success", caja_abierta=False, message="No hay ninguna caja abierta actualmente.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@router.post("/abrir")
async def api_abrir_caja(request_data: AbrirCajaRequest, current_user: dict = Depends(es_cajero)):
    # Ya no necesitamos pasar el usuario en el request_data, lo obtenemos del token
    resultado = mod_apertura_cierre.abrir_caja(
        saldo_inicial=request_data.saldo_inicial,
        usuario=current_user['username'] # Usamos el usuario autenticado
    )
    if resultado.get("status") == "success":
        return RespuestaGenerica(status="success", message=resultado.get("message"), data={"id_sesion": resultado.get("id_sesion")})
    else:
        raise HTTPException(status_code=400, detail=resultado.get("message", "Error al abrir caja."))

@router.post("/ventas/registrar", response_model=RespuestaGenerica)
async def api_registrar_venta(request_data: RegistrarVentaRequest):
    """Registra una nueva venta en la sesión de caja activa."""
    articulos_dict_list = [dict(art) for art in request_data.articulos_vendidos]
    
    resultado = mod_registro_caja.registrar_venta(
        id_sesion_caja=request_data.id_sesion_caja,
        articulos_vendidos=articulos_dict_list,
        metodo_pago=request_data.metodo_pago.upper(),
        usuario=request_data.usuario,
        total_venta=request_data.total_venta
    )
    if resultado.get("status") == "success":
        return RespuestaGenerica(status="success", message=resultado.get("message"), data={"id_movimiento": resultado.get("id_movimiento")})
    else:
        raise HTTPException(status_code=400, detail=resultado.get("message", "Error al registrar venta."))

@router.post("/ingresos/registrar", response_model=RespuestaGenerica)
async def api_registrar_ingreso(request_data: MovimientoCajaRequest):
    """Registra un ingreso de efectivo en la caja."""
    resultado = mod_registro_caja.registrar_ingreso_egreso(
        id_sesion_caja=request_data.id_sesion_caja,
        concepto=request_data.concepto,
        monto=request_data.monto,
        tipo="INGRESO",
        usuario=request_data.usuario
    )
    if resultado.get("status") == "success":
        return RespuestaGenerica(status="success", message=resultado.get("message"), data={"id_movimiento": resultado.get("id_movimiento")})
    else:
        raise HTTPException(status_code=400, detail=resultado.get("message", "Error al registrar ingreso."))

@router.post("/egresos/registrar", response_model=RespuestaGenerica)
async def api_registrar_egreso(request_data: MovimientoCajaRequest):
    """Registra un egreso de efectivo de la caja."""
    resultado = mod_registro_caja.registrar_ingreso_egreso(
        id_sesion_caja=request_data.id_sesion_caja,
        concepto=request_data.concepto,
        monto=request_data.monto,
        tipo="EGRESO",
        usuario=request_data.usuario
    )
    if resultado.get("status") == "success":
        return RespuestaGenerica(status="success", message=resultado.get("message"), data={"id_movimiento": resultado.get("id_movimiento")})
    else:
        raise HTTPException(status_code=400, detail=resultado.get("message", "Error al registrar egreso."))

@router.get("/articulos/{id_articulo}")
async def api_obtener_articulo(id_articulo: str):
    """
    Endpoint para obtener la información de un artículo por su ID.
    """
    articulo_data = mod_articulos.obtener_articulo_por_id(id_articulo)
    if not articulo_data:
        raise HTTPException(status_code=404, detail=f"Artículo con ID {id_articulo} no encontrado.")
    return articulo_data