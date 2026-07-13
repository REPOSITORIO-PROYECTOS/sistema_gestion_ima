# back/schemas/configuracion_resuelta_schemas.py

from pydantic import BaseModel, field_validator

from back.schemas.configuracion_schemas import ConfiguracionResponse
from back.schemas.perfil_operativo_schemas import (
    PerfilOperativoResuelto,
    TipoEsquemaEmpresa,
)


class ConfiguracionEstandarResponse(BaseModel):
    """Subconjunto estándar expuesto en la vista resuelta."""

    id_empresa: int
    nombre_negocio: str | None = None
    cuit: str | None = None
    link_google_sheets: str | None = None
    formato_comprobante_predeterminado: str | None = None

    class Config:
        from_attributes = True


class ConfiguracionEmpresaResuelta(BaseModel):
    tipo_esquema: TipoEsquemaEmpresa
    estandar: ConfiguracionEstandarResponse
    perfil_operativo: PerfilOperativoResuelto


class ConfiguracionResponseExtendida(ConfiguracionResponse):
    """Respuesta de mi-empresa con perfil operativo resuelto."""

    tipo_esquema: TipoEsquemaEmpresa = TipoEsquemaEmpresa.ESTANDAR
    perfil_operativo_resuelto: PerfilOperativoResuelto | None = None

    @field_validator("tipo_esquema", mode="before")
    @classmethod
    def normalizar_tipo_esquema(cls, value: object) -> TipoEsquemaEmpresa:
        if isinstance(value, TipoEsquemaEmpresa):
            return value
        if value is None or str(value).strip() == "":
            return TipoEsquemaEmpresa.ESTANDAR
        return TipoEsquemaEmpresa(str(value))
