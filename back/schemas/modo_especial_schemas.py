# back/schemas/modo_especial_schemas.py

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class UnidadMedidaEnum(str, Enum):
    unidad = "unidad"
    gramos = "gramos"
    kilogramos = "kilogramos"
    litros = "litros"
    mililitros = "mililitros"


class ProductoModoEspecialBase(BaseModel):
    codigo_interno: str = Field(min_length=1)
    descripcion: str = Field(min_length=1)
    precio_venta: float = Field(ge=0)
    precio_costo: Optional[float] = Field(default=None, ge=0)
    categorias: List[str] = Field(min_length=1)
    stock: Optional[float] = Field(default=None, ge=0)
    stock_minimo: Optional[float] = Field(default=None, ge=0)
    barcodes: Optional[List[str]] = None
    unidad: UnidadMedidaEnum = UnidadMedidaEnum.unidad
    cantidad_envase: Optional[float] = Field(default=None, ge=0)
    ubicacion: Optional[str] = None

    @field_validator("categorias")
    @classmethod
    def validar_categorias(cls, v: List[str]) -> List[str]:
        limpias = [c.strip() for c in v if c and c.strip()]
        if not limpias:
            raise ValueError("Debe indicar al menos una categoría.")
        return limpias

    @field_validator("barcodes")
    @classmethod
    def limpiar_barcodes(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if not v:
            return None
        limpios = [b.strip() for b in v if b and b.strip()]
        if not limpios:
            return None
        vistos: set[str] = set()
        for codigo in limpios:
            if codigo in vistos:
                raise ValueError(f"El código de barras '{codigo}' está repetido en la lista ingresada.")
            vistos.add(codigo)
        return limpios


class ProductoModoEspecialCreate(ProductoModoEspecialBase):
    pass


class ProductoModoEspecialUpdate(BaseModel):
    descripcion: Optional[str] = None
    precio_venta: Optional[float] = Field(default=None, ge=0)
    precio_costo: Optional[float] = Field(default=None, ge=0)
    categorias: Optional[List[str]] = None
    stock: Optional[float] = Field(default=None, ge=0)
    stock_minimo: Optional[float] = Field(default=None, ge=0)
    barcodes: Optional[List[str]] = None
    unidad: Optional[UnidadMedidaEnum] = None
    cantidad_envase: Optional[float] = Field(default=None, ge=0)
    ubicacion: Optional[str] = None
    activo: Optional[bool] = None

    @field_validator("barcodes")
    @classmethod
    def limpiar_barcodes(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if not v:
            return None
        limpios = [b.strip() for b in v if b and b.strip()]
        if not limpios:
            return None
        vistos: set[str] = set()
        for codigo in limpios:
            if codigo in vistos:
                raise ValueError(f"El código de barras '{codigo}' está repetido en la lista ingresada.")
            vistos.add(codigo)
        return limpios


class ProductoModoEspecialResponse(BaseModel):
    id: int
    codigo_interno: str
    descripcion: str
    precio_venta: float
    precio_costo: float
    venta_negocio: float
    categorias: List[str]
    stock_actual: float
    stock_minimo: Optional[float]
    barcodes: List[str]
    unidad: str
    cantidad_envase: Optional[float]
    ubicacion: Optional[str]
    activo: bool

    class Config:
        from_attributes = True


class IngresoStockItem(BaseModel):
    codigo_interno: Optional[str] = None
    id_articulo: Optional[int] = None
    cantidad: float = Field(gt=0)
    observacion: Optional[str] = None
    precio_venta: Optional[float] = Field(default=None, ge=0)
    precio_costo: Optional[float] = Field(default=None, ge=0)


class IngresoStockRequest(BaseModel):
    items: List[IngresoStockItem] = Field(min_length=1)


class SubaPrecioItem(BaseModel):
    codigo_interno: str
    precio_venta: float = Field(ge=0)


class SubaPreciosRequest(BaseModel):
    porcentaje_general: Optional[float] = None
    categoria: Optional[str] = None
    productos: Optional[List[SubaPrecioItem]] = None


class BulkProductosRequest(BaseModel):
    productos: List[ProductoModoEspecialCreate] = Field(min_length=1)


class ImportExportResumen(BaseModel):
    creados: int = 0
    actualizados: int = 0
    errores: int = 0
    detalle_errores: List[str] = []


class EmpresaTransferenciaResponse(BaseModel):
    id: int
    nombre: str


class TransferenciaStockItem(BaseModel):
    codigo_interno: str = Field(min_length=1)
    cantidad: float = Field(gt=0)
    precio_unitario: Optional[float] = Field(default=None, ge=0)


class CrearTransferenciaStockRequest(BaseModel):
    id_empresa_destino: int
    observacion: Optional[str] = None
    items: List[TransferenciaStockItem] = Field(min_length=1)


class RecibirTransferenciaItem(BaseModel):
    id_detalle: int
    cantidad_recibida: Optional[float] = Field(default=None, gt=0)


class RecibirTransferenciaRequest(BaseModel):
    items: List[RecibirTransferenciaItem] = Field(min_length=1)
    aplicar_precios: bool = True


class TransferenciaStockDetalleResponse(BaseModel):
    id: int
    codigo_interno: str
    descripcion: str
    cantidad: float
    cantidad_recibida: Optional[float]
    precio_unitario: Optional[float]


class TransferenciaStockResponse(BaseModel):
    id: int
    estado: str
    observacion: Optional[str]
    creada_en: str
    recibida_en: Optional[str]
    id_empresa_origen: int
    id_empresa_destino: int
    nombre_empresa_origen: str
    nombre_empresa_destino: str
    detalles: List[TransferenciaStockDetalleResponse]
