"""Definición de pantallas a capturar y textos de la guía de uso."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class AccionPrevia:
    """Acción opcional antes de la captura (tab, clic, espera)."""

    tipo: str  # "click_text" | "wait_ms" | "wait_selector"
    valor: str = ""


@dataclass(frozen=True)
class Pantalla:
    id: str
    archivo: str
    ruta: str
    titulo: str
    para_que_sirve: str
    procedimiento: List[str]
    roles: List[str] = field(default_factory=lambda: ["Admin", "Gerente", "Cajero"])
    requiere_auth: bool = True
    full_page: bool = True
    esperar_selector: Optional[str] = None
    acciones_previas: List[AccionPrevia] = field(default_factory=list)
    notas: Optional[str] = None


PANTALLAS: List[Pantalla] = [
    Pantalla(
        id="login",
        archivo="01_login.png",
        ruta="/",
        titulo="Inicio de sesión",
        para_que_sirve=(
            "Pantalla de acceso al sistema. Cada usuario ingresa con su nombre de usuario "
            "y contraseña asignados por el administrador de la empresa."
        ),
        procedimiento=[
            "Abrir la URL del sistema en el navegador.",
            "Ingresar usuario y contraseña.",
            "Pulsar «Ingresar». El sistema carga la empresa, el catálogo y redirige al panel principal.",
        ],
        roles=["Todos"],
        requiere_auth=False,
        esperar_selector="form.form-login",
    ),
    Pantalla(
        id="dashboard",
        archivo="02_dashboard.png",
        ruta="/dashboard",
        titulo="Panel principal",
        para_que_sirve=(
            "Página de bienvenida tras el login. Desde la barra superior se accede "
            "a Ventas, Mesas, Cocina, Contabilidad y Stock según el rol del usuario."
        ),
        procedimiento=[
            "Tras iniciar sesión, llegás acá automáticamente.",
            "Usá el menú superior para ir a cada módulo.",
            "En el menú de usuario (arriba a la derecha) están Gestión de Usuarios y Gestión de Negocio.",
        ],
        esperar_selector="#main-content",
    ),
    Pantalla(
        id="ventas",
        archivo="03_ventas.png",
        ruta="/dashboard/ventas",
        titulo="Ventas (POS / Caja)",
        para_que_sirve=(
            "Punto de venta principal: registrar ventas de mostrador, aplicar descuentos, "
            "elegir método de pago y emitir comprobantes. Requiere caja abierta para operar."
        ),
        procedimiento=[
            "Verificar que la caja esté abierta (botón «Abrir caja» si está cerrada).",
            "Buscar productos por código o nombre y agregarlos al ticket.",
            "Ajustar cantidades, descuentos y método de pago.",
            "Confirmar la venta y emitir ticket/factura según corresponda.",
            "Para egresos de caja, usar el botón de egreso disponible en esta pantalla.",
        ],
        roles=["Admin", "Cajero", "Gerente"],
        esperar_selector="#main-content",
    ),
    Pantalla(
        id="mesas",
        archivo="04_mesas.png",
        ruta="/dashboard/mesas",
        titulo="Mesas y consumos",
        para_que_sirve=(
            "Gestión de salón: mesas, pedidos abiertos, unión de mesas, impresión de comandas "
            "y tickets. Solo visible si la empresa tiene el módulo de mesas habilitado."
        ),
        procedimiento=[
            "Abrir caja si aún no está abierta.",
            "Seleccionar una mesa libre u ocupada.",
            "Cargar productos al consumo, modificar cantidades o anular ítems.",
            "Imprimir comanda para cocina/barra si corresponde.",
            "Cerrar consumo y derivar a ventas/facturación cuando el cliente paga.",
            "Opcional: unir mesas seleccionando varias y usando «Unir mesas».",
        ],
        roles=["Admin", "Cajero", "Gerente"],
        notas="Si no aparece en el menú, el módulo de mesas no está habilitado para la empresa.",
    ),
    Pantalla(
        id="cocina",
        archivo="05_cocina.png",
        ruta="/dashboard/cocina",
        titulo="Cocina (monitor de pedidos)",
        para_que_sirve=(
            "Monitor en tiempo real de ítems pendientes de preparación enviados desde Mesas. "
            "Permite marcar estados (pendiente → en preparación → listo)."
        ),
        procedimiento=[
            "Dejar esta pantalla abierta en una tablet o PC de cocina.",
            "Los pedidos llegan automáticamente al cargarse en una mesa.",
            "Marcar cada ítem según avance: «En preparación» y luego «Listo».",
            "La pantalla se actualiza sola cada pocos segundos.",
        ],
        roles=["Admin", "Cajero", "Gerente"],
        notas="Requiere módulo de mesas habilitado.",
    ),
    Pantalla(
        id="contabilidad_movimientos",
        archivo="06_contabilidad_movimientos.png",
        ruta="/dashboard/contabilidad",
        titulo="Contabilidad — Movimientos",
        para_que_sirve=(
            "Historial de movimientos de caja: ventas, ingresos, egresos y otros registros "
            "contables vinculados a la operación diaria."
        ),
        procedimiento=[
            "Entrar a Contabilidad desde el menú principal.",
            "Revisar la tabla de movimientos (filtros y columnas según permisos).",
            "Usar los datos para conciliación diaria o auditoría interna.",
        ],
        roles=["Admin", "Gerente"],
        esperar_selector="main",
    ),
    Pantalla(
        id="contabilidad_proveedores",
        archivo="07_contabilidad_proveedores.png",
        ruta="/dashboard/contabilidad/proveedores",
        titulo="Contabilidad — Proveedores",
        para_que_sirve=(
            "Alta y consulta de proveedores, configuración de plantillas de importación Excel "
            "y carga de listas de precios/costos desde archivos del proveedor."
        ),
        procedimiento=[
            "Ir a Contabilidad → Proveedores.",
            "Crear o editar un proveedor con sus datos fiscales.",
            "Configurar la plantilla de mapeo de columnas del Excel del proveedor.",
            "Subir el Excel y revisar la previsualización antes de confirmar cambios de costos.",
        ],
        roles=["Admin", "Gerente"],
    ),
    Pantalla(
        id="contabilidad_clientes",
        archivo="08_contabilidad_clientes.png",
        ruta="/dashboard/contabilidad/clientes",
        titulo="Contabilidad — Clientes",
        para_que_sirve=(
            "Gestión de clientes con cuenta corriente: datos fiscales, saldos y movimientos "
            "asociados a ventas a crédito."
        ),
        procedimiento=[
            "Ir a Contabilidad → Clientes.",
            "Alta o edición de clientes (CUIT, razón social, condición IVA).",
            "Consultar saldo y movimientos desde el detalle de cada cliente.",
        ],
        roles=["Admin", "Gerente"],
    ),
    Pantalla(
        id="contabilidad_arqueo",
        archivo="09_contabilidad_arqueo.png",
        ruta="/dashboard/contabilidad/arqueo",
        titulo="Contabilidad — Arqueo de caja",
        para_que_sirve=(
            "Control de cierre de caja: comparar lo declarado vs. lo calculado por el sistema, "
            "incluyendo desglose por medio de pago."
        ),
        procedimiento=[
            "Al final del turno, ir a Contabilidad → Arqueo de Caja.",
            "Seleccionar la sesión de caja a revisar.",
            "Comparar totales declarados con los calculados.",
            "Registrar observaciones si hay diferencias y archivar el comprobante de cierre.",
        ],
        roles=["Admin", "Gerente"],
    ),
    Pantalla(
        id="stock",
        archivo="10_stock.png",
        ruta="/dashboard/stock",
        titulo="Stock",
        para_que_sirve=(
            "Consulta del catálogo y niveles de stock. En modo especial (sin Google Sheets) "
            "permite cargar productos, ingresar stock, subir precios e importar/exportar CSV."
        ),
        procedimiento=[
            "Ir a Stock desde el menú principal.",
            "Modo Sheets: la tabla refleja el catálogo sincronizado (solo lectura operativa).",
            "Modo especial: usar las pestañas para alta manual, ingreso de stock, suba de precios o importación CSV.",
            "Para importación masiva: preparar CSV con columnas Codigo, Producto, Precio, Stock, etc.",
        ],
        roles=["Admin", "Gerente"],
        full_page=False,
        esperar_selector="main, #main-content, [role='tablist']",
    ),
    Pantalla(
        id="gestion_usuarios",
        archivo="11_gestion_usuarios.png",
        ruta="/dashboard/gestion_usuarios",
        titulo="Gestión de usuarios",
        para_que_sirve=(
            "Administración de usuarios de la empresa: altas, roles (Admin, Cajero, Gerente), "
            "activación/desactivación y reseteo de accesos."
        ),
        procedimiento=[
            "Menú usuario (arriba a la derecha) → Gestión de Usuarios.",
            "Crear usuario con rol adecuado.",
            "Editar o desactivar usuarios que ya no operan el sistema.",
        ],
        roles=["Admin", "Soporte"],
    ),
    Pantalla(
        id="gestion_negocio_fiscales",
        archivo="12_gestion_negocio_fiscales.png",
        ruta="/dashboard/gestion_de_negocio",
        titulo="Gestión de negocio — Datos fiscales",
        para_que_sirve=(
            "Configuración de la empresa: nombre, CUIT, domicilio, condición IVA, "
            "punto de venta AFIP y datos que aparecen en comprobantes."
        ),
        procedimiento=[
            "Menú usuario → Gestión de Negocio.",
            "Pestaña «Negocio y Fiscales»: completar o actualizar datos legales.",
            "Guardar cambios antes de emitir comprobantes fiscales.",
        ],
        roles=["Admin", "Soporte"],
        acciones_previas=[AccionPrevia("click_text", "Negocio y Fiscales")],
    ),
    Pantalla(
        id="gestion_negocio_personalizacion",
        archivo="13_gestion_negocio_personalizacion.png",
        ruta="/dashboard/gestion_de_negocio",
        titulo="Gestión de negocio — Personalización",
        para_que_sirve=(
            "Apariencia del sistema: colores, logo, iconos y textos legales "
            "que se muestran en tickets y comprobantes."
        ),
        procedimiento=[
            "Gestión de Negocio → pestaña «Personalización».",
            "Subir logo e icono en formatos indicados.",
            "Ajustar color principal y aclaraciones legales por tipo de comprobante.",
            "Guardar y verificar en una venta de prueba.",
        ],
        roles=["Admin", "Soporte"],
        acciones_previas=[AccionPrevia("click_text", "Personalización")],
    ),
    Pantalla(
        id="gestion_negocio_integraciones",
        archivo="14_gestion_negocio_integraciones.png",
        ruta="/dashboard/gestion_de_negocio",
        titulo="Gestión de negocio — Integraciones",
        para_que_sirve=(
            "Vinculación con Google Sheets para sincronizar catálogo/stock, "
            "enlaces personalizados del menú y otras integraciones operativas."
        ),
        procedimiento=[
            "Gestión de Negocio → pestaña «Integraciones».",
            "Pegar el link de Google Sheets si la empresa usa sync automática.",
            "Configurar enlaces rápidos visibles en la barra de navegación.",
            "Guardar y ejecutar una sincronización de prueba si aplica.",
        ],
        roles=["Admin", "Soporte"],
        acciones_previas=[AccionPrevia("click_text", "Integraciones")],
    ),
    Pantalla(
        id="panel_usuario",
        archivo="15_panel_usuario.png",
        ruta="/dashboard/panel_usuario",
        titulo="Panel de usuario",
        para_que_sirve=(
            "Vista personal del usuario logueado: datos de perfil y accesos rápidos "
            "según permisos."
        ),
        procedimiento=[
            "Acceder desde el menú de usuario si está disponible.",
            "Revisar datos personales y opciones de cuenta.",
        ],
        roles=["Admin", "Cajero", "Gerente"],
    ),
]
