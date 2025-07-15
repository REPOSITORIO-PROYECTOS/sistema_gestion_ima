# /home/sgi_user/proyectos/sistema_gestion_ima/back/api/blueprints/actualizacion_masiva_router.py

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import Dict

from back.database import get_db
# Importamos la lógica que acabamos de crear
from back.gestion.actualizaciones import actualizaciones_masivas as mod_sync 
# Podrías necesitar un esquema de respuesta, pero por ahora un Dict servirá
# from back.schemas import RespuestaGenerica 

router = APIRouter(
    prefix="/sincronizar",
    tags=["Sincronización Masiva"]
)

@router.post("/clientes", response_model=Dict)
def api_sincronizar_clientes(db: Session = Depends(get_db)):
    """
    Ejecuta una sincronización completa de los clientes desde Google Sheets a la base de datos.
    Compara por CUIT/CUIL para crear nuevos clientes o actualizar existentes.
    """
    try:
        resultado = mod_sync.sincronizar_clientes_desde_sheets(db)
        if "error" in resultado:
            raise HTTPException(status_code=500, detail=resultado["error"])
        return {"status": "success", "message": "Sincronización de clientes completada.", "data": resultado}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ocurrió un error inesperado: {e}")


@router.post("/articulos", response_model=Dict)
def api_sincronizar_articulos(db: Session = Depends(get_db)):
    """
    Ejecuta una sincronización completa de los artículos desde Google Sheets a la base de datos.
    Compara por código de barras para crear nuevos artículos o actualizar existentes.
    """
    try:
        resultado = mod_sync.sincronizar_articulos_desde_sheets(db)
        if "error" in resultado:
            raise HTTPException(status_code=500, detail=resultado["error"])
        return {"status": "success", "message": "Sincronización de artículos completada.", "data": resultado}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ocurrió un error inesperado: {e}")