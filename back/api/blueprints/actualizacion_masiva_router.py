# /home/sgi_user/proyectos/sistema_gestion_ima/back/api/blueprints/actualizacion_masiva_router.py

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import Dict

from back.database import get_db
from back.gestion.sincronizacion_orquestador import sincronizar_empresa_unificada
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
        resultado = sincronizar_empresa_unificada(
            db=db,
            id_empresa=id_empresa,
            incluir_articulos=False,
            incluir_clientes=True,
            incluir_proveedores=False,
            detener_en_error=True,
        )
        if resultado.get("status") == "busy":
            raise HTTPException(status_code=409, detail=resultado.get("message", "Sincronización en curso"))
        if resultado.get("status") == "error":
            detalle = resultado.get("pasos", {}).get("clientes", {}).get("error", "Error inesperado")
            raise HTTPException(status_code=500, detail=detalle)

        return {
            "status": "success",
            "message": "Sincronización de clientes completada.",
            "data": resultado,
        }
    except HTTPException:
        raise
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
        resultado = sincronizar_empresa_unificada(
            db=db,
            id_empresa=id_empresa,
            incluir_articulos=True,
            incluir_clientes=False,
            incluir_proveedores=False,
            detener_en_error=True,
        )
        if resultado.get("status") == "busy":
            raise HTTPException(status_code=409, detail=resultado.get("message", "Sincronización en curso"))
        if resultado.get("status") == "error":
            detalle = resultado.get("pasos", {}).get("articulos", {}).get("error", "Error inesperado")
            raise HTTPException(status_code=500, detail=detalle)

        data_articulos = resultado.get("pasos", {}).get("articulos", {}).get("resultado", {})
        total_leidos = data_articulos.get("leidos_de_sheet", 0)
        total_actualizados = data_articulos.get("actualizados_en_db", 0)
        total_creados = data_articulos.get("creados_en_db", 0)
        total_errores = data_articulos.get("filas_con_error", 0)
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en sincronización: {str(e)}")


@router.post("/proveedores", response_model=Dict)
def api_sincronizar_proveedores(db: Session = Depends(get_db),current_user: Usuario = Depends(obtener_usuario_actual)):
    """
    Ejecuta una sincronización completa de los proveedores desde Google Sheets a la base de datos.
    """
    try:
        id_empresa = current_user.id_empresa
        resultado = sincronizar_empresa_unificada(
            db=db,
            id_empresa=id_empresa,
            incluir_articulos=False,
            incluir_clientes=False,
            incluir_proveedores=True,
            detener_en_error=True,
        )
        if resultado.get("status") == "busy":
            raise HTTPException(status_code=409, detail=resultado.get("message", "Sincronización en curso"))
        if resultado.get("status") == "error":
            detalle = resultado.get("pasos", {}).get("proveedores", {}).get("error", "Error inesperado")
            raise HTTPException(status_code=500, detail=detalle)

        return {
            "status": "success",
            "message": "Sincronización de proveedores completada.",
            "data": resultado,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ocurrió un error inesperado: {e}")


@router.post("/todo", response_model=Dict)
def api_sincronizar_todo(db: Session = Depends(get_db), current_user: Usuario = Depends(obtener_usuario_actual)):
    """
    Ejecuta sincronización completa de la empresa: artículos, clientes y proveedores.
    Devuelve estado "partial" si al menos un paso falló pero otros pudieron completarse.
    """
    try:
        id_empresa = current_user.id_empresa
        resultado = sincronizar_empresa_unificada(
            db=db,
            id_empresa=id_empresa,
            incluir_articulos=True,
            incluir_clientes=True,
            incluir_proveedores=True,
            detener_en_error=False,
        )

        if resultado.get("status") == "busy":
            raise HTTPException(status_code=409, detail=resultado.get("message", "Sincronización en curso"))

        if resultado.get("status") == "error":
            raise HTTPException(status_code=500, detail=resultado.get("message", "Error en sincronización"))

        return {
            "status": resultado.get("status", "success"),
            "message": resultado.get("message", "Sincronización completada."),
            "data": resultado,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en sincronización completa: {str(e)}")