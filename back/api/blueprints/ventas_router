# back/api/blueprints/ventas_router.py

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from back.database import get_db
# Importamos la lógica desde su nueva ubicación
from back.gestion.ventas import manager as ventas_manager
from back.schemas.boleta_schemas import BoletaResponse
# Seguridad desactivada temporalmente, como acordamos
# from back.security import obtener_usuario_actual

router = APIRouter(
    prefix="/ventas",
    tags=["Ventas y Boletas"]
)

@router.get("/{id_venta}/boleta", response_model=BoletaResponse)
def api_obtener_boleta(id_venta: int, db: Session = Depends(get_db)):
    """
    Devuelve un objeto JSON con la información para un Comprobante de Venta (no fiscal).
    """
    try:
        boleta_data = ventas_manager.obtener_datos_boleta(db, id_venta)
        return boleta_data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")