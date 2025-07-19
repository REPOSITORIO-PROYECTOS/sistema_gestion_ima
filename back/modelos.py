# /home/sgi_user/proyectos/sistema_gestion_ima/back/modelos.py
# VERSIÓN FINAL UNIFICADA CON MÓDULO DE INVENTARIO AVANZADO

from datetime import datetime, date
from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel, JSON, Column

# ===================================================================
# === MODELOS DE ENTIDADES PRINCIPALES
# ===================================================================

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

    sesiones_abiertas: List["CajaSesion"] = Relationship(back_populates="usuario_apertura", sa_relationship_kwargs={'foreign_keys': '[CajaSesion.id_usuario_apertura]'})
    sesiones_cerradas: List["CajaSesion"] = Relationship(back_populates="usuario_cierre", sa_relationship_kwargs={'foreign_keys': '[CajaSesion.id_usuario_cierre]'})
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
    articulos_proveidos: List["Articulo"] = Relationship(back_populates="proveedor_principal")

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

# ===================================================================
# === MODELO DE ARTÍCULO Y GESTIÓN DE INVENTARIO
# ===================================================================

class Articulo(SQLModel, table=True):
    __tablename__ = "articulos"
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # --- Identificadores Múltiples ---
    codigo_interno: Optional[str] = Field(index=True, unique=True, nullable=True)
    codigo_proveedor: Optional[str] = Field(index=True, nullable=True)

    descripcion: str
    
    # --- Unidades de Compra y Venta (La "División") ---
    unidad_compra: str = Field(default="Unidad")
    unidad_venta: str = Field(default="Unidad")
    factor_conversion: float = Field(default=1.0, description="Cuántas unidades de venta hay en una unidad de compra.")
    
    # --- Componentes para el Cálculo de Precio (Los "Multiplicadores") ---
    precio_costo: float = Field(default=0.0, description="Costo por UNIDAD DE COMPRA, sin IVA.")
    tasa_iva: float = Field(default=0.21, description="La tasa de IVA aplicable, ej: 0.21 para 21%")
    margen_ganancia: float = Field(default=0.0, description="El margen de ganancia deseado, ej: 0.30 para 30%")
    
    # --- Precio Final y Control ---
    precio_venta: float = Field(description="Precio final por UNIDAD DE VENTA, con IVA incluido.")
    auto_actualizar_precio: bool = Field(default=True, description="Si es True, el precio de venta se recalcula al cambiar costo o márgenes.")
    
    venta_negocio: float = Field(default=0.0) # Este campo podría ser para otros usos o descuentos
    
    # --- Stock (medido en UNIDAD DE VENTA) ---
    stock_actual: float = Field(default=0.0)
    stock_minimo: Optional[float] = Field(description="Stock de alerta para reposición")
    
    # --- Reposición Automática ---
    cantidad_minima_pedido: Optional[float]
    cantidad_deseada_pedido: Optional[float]

    # --- Atributos de Control ---
    activo: bool = Field(default=True)
    es_combo: bool = Field(default=False)
    maneja_lotes: bool = Field(default=False)
    
    # --- Relaciones ---
    id_proveedor_principal: Optional[int] = Field(default=None, foreign_key="terceros.id")
    id_categoria: Optional[int] = Field(default=None, foreign_key="categorias.id")
    id_marca: Optional[int] = Field(default=None, foreign_key="marcas.id")

    proveedor_principal: Optional["Tercero"] = Relationship(back_populates="articulos_proveidos")
    categoria: Optional["Categoria"] = Relationship(back_populates="articulos")
    marca: Optional["Marca"] = Relationship(back_populates="articulos")
    
    # Relación a la nueva tabla de códigos
    codigos: List["ArticuloCodigo"] = Relationship(back_populates="articulo")
    
    movimientos_stock: List["StockMovimiento"] = Relationship(back_populates="articulo")
    items_compra: List["CompraDetalle"] = Relationship(back_populates="items_compra")
    items_venta: List["VentaDetalle"] = Relationship(back_populates="items_venta")
    componentes_combo: List["ArticuloCombo"] = Relationship(back_populates="combo_padre", sa_relationship_kwargs={'primaryjoin': 'Articulo.id == ArticuloCombo.id_articulo_padre'})
    parte_de_combos: List["ArticuloCombo"] = Relationship(back_populates="componente_hijo", sa_relationship_kwargs={'primaryjoin': 'Articulo.id == ArticuloCombo.id_articulo_hijo'})
    
class DescuentoProveedor(SQLModel, table=True):
    __tablename__ = "descuento_proveedor"
    id: Optional[int] = Field(default=None, primary_key=True)
    id_proveedor: int = Field(foreign_key="terceros.id")
    porcentaje_descuento: float
    activo: bool = Field(default=True)

class PlantillaProveedor(SQLModel, table=True):
    __tablename__ = "plantilla_proveedor"
    id: Optional[int] = Field(default=None, primary_key=True)
    id_proveedor: int = Field(foreign_key="terceros.id")
    nombre_plantilla: str
    mapeo_columnas: dict = Field(sa_column=Column(JSON))

class ArticuloCombo(SQLModel, table=True):
    __tablename__ = "articulo_combo"
    id_articulo_padre: int = Field(foreign_key="articulos.id", primary_key=True)
    id_articulo_hijo: int = Field(foreign_key="articulos.id", primary_key=True)
    cantidad: float = Field(description="Cantidad del hijo necesaria para 1 unidad del padre")

    combo_padre: Articulo = Relationship(back_populates="componentes_combo", sa_relationship_kwargs={'primaryjoin': 'ArticuloCombo.id_articulo_padre == Articulo.id'})
    componente_hijo: Articulo = Relationship(back_populates="parte_de_combos", sa_relationship_kwargs={'primaryjoin': 'ArticuloCombo.id_articulo_hijo == Articulo.id'})

class ArticuloCodigo(SQLModel, table=True):
    __tablename__ = "articulo_codigos"
    
    # El código de barras es la clave primaria. Debe ser único en toda la tabla.
    codigo: str = Field(primary_key=True, index=True)
    
    id_articulo: int = Field(foreign_key="articulos.id")
    
    # La relación inversa para saber a qué artículo pertenece este código
    articulo: "Articulo" = Relationship(back_populates="codigos")


# ===================================================================
# === MODELOS DE OPERACIONES Y MOVIMIENTOS
# ===================================================================

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
    
    usuario_apertura: Usuario = Relationship(back_populates="sesiones_abiertas", sa_relationship_kwargs={'foreign_keys': '[CajaSesion.id_usuario_apertura]'})
    usuario_cierre: Optional[Usuario] = Relationship(back_populates="sesiones_cerradas", sa_relationship_kwargs={'foreign_keys': '[CajaSesion.id_usuario_cierre]'})
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
    
# ===================================================================
# === MODELOS DE DOCUMENTOS (COMPRAS Y VENTAS)
# ===================================================================

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
    descuento_aplicado: float = Field(default=0.0)
    
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
    descuento_aplicado: float = Field(default=0.0)
    
    id_venta: int = Field(foreign_key="ventas.id")
    id_articulo: int = Field(foreign_key="articulos.id")
    
    venta: Venta = Relationship(back_populates="items")
    articulo: Articulo = Relationship(back_populates="items_venta")
    movimiento_stock: Optional[StockMovimiento] = Relationship(back_populates="venta_detalle")

# ===================================================================
# === MODELOS DE SEGURIDAD Y OTROS
# ===================================================================

class LlaveMaestra(SQLModel, table=True):
    __tablename__ = "llave_maestra"
    id: Optional[int] = Field(default=None, primary_key=True)
    llave: str = Field(index=True, unique=True)
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow)
    fecha_expiracion: datetime