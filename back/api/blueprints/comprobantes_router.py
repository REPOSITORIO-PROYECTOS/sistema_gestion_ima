# back/api/blueprints/comprobantes_router.py

from fastapi import APIRouter, Depends, HTTPException
from starlette.responses import Response

# --- Módulos del Proyecto ---
from back.security import es_cajero # O una dependencia de seguridad genérica
from back.schemas.comprobante_schemas import GenerarComprobanteRequest
from back.gestion.reportes.generador_comprobantes import generar_comprobante_stateless

router = APIRouter(
    prefix="/comprobantes",
    tags=["Generación de Comprobantes"],
    dependencies=[Depends(es_cajero)] # Aún protegido por un login de usuario
)

@router.post(
    "/generar",
    summary="Generar un comprobante (factura, remito, etc.) on-demand",
    responses={
        200: {"content": {"application/pdf": {}}, "description": "El archivo PDF del comprobante."},
        422: {"description": "Datos de entrada inválidos."},
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
        
        filename = f"{req.tipo}_{req.emisor.punto_venta}_{req.receptor.cuit_o_dni}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'}
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"ERROR INESPERADO al generar comprobante: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno al generar el comprobante.")