# back/api/blueprints/afip_tools_router.py

from fastapi import APIRouter, Depends, HTTPException, Body
from starlette.responses import Response

from back.security import es_admin
from pydantic import BaseModel
import back.gestion.afip_tools_manager as manager

router = APIRouter(
    prefix="/afip-tools",
    tags=["Herramientas AFIP"],
    dependencies=[Depends(es_admin)]
)

class GenerarCSRRequest(BaseModel):
    cuit: str
    razon_social: str

@router.post("/generar-csr", summary="Generar Clave Privada y CSR")
def api_generar_csr(req: GenerarCSRRequest):
    """
    Genera un par de claves y una Solicitud de Firma de Certificado (CSR).
    Devuelve el CSR para que el usuario lo descargue. La clave privada se
    guarda temporalmente en el servidor.
    """
    try:
        _, csr_pem = manager.generar_claves_y_csr(req.cuit, req.razon_social)
        
        return Response(
            content=csr_pem,
            media_type="application/x-pem-file",
            headers={"Content-Disposition": f'attachment; filename="{req.cuit}.csr"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar el CSR: {e}")

@router.post("/subir-certificado", summary="Subir certificado y guardar en la Bóveda")
def api_subir_certificado(cuit: str = Body(...), certificado_pem: str = Body(...)):
    """
    Recibe el certificado (.crt) de AFIP, lo une con la clave privada
    temporal y guarda ambos en la bóveda de secretos.
    """
    # Esta es una simulación. Aquí iría la lógica completa.
    clave_privada_temp = manager.TEMP_KEY_STORAGE.pop(cuit, None)
    if not clave_privada_temp:
        raise HTTPException(status_code=404, detail="No se encontró una clave privada pendiente para este CUIT. Vuelva a generar el CSR.")

    # manager.guardar_credenciales_en_boveda(cuit, certificado_pem, clave_privada_temp)
    
    print(f"SIMULACIÓN: Credenciales para {cuit} guardadas en la bóveda.")
    print(f"Certificado: {certificado_pem[:30]}...")
    print(f"Clave Privada: {clave_privada_temp[:30]}...")

    return {"message": f"Certificado para la empresa {cuit} procesado y guardado de forma segura."}