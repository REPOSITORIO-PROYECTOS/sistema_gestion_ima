# back/api/blueprints/afip_tools_router.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

# Importamos las dependencias y la lógica de negocio
from back.security import es_rol
from back.gestion import afip_tools_manager
from back.schemas.afip_tools_schemas import CsrRequest, CertificadoRequest

router = APIRouter(
    prefix="/api/afip-tools",
    tags=["Herramientas AFIP"],
    dependencies=[Depends(es_rol(["admin"]))]  # Solo accesible por administradores
)

@router.post("/generar-csr")
def api_generar_csr(req: CsrRequest):
    """
    Genera una clave privada (guardada temporalmente en archivo) y devuelve
    una solicitud de firma de certificado (.csr) para descargar.
    """
    try:
        # Llama a la función refactorizada que usa archivos
        csr_content = afip_tools_manager.generar_csr_y_guardar_clave_temporal(
            cuit_empresa=req.cuit,
            razon_social=req.razon_social
        )
        return Response(content=csr_content, media_type="application/x-pem-file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar CSR: {e}")

@router.post("/subir-certificado")
def api_subir_certificado(req: CertificadoRequest):
    """
    Recibe el certificado firmado y lo envía junto con la clave privada
    temporal al microservicio de Bóveda.
    """
    try:
        # Llama a la función que usa el ClienteBoveda
        resultado = afip_tools_manager.enviar_credenciales_a_boveda(
            cuit=req.cuit,
            certificado_pem=req.certificado_pem
        )
        return resultado
    except ValueError as e: # Captura errores de negocio (clave no encontrada, CUIT duplicado)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e: # Captura errores de autenticación con la bóveda
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Error de autenticación con el servicio de bóveda: {e}")
    except ConnectionError as e: # Captura errores de conexión a la bóveda
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"El servicio de bóveda no está disponible: {e}")
    except Exception as e: # Captura cualquier otro error inesperado
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error inesperado: {e}")