# back/modelos.py
from datetime import datetime, date, time
from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel, create_engine

# --- MODELOS DE ENTIDADES PRINCIPALES ---

class Rol(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(index=True, unique=True)
    usuarios: List["Usuario"] = Relationship(back_populates="rol")

class Usuario(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre_usuario: str = Field(index=True, unique=True)
    password_hash: str
    activo: bool = Field(default=True)
    creado_en: datetime = Field(default_factory=datetime.utcnow)
    
    id_rol: int = Field(foreign_key="rol.id")
    rol: Rol = Relationship(back_populates="usuarios")

class Tercero(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    codigo_interno: Optional[str] = Field(index=True)
    es_cliente: bool = Field(default=False)
    es_proveedor: bool = Field(default=False)
    nombre_razon_social: str = Field(index=True)
    nombre_fantasia: Optional[str]
    identificacion_fiscal: Optional[str] = Field(index=True)
    condicion_iva: str
    direccion: Optional[str]
    localidad: Optional[str]
    provincia: Optional[str]
    pais: Optional[str]
    telefono: Optional[str]
    email: Optional[str]
    limite_credito: float = Field(default=0.0)
    activo: bool = Field(default=True)
    fecha_alta: datetime = Field(default_factory=datetime.utcnow)
    notas: Optional[str]

class Categoria(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(unique=True)

class Marca(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(unique=True)

class Articulo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    codigo_barras: Optional[str] = Field(index=True, unique=True)
    descripcion: str
    precio_costo: float = Field(default=0.0)
    precio_venta: float
    stock_actual: float = Field(default=0.0)
    stock_minimo: Optional[float]
    activo: bool = Field(default=True)
    maneja_lotes: bool = Field(default=False)
    
    id_categoria: Optional[int] = Field(default=None, foreign_key="categoria.id")
    id_marca: Optional[int] = Field(default=None, foreign_key="marca.id")

# --- MODELOS DE OPERACIONES ---

class CajaSesion(SQLModel, table=True):
    __tablename__ = "caja_sesiones"
    id: Optional[int] = Field(default=None, primary_key=True)
    fecha_apertura: datetime = Field(default_factory=datetime.utcnow)
    saldo_inicial: float
    fecha_cierre: Optional[datetime] = None
    saldo_final_declarado: Optional[float]
    saldo_final_calculado: Optional[float]
    diferencia: Optional[float]
    estado: str = Field(default="ABIERTA") # Ej: ABIERTA, CERRADA
    
    id_usuario_apertura: int = Field(foreign_key="usuario.id")
    id_usuario_cierre: Optional[int] = Field(default=None, foreign_key="usuario.id")
    
class CajaMovimiento(SQLModel, table=True):
    __tablename__ = "caja_movimientos"
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tipo: str  # Ej: VENTA, EGRESO, INGRESO_EXTRA
    concepto: str
    monto: float
    metodo_pago: str # Ej: EFECTIVO, TARJETA, TRANSFERENCIA
    
    id_caja_sesion: int = Field(foreign_key="caja_sesiones.id")
    id_usuario: int = Field(foreign_key="usuario.id")
    id_venta: Optional[int] = Field(default=None, foreign_key="venta.id") # Si es una venta
    
class StockMovimiento(SQLModel, table=True):
    __tablename__ = "stock_movimientos"
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tipo: str  # Ej: COMPRA, VENTA, AJUSTE_POSITIVO, AJUSTE_NEGATIVO
    cantidad: float
    stock_anterior: float
    stock_nuevo: float
    
    id_articulo: int = Field(foreign_key="articulo.id")
    id_usuario: int = Field(foreign_key="usuario.id")
    id_compra_detalle: Optional[int] = Field(default=None, foreign_key="compra_detalle.id")
    id_venta_detalle: Optional[int] = Field(default=None, foreign_key="venta_detalle.id")

# --- MODELOS DE DOCUMENTOS (COMPRAS Y VENTAS) ---

class Compra(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    fecha_emision: date
    numero_factura_proveedor: str
    total: float
    estado: str = Field(default="RECIBIDA")
    
    id_proveedor: int = Field(foreign_key="tercero.id")
    id_usuario: int = Field(foreign_key="usuario.id")
    
    items: List["CompraDetalle"] = Relationship(back_populates="compra")

class CompraDetalle(SQLModel, table=True):
    __tablename__ = "compra_detalle"
    id: Optional[int] = Field(default=None, primary_key=True)
    cantidad: float
    costo_unitario: float
    
    id_compra: int = Field(foreign_key="compra.id")
    id_articulo: int = Field(foreign_key="articulo.id")
    
    compra: Compra = Relationship(back_populates="items")
    
class Venta(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    total: float
    estado: str = Field(default="COMPLETADA") # o ANULADA
    
    id_cliente: Optional[int] = Field(default=None, foreign_key="tercero.id")
    id_usuario: int = Field(foreign_key="usuario.id")
    id_caja_sesion: int = Field(foreign_key="caja_sesiones.id")
    
    items: List["VentaDetalle"] = Relationship(back_populates="venta")

class VentaDetalle(SQLModel, table=True):
    __tablename__ = "venta_detalle"
    id: Optional[int] = Field(default=None, primary_key=True)
    cantidad: float
    precio_unitario: float
    
    id_venta: int = Field(foreign_key="venta.id")
    id_articulo: int = Field(foreign_key="articulo.id")
    
    venta: Venta = Relationship(back_populates="items")