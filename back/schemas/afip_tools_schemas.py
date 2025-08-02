# back/schemas/afip_tools_schemas.py

from pydantic import BaseModel, Field

class CsrRequest(BaseModel):
    """
    Schema para la petición de generación de un CSR.
    Contiene los datos necesarios para construir el 'subject' del certificado.
    """
    cuit: str = Field(
        ...,
        description="El CUIT de la empresa para la que se genera el certificado. Sin guiones.",
        examples=["30123456789"]
    )
    razon_social: str = Field(
        ...,
        description="La razón social completa de la empresa.",
        examples=["Mi Empresa S.A."]
    )

class CertificadoRequest(BaseModel):
    """
    Schema para la petición de subida de un certificado firmado.
    Contiene el CUIT para identificar la clave privada temporal y el
    contenido del certificado en formato PEM.
    """
    cuit: str = Field(
        ...,
        description="El CUIT de la empresa, debe coincidir con el usado para generar el CSR.",
        examples=["30123456789"]
    )
    certificado_pem: str = Field(
        ...,
        description="El contenido completo del archivo .crt como un string, incluyendo las líneas BEGIN/END.",
        examples=["-----BEGIN CERTIFICATE-----\nMIIC...BASE64DATA...==\n-----END CERTIFICATE-----"]
    )