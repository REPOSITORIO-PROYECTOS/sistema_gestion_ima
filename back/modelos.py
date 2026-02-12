#/sistema_gestion_ima/back/modelos.py

from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlmodel import Field, Relationship, SQLModel, JSON, Column
from sqlalchemy import DECIMAL, TIMESTAMP, BigInteger, Date, UniqueConstraint, func
from sqlmodel import Column  # Importante
from sqlalchemy import String,JSON   # Importante

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
    configuracion: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

class Tercero(SQLModel, table=True):
    __tablename__ = "terceros"
    id: int = Field(primary_key=True)
    codigo_interno: Optional[str] = Field(index=True)
    es_cliente: bool = Field(default=False)
    es_proveedor: bool = Field(default=False)
    nombre_razon_social: str = Field(index=True)
    nombre_fantasia: Optional[str]
    cuit: Optional[str] = Field(default=None, index=True) 
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
    __table_args__ = (
        UniqueConstraint("codigo_interno", "id_empresa", name="uq_codigo_interno_empresa"),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    codigo_interno: Optional[str] = Field(index=True, nullable=True)
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
    ubicacion: Optional[str] = Field(default="Sin definir")
    
    id_categoria: Optional[int] = Field(default=None, foreign_key="categorias.id")
    id_marca: Optional[int] = Field(default=None, foreign_key="marcas.id")

    categoria: Optional["Categoria"] = Relationship(back_populates="articulos")
    marca: Optional["Marca"] = Relationship(back_populates="articulos")
    empresa: "Empresa" = Relationship()
    proveedores: List["ArticuloProveedor"] = Relationship(back_populates="articulo")
   
    codigos: List["ArticuloCodigo"] = Relationship(
        back_populates="articulo",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    movimientos_stock: List["StockMovimiento"] = Relationship(back_populates="articulo")
    
    # === LA CORRECCIÓN CLAVE ESTÁ AQUÍ ===
    items_compra: List["CompraDetalle"] = Relationship(back_populates="articulo")
    items_venta: List["VentaDetalle"] = Relationship(back_populates="articulo")
    
    componentes_combo: List["ArticuloCombo"] = Relationship(back_populates="combo_padre", sa_relationship_kwargs={'primaryjoin': 'Articulo.id == ArticuloCombo.id_articulo_padre'})
    parte_de_combos: List["ArticuloCombo"] = Relationship(back_populates="componente_hijo", sa_relationship_kwargs={'primaryjoin': 'Articulo.id == ArticuloCombo.id_articulo_hijo'})
    # Relación con códigos de barras (viewonly=True para evitar conflictos en sincronización)
    codigos_barras: List["ArticuloCodigo"] = Relationship(back_populates="articulo", sa_relationship_kwargs={"viewonly": True})

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
    saldo_final_transferencias: Optional[float]
    saldo_final_bancario: Optional[float]
    saldo_final_efectivo: Optional[float]
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
    id_consumo_mesa_detalle: Optional[int] = Field(default=None, foreign_key="consumo_mesa_detalle.id")  # Nueva relación
    articulo: Articulo = Relationship(back_populates="movimientos_stock")
    usuario: Usuario = Relationship(back_populates="movimientos_de_stock")
    compra_detalle: Optional["CompraDetalle"] = Relationship(back_populates="movimiento_stock")
    venta_detalle: Optional["VentaDetalle"] = Relationship(back_populates="movimiento_stock")
    consumo_mesa_detalle: Optional["ConsumoMesaDetalle"] = Relationship(back_populates="movimiento_stock")  # Nueva relación
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
    descuento_total: float = Field(default=0.0)
    facturada: bool = Field(default=False, index=True)
    datos_factura: Optional[Dict[str, str]] = Field(default=None, sa_column=Column(JSON))
    estado: str = Field(default="COMPLETADA")
    id_venta_lote_padre: Optional[int] = Field(default=None, foreign_key="ventas.id", index=True)
    id_cliente: Optional[int] = Field(default=None, foreign_key="terceros.id")
    id_usuario: int = Field(foreign_key="usuarios.id")
    id_caja_sesion: int = Field(foreign_key="caja_sesiones.id")
    id_mesa: Optional[int] = Field(default=None, foreign_key="mesas.id")  # Nueva relación con mesa
    pago_separado: Optional[bool] = None
    detalles_pago_separado: Optional[str] = None
    tipo_comprobante_solicitado: Optional[str] = Field(
        default=None, 
        sa_column=Column(String(255)) # Longitud 255
    )
    cliente: Optional[Tercero] = Relationship(back_populates="ventas_recibidas")
    usuario: Usuario = Relationship(back_populates="ventas_realizadas")
    caja_sesion: CajaSesion = Relationship(back_populates="ventas")
    mesa: Optional["Mesa"] = Relationship(back_populates="ventas")  # Nueva relación
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
    cuit: str = Field(index=True)
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
    cuit: str = Field(index=True)
    id_empresa: int = Field(foreign_key="empresas.id", primary_key=True)
    link_google_sheets: Optional[str] = Field(default=None) # Enlace a Google Sheets para reportes
    # --- Tres enlaces públicos/visualizadores asociables a la empresa ---
    # Pueden usarse para dashboards, reportes externos, vistas embed, etc.
    link_visual_1: Optional[str] = Field(default=None)
    link_visual_2: Optional[str] = Field(default=None)
    link_visual_3: Optional[str] = Field(default=None)
    
    # --- Configuración de Apariencia ---
    nombre_negocio: Optional[str] # Nombre a mostrar en los tickets
    color_principal: str = Field(default="bg-sky-800")
    ruta_logo: Optional[str] = Field(default="front\public\default-logo.png")
    ruta_icono: Optional[str] = Field(default="front\public\favicon.ico")
    recargo_transferencia: float = Field(default=0.0)
    concepto_recargo_transferencia: str = Field(default="Recargo por Transferencia")
    recargo_banco: float = Field(default=0.0)
    concepto_recargo_banco: str = Field(default="Recargo por Pago con Banco")
    formato_comprobante_predeterminado: str = Field(default="ticket")
    # --- Configuración Fiscal (AFIP) ---
    afip_condicion_iva: Optional[str] = Field(default=None) # Ej: Monotributo, Responsable Inscripto
    afip_punto_venta_predeterminado: Optional[int] = Field(default=None)
    limite_consumidor_final: float = Field(default=211026.15)
    aclaraciones_legales: Optional[Dict[str, str]] = Field(
        default_factory=dict, 
        sa_column=Column(JSON)
    )
    # --- Datos de Contacto del Negocio ---
    direccion_negocio: Optional[str] = Field(default=None)
    telefono_negocio: Optional[str] = Field(default=None)
    mail_negocio: Optional[str] = Field(default=None)
    
    # --- Bóveda de Secretos ---
    # Aquí irían los secretos ENCRIPTADOS. El nombre del campo lo deja claro.
    afip_certificado_encrypted: Optional[str] = Field(default=None)
    afip_clave_privada_encrypted: Optional[str] = Field(default=None)
    
    # --- Versión de Catálogo ---
    catalogo_version: int = Field(default=0)
    
    
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




#ESTO ES PARA EL OTRO PROYECTO DE IMA, FACTURADOR
class FacturaElectronica(SQLModel, table=True):
    __tablename__ = "facturas_electronicas"

    id: Optional[int] = Field(default=None, primary_key=True)
    # --- CAMBIO AQUÍ: El índice se define de forma estándar en el Field ---
    ingreso_id: str = Field(index=True, description="El 'ID Ingresos' que vincula esta factura a la venta original.")

    cae: str = Field(max_length=14, unique=True, description="Código de Autorización Electrónico.")
    numero_comprobante: int = Field(sa_column=Column(BigInteger), description="Número de la factura (ej. 1234).")
    punto_venta: int = Field(description="Punto de venta (ej. 1, 2).")
    tipo_comprobante: int = Field(description="Código del tipo de comprobante (1=A, 6=B, 11=C).")
    
    # --- CAMBIO AQUÍ: El índice se mueve DENTRO del Column ---
    fecha_comprobante: date = Field(sa_column=Column(Date, index=True), description="Fecha de emisión del comprobante.")
    
    vencimiento_cae: date = Field(sa_column=Column(Date), description="Fecha de vencimiento del CAE.")
    resultado_afip: Optional[str] = Field(default=None, max_length=1, description="'A' (Aprobado), 'R' (Rechazado).")
    cuit_emisor: str = Field(max_length=11)
    tipo_doc_receptor: int = Field(description="Código del tipo de documento del receptor (80=CUIT, 96=DNI).")
    
    # --- CAMBIO AQUÍ: El índice se define de forma estándar en el Field (si no usas sa_column) ---
    nro_doc_receptor: str = Field(max_length=11, index=True)
    
    importe_total: Decimal = Field(sa_column=Column(DECIMAL(15, 2)))
    importe_neto: Decimal = Field(sa_column=Column(DECIMAL(15, 2)))
    importe_iva: Decimal = Field(sa_column=Column(DECIMAL(15, 2)))
    raw_response: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    
    created_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, server_default=func.now())
    )
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    )

# ===================================================================
# === MODELO DE MESA (PARA GESTIÓN DE MESAS EN RESTAURANTES)
# ===================================================================

class Mesa(SQLModel, table=True):
    __tablename__ = "mesas"
    __table_args__ = (UniqueConstraint("numero", "id_empresa", name="uq_numero_empresa_mesa"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    numero: int = Field(index=True)  # Número de la mesa (ej. 1, 2, 3)
    capacidad: int = Field(default=4)  # Número de personas que caben
    estado: str = Field(default="LIBRE")  # LIBRE, OCUPADA, RESERVADA
    activo: bool = Field(default=True)
    id_empresa: int = Field(foreign_key="empresas.id")
    empresa: "Empresa" = Relationship()
    # Relaciones con consumos y ventas
    consumos: List["ConsumoMesa"] = Relationship(back_populates="mesa")
    ventas: List["Venta"] = Relationship(back_populates="mesa")

# ===================================================================
# === MODELOS DE CONSUMO EN MESAS (PARA PEDIDOS ABIERTOS)
# ===================================================================

class ConsumoMesa(SQLModel, table=True):
    __tablename__ = "consumo_mesa"
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp_inicio: datetime = Field(default_factory=datetime.utcnow)
    timestamp_cierre: Optional[datetime] = None
    total: float = Field(default=0.0)
    propina: float = Field(default=0.0) # Monto calculado de propina
    porcentaje_propina: float = Field(default=0.0) # Porcentaje aplicado
    estado: str = Field(default="ABIERTO")  # ABIERTO, CERRADO, FACTURADO
    id_mesa: int = Field(foreign_key="mesas.id")
    id_usuario: int = Field(foreign_key="usuarios.id")
    id_empresa: int = Field(foreign_key="empresas.id")
    mesa: "Mesa" = Relationship(back_populates="consumos")
    usuario: "Usuario" = Relationship()
    empresa: "Empresa" = Relationship()
    detalles: List["ConsumoMesaDetalle"] = Relationship(back_populates="consumo")

class ConsumoMesaDetalle(SQLModel, table=True):
    __tablename__ = "consumo_mesa_detalle"
    id: Optional[int] = Field(default=None, primary_key=True)
    cantidad: float
    precio_unitario: float
    descuento_aplicado: float = Field(default=0.0)
    id_consumo_mesa: int = Field(foreign_key="consumo_mesa.id")
    id_articulo: int = Field(foreign_key="articulos.id")
    impreso: bool = Field(default=False)
    estado_cocina: str = Field(default="PENDIENTE") # PENDIENTE, LISTO, ENTREGADO
    observacion: Optional[str] = Field(default=None) # Nueva columna para observaciones
    consumo: "ConsumoMesa" = Relationship(back_populates="detalles")
    articulo: "Articulo" = Relationship()
    movimiento_stock: Optional[StockMovimiento] = Relationship(back_populates="consumo_mesa_detalle")

# ===================================================================
# === AUDITORÍA Y ÓRDENES
# ===================================================================

class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    accion: str
    entidad: str
    entidad_id: Optional[int] = None
    exito: bool = Field(default=True)
    detalles: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    id_usuario: int = Field(foreign_key="usuarios.id")
    id_empresa: int = Field(foreign_key="empresas.id")
    usuario: Usuario = Relationship()
    empresa: "Empresa" = Relationship()

class Orden(SQLModel, table=True):
    __tablename__ = "ordenes"
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tipo: str = Field(default="MESA")
    estado: str = Field(default="ABIERTA")
    total: float = Field(default=0.0)
    id_consumo_mesa: Optional[int] = Field(default=None, foreign_key="consumo_mesa.id")
    id_venta: Optional[int] = Field(default=None, foreign_key="ventas.id")
    numero_comprobante: Optional[str] = None
    id_usuario: int = Field(foreign_key="usuarios.id")
    id_empresa: int = Field(foreign_key="empresas.id")
    consumo_mesa: Optional["ConsumoMesa"] = Relationship()
    venta: Optional["Venta"] = Relationship()
    usuario: Usuario = Relationship()
    empresa: "Empresa" = Relationship()

class ImpresionSesion(SQLModel, table=True):
    __tablename__ = "impresion_sesion"
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp_inicio: datetime = Field(default_factory=datetime.utcnow)
    timestamp_cierre: Optional[datetime] = None
    estado: str = Field(default="ABIERTA")
    id_usuario: int = Field(foreign_key="usuarios.id")
    id_empresa: int = Field(foreign_key="empresas.id")
    usuario: Usuario = Relationship()
    empresa: "Empresa" = Relationship()
