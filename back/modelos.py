#/sistema_gestion_ima/back/modelos.py

from datetime import datetime, date
from typing import Dict, List, Optional
from sqlmodel import Field, Relationship, SQLModel, JSON, Column
from sqlalchemy import UniqueConstraint

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
    # --- RELACIÓN CON EMPRESA ---
    id_empresa: int = Field(foreign_key="empresas.id")
    empresa: "Empresa" = Relationship(back_populates="usuarios")    

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
    id_empresa: int = Field(foreign_key="empresas.id")
    empresa: "Empresa" = Relationship() # No necesita back_populates si Empresa no lista terceros

    # --- NUEVA RELACIÓN PARA LAS PLANTILLAS DE IMPORTACIÓN ---
    plantillas_mapeo: List["PlantillaMapeoProveedor"] = Relationship(back_populates="proveedor")

    # --- NUEVA RELACIÓN PARA LOS ARTÍCULOS ASOCIADOS ---
    articulos_asociados: List["ArticuloProveedor"] = Relationship(back_populates="proveedor")


class Categoria(SQLModel, table=True):
    __tablename__ = "categorias"
    __table_args__ = (UniqueConstraint("nombre", "id_empresa", name="uq_nombre_empresa_categoria"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str 
    id_empresa: int = Field(foreign_key="empresas.id")
    articulos: List["Articulo"] = Relationship(back_populates="categoria")
    empresa: "Empresa" = Relationship()
    
class Marca(SQLModel, table=True):
    __tablename__ = "marcas"
    __table_args__ = (UniqueConstraint("nombre", "id_empresa", name="uq_nombre_empresa_categoria"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    articulos: List["Articulo"] = Relationship(back_populates="marca")
    id_empresa: int = Field(foreign_key="empresas.id")
    empresa: "Empresa" = Relationship()
    
# ===================================================================
# === MODELO DE ARTÍCULO Y GESTIÓN DE INVENTARIO
# ===================================================================

class Articulo(SQLModel, table=True):
    __tablename__ = "articulos"
    id: Optional[int] = Field(default=None, primary_key=True)
    codigo_interno: Optional[str] = Field(index=True, unique=True, nullable=True)
    descripcion: str
    unidad_compra: str = Field(default="Unidad")
    unidad_venta: str = Field(default="Unidad")
    factor_conversion: float = Field(default=1.0)
    precio_costo: float = Field(default=0.0)
    tasa_iva: float = Field(default=0.21)
    margen_ganancia: float = Field(default=0.0)
    precio_venta: float
    auto_actualizar_precio: bool = Field(default=True)
    venta_negocio: float = Field(default=0.0)
    stock_actual: float = Field(default=0.0)
    stock_minimo: Optional[float]
    cantidad_minima_pedido: Optional[float]
    cantidad_deseada_pedido: Optional[float]
    activo: bool = Field(default=True)
    es_combo: bool = Field(default=False)
    maneja_lotes: bool = Field(default=False)
    
    id_categoria: Optional[int] = Field(default=None, foreign_key="categorias.id")
    id_marca: Optional[int] = Field(default=None, foreign_key="marcas.id")

    categoria: Optional["Categoria"] = Relationship(back_populates="articulos")
    marca: Optional["Marca"] = Relationship(back_populates="articulos")
    empresa: "Empresa" = Relationship()
    proveedores: List["ArticuloProveedor"] = Relationship(back_populates="articulo")
   
    codigos: List["ArticuloCodigo"] = Relationship(back_populates="articulo")
    movimientos_stock: List["StockMovimiento"] = Relationship(back_populates="articulo")
    
    # === LA CORRECCIÓN CLAVE ESTÁ AQUÍ ===
    items_compra: List["CompraDetalle"] = Relationship(back_populates="articulo")
    items_venta: List["VentaDetalle"] = Relationship(back_populates="articulo")
    
    componentes_combo: List["ArticuloCombo"] = Relationship(back_populates="combo_padre", sa_relationship_kwargs={'primaryjoin': 'Articulo.id == ArticuloCombo.id_articulo_padre'})
    parte_de_combos: List["ArticuloCombo"] = Relationship(back_populates="componente_hijo", sa_relationship_kwargs={'primaryjoin': 'Articulo.id == ArticuloCombo.id_articulo_hijo'})
    # Relación con códigos de barras
    codigos_barras: List["ArticuloCodigo"] = Relationship(back_populates="articulo")

    # --- CAMPO Y RELACIÓN AÑADIDOS PARA MULTI-EMPRESA ---
    # Asumo que Empresa ya existe en este archivo.
    id_empresa: int = Field(foreign_key="empresas.id")
    
class DescuentoProveedor(SQLModel, table=True):
    __tablename__ = "descuento_proveedor"
    id: Optional[int] = Field(default=None, primary_key=True)
    id_proveedor: int = Field(foreign_key="terceros.id")
    porcentaje_descuento: float
    activo: bool = Field(default=True)

class PlantillaMapeoProveedor(SQLModel, table=True):
    __tablename__ = "plantilla_mapeo_proveedor" # Renombrado para claridad
    __table_args__ = (UniqueConstraint("nombre_plantilla", "id_empresa", name="uq_nombre_plantilla_empresa"),)
    
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre_plantilla: str
    
    # Relaciones clave
    id_proveedor: int = Field(foreign_key="terceros.id")
    id_empresa: int = Field(foreign_key="empresas.id")
    
    # Configuración del mapeo (tu implementación era perfecta)
    mapeo_columnas: Dict[str, str] = Field(sa_column=Column(JSON))
    nombre_hoja_excel: Optional[str] = Field(default=None) # Ej: "Lista Precios"
    fila_inicio: int = Field(default=2) # Es más común que la fila 1 sea de encabezados

    # Relaciones para navegar
    proveedor: Tercero = Relationship(back_populates="plantillas_mapeo")
    empresa: "Empresa" = Relationship()

class ArticuloCombo(SQLModel, table=True):
    __tablename__ = "articulo_combo"
    id_articulo_padre: int = Field(foreign_key="articulos.id", primary_key=True)
    id_articulo_hijo: int = Field(foreign_key="articulos.id", primary_key=True)
    cantidad: float
    combo_padre: Articulo = Relationship(back_populates="componentes_combo", sa_relationship_kwargs={'primaryjoin': 'ArticuloCombo.id_articulo_padre == Articulo.id'})
    componente_hijo: Articulo = Relationship(back_populates="parte_de_combos", sa_relationship_kwargs={'primaryjoin': 'ArticuloCombo.id_articulo_hijo == Articulo.id'})

class ArticuloCodigo(SQLModel, table=True):
    __tablename__ = "articulo_codigos"
    codigo: str = Field(primary_key=True, index=True)
    id_articulo: int = Field(foreign_key="articulos.id")
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
    id_empresa: int = Field(foreign_key="empresas.id")
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
    id_empresa: int = Field(foreign_key="empresas.id")
    empresa: "Empresa" = Relationship()
    
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
    id_empresa: int = Field(foreign_key="empresas.id")
    empresa: "Empresa" = Relationship()


class CompraDetalle(SQLModel, table=True):
    __tablename__ = "compra_detalle"
    id: Optional[int] = Field(default=None, primary_key=True)
    cantidad: float
    costo_unitario: float
    descuento_aplicado: float = Field(default=0.0)
    id_compra: int = Field(foreign_key="compras.id")
    id_articulo: int = Field(foreign_key="articulos.id")
    compra: Compra = Relationship(back_populates="items")
    # === LA CORRECCIÓN CLAVE ESTÁ AQUÍ ===
    articulo: Articulo = Relationship(back_populates="items_compra")
    movimiento_stock: Optional[StockMovimiento] = Relationship(back_populates="compra_detalle")

class Venta(SQLModel, table=True):
    __tablename__ = "ventas"
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    total: float
    facturada: bool = Field(default=False, index=True)
    datos_factura: Optional[Dict[str, str]] = Field(default=None, sa_column=Column(JSON))
    estado: str = Field(default="COMPLETADA")
    id_cliente: Optional[int] = Field(default=None, foreign_key="terceros.id")
    id_usuario: int = Field(foreign_key="usuarios.id")
    id_caja_sesion: int = Field(foreign_key="caja_sesiones.id")
    cliente: Optional[Tercero] = Relationship(back_populates="ventas_recibidas")
    usuario: Usuario = Relationship(back_populates="ventas_realizadas")
    caja_sesion: CajaSesion = Relationship(back_populates="ventas")
    items: List["VentaDetalle"] = Relationship(back_populates="venta")
    movimientos_de_caja: List[CajaMovimiento] = Relationship(back_populates="venta")
    id_empresa: int = Field(foreign_key="empresas.id")
    empresa: "Empresa" = Relationship() # Puedes añadir back_populates si quieres


class VentaDetalle(SQLModel, table=True):
    __tablename__ = "venta_detalle"
    id: Optional[int] = Field(default=None, primary_key=True)
    cantidad: float
    precio_unitario: float
    descuento_aplicado: float = Field(default=0.0)
    id_venta: int = Field(foreign_key="ventas.id")
    id_articulo: int = Field(foreign_key="articulos.id")
    venta: Venta = Relationship(back_populates="items")
    # === LA CORRECCIÓN CLAVE ESTÁ AQUÍ ===
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
    
# ===================================================================
# === MODELOS DE CONFIGURACIÓN Y MULTI-EMPRESA
# ===================================================================   

class Empresa(SQLModel, table=True):
    __tablename__ = "empresas"
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre_legal: str = Field(index=True, unique=True) # Razón Social
    nombre_fantasia: Optional[str]
    cuit: str = Field(unique=True, index=True)
    activa: bool = Field(default=True)
    creada_en: datetime = Field(default_factory=datetime.utcnow)

    # --- RELACIONES ---
    
    # Cada empresa tiene su propia configuración específica.
    configuracion: Optional["ConfiguracionEmpresa"] = Relationship(back_populates="empresa")
    
    # Cada usuario pertenece a una empresa.
    usuarios: List["Usuario"] = Relationship(back_populates="empresa")

class ConfiguracionEmpresa(SQLModel, table=True):
    __tablename__ = "configuracion_empresa"
    
    # La clave primaria es el ID de la empresa. Esto asegura que solo haya
    # una fila de configuración por empresa. Es una relación uno a uno.
    id_empresa: int = Field(foreign_key="empresas.id", primary_key=True)
    link_google_sheets: Optional[str] = Field(default=None) # Enlace a Google Sheets para reportes
    
    # --- Configuración de Apariencia ---
    nombre_negocio: Optional[str] # Nombre a mostrar en los tickets
    color_principal: str = Field(default="#000000")
    ruta_logo: Optional[str] = Field(default=None)
    ruta_icono: Optional[str] = Field(default=None)
    
    # --- Configuración Fiscal (AFIP) ---
    afip_condicion_iva: Optional[str] = Field(default=None) # Ej: Monotributo, Responsable Inscripto
    afip_punto_venta_predeterminado: Optional[int] = Field(default=None)
    
    # --- Datos de Contacto del Negocio ---
    direccion_negocio: Optional[str] = Field(default=None)
    telefono_negocio: Optional[str] = Field(default=None)
    mail_negocio: Optional[str] = Field(default=None)
    
    # --- Bóveda de Secretos ---
    # Aquí irían los secretos ENCRIPTADOS. El nombre del campo lo deja claro.
    afip_certificado_encrypted: Optional[str] = Field(default=None)
    afip_clave_privada_encrypted: Optional[str] = Field(default=None)
    
    # --- RELACIÓN ---
    empresa: Empresa = Relationship(back_populates="configuracion")
    
    
class ArticuloProveedor(SQLModel, table=True):
    __tablename__ = "articulo_proveedor"
    id_articulo: int = Field(foreign_key="articulos.id", primary_key=True)
    id_proveedor: int = Field(foreign_key="terceros.id", primary_key=True)
    
    # Este es el campo clave para la importación
    codigo_articulo_proveedor: str = Field(index=True) 

    # Relaciones para poder navegar desde este objeto
    articulo: Articulo = Relationship(back_populates="proveedores")
    proveedor: Tercero = Relationship(back_populates="articulos_asociados")