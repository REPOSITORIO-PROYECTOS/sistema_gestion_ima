# /home/sgi_user/proyectos/sistema_gestion_ima/back/modelos.py
# VERSIÓN COMPLETA CON RELACIONES BIDIRECCIONALES Y LLAVE MAESTRA

from datetime import datetime, date
from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel

# --- MODELOS DE ENTIDADES PRINCIPALES ---

class Rol(SQLModel, table=True):
    __tablename__ = "roles"
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(index=True, unique=True)
    
    usuarios: List["Usuario"] = Relationship(back_populates="rol")

class Usuario(SQLModel, table=True):
    __tablename__ = "usuarios"
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre_usuario: str = Field(index=True, unique=True)
    password_hash: str
    activo: bool = Field(default=True)
    creado_en: datetime = Field(default_factory=datetime.utcnow)
    
    id_rol: int = Field(foreign_key="roles.id")
    rol: Rol = Relationship(back_populates="usuarios")

    # --- Relaciones Inversas ---
    sesiones_abiertas: List["CajaSesion"] = Relationship(
        back_populates="usuario_apertura",
        sa_relationship_kwargs={'foreign_keys': '[CajaSesion.id_usuario_apertura]'}
    )
    sesiones_cerradas: List["CajaSesion"] = Relationship(
        back_populates="usuario_cierre",
        sa_relationship_kwargs={'foreign_keys': '[CajaSesion.id_usuario_cierre]'}
    )
    movimientos_de_caja: List["CajaMovimiento"] = Relationship(back_populates="usuario")
    movimientos_de_stock: List["StockMovimiento"] = Relationship(back_populates="usuario")
    compras_registradas: List["Compra"] = Relationship(back_populates="usuario")
    ventas_realizadas: List["Venta"] = Relationship(back_populates="usuario")

class Tercero(SQLModel, table=True):
    __tablename__ = "terceros"
    id: int = Field(primary_key=True)
    codigo_interno: Optional[str] = Field(index=True)
    es_cliente: bool = Field(default=False)
    es_proveedor: bool = Field(default=False)
    nombre_razon_social: str = Field(index=True)
    nombre_fantasia: Optional[str]
    cuit: Optional[str] = Field(unique=True, index=True)
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

    compras_realizadas: List["Compra"] = Relationship(back_populates="proveedor")
    ventas_recibidas: List["Venta"] = Relationship(back_populates="cliente")

class Categoria(SQLModel, table=True):
    __tablename__ = "categorias"
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(unique=True)
    
    articulos: List["Articulo"] = Relationship(back_populates="categoria")

class Marca(SQLModel, table=True):
    __tablename__ = "marcas"
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(unique=True)

    articulos: List["Articulo"] = Relationship(back_populates="marca")

class Articulo(SQLModel, table=True):
    __tablename__ = "articulos"
    id: Optional[int] = Field(default=None, primary_key=True)
    codigo_barras: Optional[str] = Field(index=True, unique=True)
    descripcion: str
    precio_costo: float = Field(default=0.0)
    precio_venta: float
    venta_negocio: float = Field(default=0.0)
    stock_actual: float = Field(default=0.0)
    stock_minimo: Optional[float]
    activo: bool = Field(default=True)
    maneja_lotes: bool = Field(default=False)
    
    id_categoria: Optional[int] = Field(default=None, foreign_key="categorias.id")
    id_marca: Optional[int] = Field(default=None, foreign_key="marcas.id")

    categoria: Optional[Categoria] = Relationship(back_populates="articulos")
    marca: Optional[Marca] = Relationship(back_populates="articulos")
    movimientos_stock: List["StockMovimiento"] = Relationship(back_populates="articulo")
    items_compra: List["CompraDetalle"] = Relationship(back_populates="articulo")
    items_venta: List["VentaDetalle"] = Relationship(back_populates="articulo")

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
    estado: str = Field(default="ABIERTA")
    
    id_usuario_apertura: int = Field(foreign_key="usuarios.id")
    id_usuario_cierre: Optional[int] = Field(default=None, foreign_key="usuarios.id")
    
    usuario_apertura: Usuario = Relationship(
        back_populates="sesiones_abiertas",
        sa_relationship_kwargs={'foreign_keys': '[CajaSesion.id_usuario_apertura]'}
    )
    usuario_cierre: Optional[Usuario] = Relationship(
        back_populates="sesiones_cerradas",
        sa_relationship_kwargs={'foreign_keys': '[CajaSesion.id_usuario_cierre]'}
    )
    movimientos: List["CajaMovimiento"] = Relationship(back_populates="caja_sesion")
    ventas: List["Venta"] = Relationship(back_populates="caja_sesion")

class CajaMovimiento(SQLModel, table=True):
    __tablename__ = "caja_movimientos"
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tipo: str
    concepto: str
    monto: float
    metodo_pago: str
    
    id_caja_sesion: int = Field(foreign_key="caja_sesiones.id")
    id_usuario: int = Field(foreign_key="usuarios.id")
    id_venta: Optional[int] = Field(default=None, foreign_key="ventas.id")
    
    caja_sesion: CajaSesion = Relationship(back_populates="movimientos")
    usuario: Usuario = Relationship(back_populates="movimientos_de_caja")
    venta: Optional["Venta"] = Relationship(back_populates="movimientos_de_caja")

class StockMovimiento(SQLModel, table=True):
    __tablename__ = "stock_movimientos"
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tipo: str
    cantidad: float
    stock_anterior: float
    stock_nuevo: float
    
    id_articulo: int = Field(foreign_key="articulos.id")
    id_usuario: int = Field(foreign_key="usuarios.id")
    id_compra_detalle: Optional[int] = Field(default=None, foreign_key="compra_detalle.id")
    id_venta_detalle: Optional[int] = Field(default=None, foreign_key="venta_detalle.id")

    articulo: Articulo = Relationship(back_populates="movimientos_stock")
    usuario: Usuario = Relationship(back_populates="movimientos_de_stock")
    compra_detalle: Optional["CompraDetalle"] = Relationship(back_populates="movimiento_stock")
    venta_detalle: Optional["VentaDetalle"] = Relationship(back_populates="movimiento_stock")
    
# --- MODELOS DE DOCUMENTOS (COMPRAS Y VENTAS) ---

class Compra(SQLModel, table=True):
    __tablename__ = "compras"
    id: Optional[int] = Field(default=None, primary_key=True)
    fecha_emision: date
    numero_factura_proveedor: str
    total: float
    estado: str = Field(default="RECIBIDA")
    
    id_proveedor: int = Field(foreign_key="terceros.id")
    id_usuario: int = Field(foreign_key="usuarios.id")
    
    proveedor: Tercero = Relationship(back_populates="compras_realizadas")
    usuario: Usuario = Relationship(back_populates="compras_registradas")
    items: List["CompraDetalle"] = Relationship(back_populates="compra")

class CompraDetalle(SQLModel, table=True):
    __tablename__ = "compra_detalle"
    id: Optional[int] = Field(default=None, primary_key=True)
    cantidad: float
    costo_unitario: float
    
    id_compra: int = Field(foreign_key="compras.id")
    id_articulo: int = Field(foreign_key="articulos.id")
    
    compra: Compra = Relationship(back_populates="items")
    articulo: Articulo = Relationship(back_populates="items_compra")
    movimiento_stock: Optional[StockMovimiento] = Relationship(back_populates="compra_detalle")

class Venta(SQLModel, table=True):
    __tablename__ = "ventas"
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    total: float
    estado: str = Field(default="COMPLETADA")
    
    id_cliente: Optional[int] = Field(default=None, foreign_key="terceros.id")
    id_usuario: int = Field(foreign_key="usuarios.id")
    id_caja_sesion: int = Field(foreign_key="caja_sesiones.id")
    
    cliente: Optional[Tercero] = Relationship(back_populates="ventas_recibidas")
    usuario: Usuario = Relationship(back_populates="ventas_realizadas")
    caja_sesion: CajaSesion = Relationship(back_populates="ventas")
    items: List["VentaDetalle"] = Relationship(back_populates="venta")
    movimientos_de_caja: List[CajaMovimiento] = Relationship(back_populates="venta")

class VentaDetalle(SQLModel, table=True):
    __tablename__ = "venta_detalle"
    id: Optional[int] = Field(default=None, primary_key=True)
    cantidad: float
    precio_unitario: float
    
    id_venta: int = Field(foreign_key="ventas.id")
    id_articulo: int = Field(foreign_key="articulos.id")
    
    venta: Venta = Relationship(back_populates="items")
    articulo: Articulo = Relationship(back_populates="items_venta")
    movimiento_stock: Optional[StockMovimiento] = Relationship(back_populates="venta_detalle")

# --- Modelo de seguridad que discutimos ---
class LlaveMaestra(SQLModel, table=True):
    __tablename__ = "llave_maestra"
    id: Optional[int] = Field(default=None, primary_key=True)
    llave: str = Field(index=True, unique=True)
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow)
    fecha_expiracion: datetime