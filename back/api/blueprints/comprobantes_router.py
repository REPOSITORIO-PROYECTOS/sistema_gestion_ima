# back/api/blueprints/comprobantes_router.py
# VERSIÓN FINAL, LIMPIA Y COMPLETA

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from starlette.responses import Response
from sqlmodel import Session # <-- 1. IMPORTACIÓN AÑADIDA

# --- Módulos del Proyecto (Limpios y Ordenados) ---
# Dependencias de FastAPI y Seguridad
from back.database import get_db
from back.security import obtener_usuario_actual
from back.modelos import Usuario # <-- 2. IMPORTACIÓN AÑADIDA

# Especialistas de la capa de Gestión
from back.gestion.reportes.generador_comprobantes import generar_comprobante_stateless
from back.gestion import facturacion_lotes_manager # <-- Importamos el módulo completo
from back.schemas.venta_ciclo_de_vida_schemas import VentaResponse # Reutilizamos el schema de respuesta
from back.gestion.reportes.ciclo_vida_comp import agrupar_comprobantes_en_uno_nuevo

# Schemas necesarios para este router
from back.schemas.comprobante_schemas import (
    GenerarComprobanteRequest,
    FacturarLoteRequest,
    FacturarLoteResponse
)

# --- Schema para el Payload de Entrada ---
class AgruparRequest(BaseModel):
    ids_comprobantes: List[int]
    nuevo_tipo_comprobante: str # Ej: "Factura A"

router = APIRouter(
    prefix="/comprobantes",
    tags=["Generación de Comprobantes"],
    # dependencies=[Depends(obtener_usuario_actual)] # Puedes proteger todo el router si quieres
)

@router.post("/generar", summary="Generar un comprobante (factura, remito, etc.) on-demand",
    responses={
        200: {"content": {"application/pdf": {}}, "description": "El archivo PDF del comprobante."},
        404: {"description": "Plantilla no encontrada."},
        503: {"description": "Servicio de AFIP no disponible."}
    }
)
def api_generar_comprobante(req: GenerarComprobanteRequest):
    """
    Recibe todos los datos necesarios en el cuerpo de la petición y genera
    un comprobante en PDF (factura, remito, presupuesto o recibo).
    """
    try:
        pdf_bytes = generar_comprobante_stateless(req)
        
        # Generamos un nombre de archivo más robusto
        filename = f"{req.tipo}_{req.emisor.punto_venta}_{req.receptor.cuit_o_dni or 'consumidor'}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'}
        )
    except ValueError as e:
        # Errores de negocio (ej. plantilla no existe)
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException as e:
        # Re-lanzamos excepciones HTTP que vienen de capas inferiores (ej. 503 de AFIP)
        raise e
    except Exception as e:
        # Capturamos cualquier otro error inesperado
        print(f"ERROR INESPERADO al generar comprobante: {e}")
        raise HTTPException(status_code=500, detail="Error interno al generar el comprobante.")
    

@router.post("/facturar-lote", summary="Factura un lote de ventas no facturadas a un único cliente",
response_model=FacturarLoteResponse)
def api_facturar_lote_de_ventas(
    req: FacturarLoteRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    """
    Recibe una lista de IDs de movimientos de venta, los consolida,
    genera una única factura en AFIP y actualiza todas las ventas en la DB.
    Devuelve un JSON con el resultado, no un PDF.
    """
    try:
        # Llamamos a la función a través de su módulo, manteniendo el código limpio
        resultado_factura = facturacion_lotes_manager.facturar_lote_de_ventas(
            db=db,
            usuario_actual=current_user,
            ids_movimientos=req.ids_movimientos,
            id_cliente_final=req.id_cliente_final
        )
        # Si la función de negocio tiene éxito, hacemos commit
        db.commit()
        
        return FacturarLoteResponse(
            status="success",
            mensaje="El lote de movimientos ha sido facturado con éxito.",
            datos_factura=resultado_factura,
            ids_procesados=req.ids_movimientos
        )
    except (ValueError, RuntimeError) as e:
        # Si la lógica de negocio lanza un error conocido, revertimos y devolvemos 409
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e))
    except Exception:
        # Para cualquier otro error inesperado, revertimos y devolvemos 500
        db.rollback()
        raise HTTPException(status_code=500, detail="Ocurrió un error interno inesperado al facturar el lote.")

@router.post("/agrupar", response_model=VentaResponse, summary="Agrupa múltiples comprobantes en uno solo nuevo")
def endpoint_agrupar_comprobantes(
    payload: AgruparRequest,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(obtener_usuario_actual)
):
    """
    Toma una lista de IDs de comprobantes existentes (ej: Remitos),
    consolida todos sus ítems en un nuevo comprobante único (ej: una Factura),
    y anula los comprobantes originales.

    Esta operación es atómica: o todo tiene éxito o todo se revierte.
    """
    comprobante_final = agrupar_comprobantes_en_uno_nuevo(
        db=db,
        usuario=usuario_actual,
        ids_a_agrupar=payload.ids_comprobantes,
        nuevo_tipo_comprobante=payload.nuevo_tipo_comprobante
    )
    
    # El commit final se hace aquí para asegurar la atomicidad
    db.commit()
    db.refresh(comprobante_final)
    
    return comprobante_final