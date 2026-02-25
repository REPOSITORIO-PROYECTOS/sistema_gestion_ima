# /home/sgi_user/proyectos/sistema_gestion_ima/back/api/blueprints/actualizacion_masiva_router.py

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import Dict

from back.database import get_db
# Importamos la lógica mejorada de sincronización
from back.gestion.sincronizacion_manager import sincronizar_articulos_desde_sheet
from back.gestion.actualizaciones import actualizaciones_masivas as mod_sync
from back.modelos import Usuario
from back.security import obtener_usuario_actual

router = APIRouter(
    prefix="/sincronizar",
    tags=["Sincronización Masiva"]
)

@router.post("/clientes", response_model=Dict)
def api_sincronizar_clientes(db: Session = Depends(get_db),current_user: Usuario = Depends(obtener_usuario_actual)):
    """
    Ejecuta una sincronización completa de los clientes desde Google Sheets a la base de datos.
    Compara por CUIT/CUIL para crear nuevos clientes o actualizar existentes.
    """
    try:
        id_empresa = current_user.id_empresa
        resultado = mod_sync.sincronizar_clientes_desde_sheets(db,id_empresa)
        if "error" in resultado:
            raise HTTPException(status_code=500, detail=resultado["error"])
        return {"status": "success", "message": "Sincronización de clientes completada.", "data": resultado}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ocurrió un error inesperado: {e}")


@router.post("/articulos", response_model=Dict)
def api_sincronizar_articulos(db: Session = Depends(get_db),current_user: Usuario = Depends(obtener_usuario_actual)):
    """
    Ejecuta una sincronización completa de los artículos desde Google Sheets a la base de datos.
    Sincroniza artículos, precios, stock y códigos de barra automáticamente.
    """
    try:
        id_empresa = current_user.id_empresa
        resultado = sincronizar_articulos_desde_sheet(db, id_empresa)
        if resultado.get("error"):
            raise HTTPException(status_code=500, detail=resultado.get("error"))

        total_leidos = resultado.get("leidos_de_sheet", 0)
        total_actualizados = resultado.get("actualizados_en_db", 0)
        total_creados = resultado.get("creados_en_db", 0)
        total_errores = resultado.get("filas_con_error", 0)
        mensaje_resumen = (
            f"✅ Sincronización completada. "
            f"Leídos: {total_leidos}, "
            f"Actualizados: {total_actualizados}, "
            f"Creados: {total_creados}"
            f"{f', Errores: {total_errores}' if total_errores > 0 else ''}."
        )

        return {
            "status": "success",
            "message": mensaje_resumen,
            "data": resultado
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en sincronización: {str(e)}")


@router.post("/proveedores", response_model=Dict)
def api_sincronizar_proveedores(db: Session = Depends(get_db),current_user: Usuario = Depends(obtener_usuario_actual)):
    """
    Ejecuta una sincronización completa de los proveedores desde Google Sheets a la base de datos.
    """
    try:
        id_empresa = current_user.id_empresa
        resultado = mod_sync.sincronizar_proveedores_desde_sheets(db,id_empresa)
        if "error" in resultado:
            raise HTTPException(status_code=500, detail=resultado["error"])
        return {"status": "success", "message": "Sincronización de proveedores completada.", "data": resultado}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ocurrió un error inesperado: {e}")
        resultado = mod_sync.sincronizar_proveedores_desde_sheets(db,id_empresa)
        if "error" in resultado:
            raise HTTPException(status_code=500, detail=resultado["error"])
        return {"status": "success", "message": "Sincronización de proveedores completada.", "data": resultado}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ocurrió un error inesperado: {e}")