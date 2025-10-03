# back/api/blueprints/comprobantes_router.py
# VERSIÓN FINAL, LIMPIA Y COMPLETA

from typing import List, Optional
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
from back.gestion import facturacion_afip
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

class AnularFacturaRequest(BaseModel):
    id_movimiento: int
    motivo: Optional[str]

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
def api_generar_comprobante(
    req: GenerarComprobanteRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    """
    Recibe todos los datos necesarios en el cuerpo de la petición y genera
    un comprobante en PDF (factura, remito, presupuesto o recibo).
    Si es una factura y no tiene datos de AFIP, la procesa primero por AFIP.
    """
    print("entramos a generar comprobante")
    try:
        print("entramos al try de generar comprobante")
        
        # Solo procesar por AFIP si:
        # 1. Es una factura o nota de crédito (los otros tipos como presupuesto, remito, etc. no se procesan)
        # 2. No tiene datos de AFIP ya cargados
        # Las facturas y notas de crédito siempre se procesan por AFIP, incluso para consumidor final
        es_factura = req.tipo.lower() == "factura"
        es_nota_credito = req.tipo.lower() in ["nota_credito", "nota de credito", "nc"]
        necesita_afip = ((es_factura or es_nota_credito) and req.transaccion.afip is None)
        
        if necesita_afip:
            if es_factura:
                print("Procesando factura por AFIP...")
            else:
                print("Procesando nota de crédito por AFIP...")
            
            # Importar las funciones reales de facturación
            from back.gestion.facturacion_afip import generar_factura_para_venta, generar_nota_credito_para_venta
            from back.schemas.comprobante_schemas import AfipData
            from back.modelos import Venta
            from datetime import datetime
            
            try:
                if es_factura:
                    # Crear una venta temporal para AFIP (sin guardar en DB aún)
                    venta_temporal = Venta(
                        total=req.transaccion.total,
                        id_empresa=current_user.id_empresa
                    )
                    
                    # Llamar a la función real de AFIP para facturas
                    resultado_afip = generar_factura_para_venta(
                        db=db,
                        venta_a_facturar=venta_temporal,
                        total=req.transaccion.total,
                        cliente_data=req.receptor,
                        emisor_data=req.emisor,
                        formato_comprobante=req.formato
                    )
                    tipo_comprobante_nombre = "FACTURA"
                    
                elif es_nota_credito:
                    # Para nota de crédito necesitamos el comprobante asociado
                    comprobante_asociado = req.comprobante_asociado or {
                        "tipo_afip": 1,  # Factura A por defecto
                        "punto_venta": req.emisor.punto_venta,
                        "numero_comprobante": 1  # Valor por defecto si no se especifica
                    }
                    
                    # Llamar a la función real de AFIP para notas de crédito
                    resultado_afip = generar_nota_credito_para_venta(
                        total=req.transaccion.total,
                        cliente_data=req.receptor,
                        emisor_data=req.emisor,
                        comprobante_asociado=comprobante_asociado
                    )
                    tipo_comprobante_nombre = "NOTA DE CREDITO"
                
                # Debug: Log de la respuesta de AFIP
                print(f"DEBUG - Respuesta de AFIP: {resultado_afip}")
                
                # Crear el objeto AfipData con los datos reales de AFIP con validaciones
                req.transaccion.afip = AfipData(
                    fecha_emision=resultado_afip.get("fecha_comprobante") or datetime.now().strftime("%Y-%m-%d"),
                    tipo_comprobante_afip=resultado_afip.get("tipo_afip") or 1,
                    tipo_comprobante_nombre=tipo_comprobante_nombre,
                    numero_comprobante=resultado_afip.get("numero_comprobante") or 0,
                    codigo_tipo_doc_receptor=resultado_afip.get("tipo_doc_receptor") or 99,
                    cae=resultado_afip.get("cae") or "SIN_CAE",
                    fecha_vencimiento_cae=resultado_afip.get("vencimiento_cae"),
                    qr_base64=resultado_afip.get("qr_base64")
                )
                print(f"Procesamiento real por AFIP completado. CAE: {resultado_afip.get('cae')}")
                
            except Exception as e:
                print(f"Error en procesamiento AFIP: {e}")
                raise HTTPException(status_code=500, detail=f"Error en procesamiento AFIP: {str(e)}")
        else:
            print(f"Comprobante tipo '{req.tipo}' no requiere procesamiento AFIP")
        
        pdf_bytes = generar_comprobante_stateless(req)
        print("salimos de genrerar comprobantes stateless")
        # Generamos un nombre de archivo más robusto
        filename = f"{req.tipo}_{req.emisor.punto_venta}_{req.receptor.cuit_o_dni or 'consumidor'}.pdf"
        print("estamos por hacer la response")
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

@router.post("/anular-factura", summary="Anula una factura existente mediante una Nota de Crédito")
def api_anular_factura_con_nc(
    req: AnularFacturaRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(obtener_usuario_actual)
):
    """
    Recibe el ID de un movimiento de venta ya facturado, invoca la lógica
    de negocio para generar la Nota de Crédito correspondiente en AFIP,
    y actualiza el estado de la venta original en la base de datos.
    La operación es atómica.
    """
    try:
        # Llamamos a la función "hermana" que ya creamos en el manager
        resultado_nc = facturacion_lotes_manager.crear_nota_credito_para_anular(
            db=db,
            usuario_actual=current_user,
            id_movimiento_a_anular=req.id_movimiento_a_anular
        )
        
        # Si la lógica del manager no lanzó ninguna excepción, hacemos commit
        db.commit()
        
        return {
            "status": "success",
            "mensaje": "La factura ha sido anulada con éxito mediante la Nota de Crédito.",
            "datos_nota_credito": resultado_nc
        }
    except (ValueError, RuntimeError) as e:
        # Capturamos errores de negocio (ej: "ya fue anulada", "no es una factura")
        db.rollback() # Revertimos cualquier cambio parcial en la sesión de la DB
        raise HTTPException(
            status_code=409, # 409 Conflict es un buen código para errores de lógica de negocio
            detail=str(e)
        )
    except Exception as e:
        # Capturamos cualquier otro error inesperado (ej: fallo de red con la bóveda)
        db.rollback()
        # En producción, deberías loguear el error 'e' para poder depurarlo
        print(f"ERROR INESPERADO al anular factura: {e}")
        raise HTTPException(
            status_code=500, # 500 Internal Server Error
            detail="Ocurrió un error interno inesperado al intentar anular la factura."
        )
