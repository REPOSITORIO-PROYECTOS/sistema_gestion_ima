# back/schemas/perfil_operativo_schemas.py

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class TipoEsquemaEmpresa(str, Enum):
    ESTANDAR = "estandar"
    ESPECIAL = "especial"


class PerfilOperativoEmpresa(BaseModel):
    version: int = 1
    plantilla_origen: Optional[str] = None
    modo_especial: bool = False
    sincronizar_google_sheets: bool = True
    caja_solo_comprobante: bool = False
    caja_permitir_remito_presupuesto: bool = False
    factura_auto_mercado_pago: bool = False
    panel_estadisticas_caja: bool = False
    mesas_habilitado: bool = False
    bloquear_descuentos_cajero: bool = False
    balanza_auto_agregar: bool = False
    balanza_auto_facturar: bool = False
    cache_degradado: bool = False
    empresas_transferencia_ids: list[int] = Field(default_factory=list)
    casos_especiales: dict[str, str | int | bool] = Field(default_factory=dict)


class PerfilOperativoResuelto(PerfilOperativoEmpresa):
    facturacion_afip_habilitada: bool = False
    caja_puede_facturar: bool = False
    caja_puede_remito_presupuesto: bool = False


class PerfilOperativoUpdate(BaseModel):
    """PATCH parcial del perfil operativo (solo esquema especial)."""

    modo_especial: Optional[bool] = None
    sincronizar_google_sheets: Optional[bool] = None
    caja_solo_comprobante: Optional[bool] = None
    caja_permitir_remito_presupuesto: Optional[bool] = None
    factura_auto_mercado_pago: Optional[bool] = None
    panel_estadisticas_caja: Optional[bool] = None
    mesas_habilitado: Optional[bool] = None
    bloquear_descuentos_cajero: Optional[bool] = None
    balanza_auto_agregar: Optional[bool] = None
    balanza_auto_facturar: Optional[bool] = None
    cache_degradado: Optional[bool] = None
    empresas_transferencia_ids: Optional[list[int]] = None
    casos_especiales: Optional[dict[str, str | int | bool]] = None


class MigrarEsquemaRequest(BaseModel):
    tipo_esquema: TipoEsquemaEmpresa
    plantilla_id: Optional[str] = None


class PlantillaPerfilResponse(BaseModel):
    id: str
    nombre: str
    descripcion: str
    perfil: PerfilOperativoEmpresa


class PerfilOperativoAdminResponse(BaseModel):
    id_empresa: int
    tipo_esquema: TipoEsquemaEmpresa
    perfil_operativo: PerfilOperativoEmpresa
    perfil_operativo_resuelto: PerfilOperativoResuelto
    modo_especial_habilitado: bool
    tiene_archivo: bool = False
