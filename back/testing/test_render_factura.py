import os
import base64
from types import SimpleNamespace
from datetime import datetime, timedelta
from jinja2 import Environment, FileSystemLoader, select_autoescape
import re

# Helper to recursively convert dicts to objects for attribute access in templates
def to_ns(obj):
    if isinstance(obj, dict):
        return SimpleNamespace(**{k: to_ns(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return [to_ns(x) for x in obj]
    return obj

# Simple 1x1 PNG base64 (black pixel) placeholder for QR
QR_BASE64_PLACEHOLDER = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGMAAQAABQAB" \
    "J6kZ/wAAAABJRU5ErkJggg=="
)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TICKET_TEMPLATE = os.path.join(BASE_DIR, 'gestion', 'reportes', 'plantillas', 'ticket', 'factura.html')
PDF_TEMPLATE = os.path.join(BASE_DIR, 'gestion', 'reportes', 'plantillas', 'pdf', 'factura.html')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'render_output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Sample data
emisor = {
    'razon_social': 'MI EMPRESA S.A.',
    'domicilio': 'Av. Principal 123 - Ciudad',
    'condicion_iva': 'Responsable Inscripto',
    'cuit': '30711223345',
    'ingresos_brutos': 'CM 901-123456-7',
    'inicio_actividades': '01/01/2015',
    'punto_venta': 5,
    'logo_url': 'https://via.placeholder.com/150x60.png?text=LOGO'
}

receptor = {
    'nombre_razon_social': 'Cliente Ejemplo SRL',
    'cuit_o_dni': '30777888999',
    'condicion_iva': 'Responsable Inscripto',
    'domicilio': 'Calle Falsa 742'
}

items = [
    {
        'cantidad': 2,
        'descripcion': 'Producto A Ultra Largo Para Testear Corte',
        'precio_unitario': 1250.50,
        'descuento_especifico': 100.00,
        'descuento_especifico_por': 3.85
    },
    {
        'cantidad': 1,
        'descripcion': 'Servicio Técnico Especializado',
        'precio_unitario': 8000.00,
        'descuento_especifico': 0.0,
        'descuento_especifico_por': 0.0
    },
    {
        'cantidad': 3,
        'descripcion': 'Repuesto XYZ',
        'precio_unitario': 499.90,
        'descuento_especifico': 0.0,
        'descuento_especifico_por': 0.0
    }
]

subtotal_bruto = sum(i['cantidad'] * i['precio_unitario'] for i in items)
desc_item_total = sum(i.get('descuento_especifico', 0) for i in items)
subtotal_post_desc_items = subtotal_bruto - desc_item_total

descuento_general_por = 5.0
descuento_general = round(subtotal_post_desc_items * descuento_general_por / 100, 2)
subtotal_final = subtotal_post_desc_items - descuento_general

neto = round(subtotal_final / 1.21, 2)
iva = round(subtotal_final - neto, 2)

transaccion = {
    'items': items,
    'subtotal': round(subtotal_post_desc_items, 2),
    'descuento_general': descuento_general,
    'descuento_general_por': descuento_general_por,
    'total': round(subtotal_final, 2),
    'observaciones': 'Membrete Especial\nLinea 2 --- Observación interna para la venta. Gracias por su compra.',
    'pagos': [
        {'forma_pago': 'Efectivo', 'monto': round(subtotal_final * 0.4, 2)},
        {'forma_pago': 'Tarjeta Crédito', 'monto': round(subtotal_final * 0.6, 2)},
    ]
}

afip = {
    'tipo_comprobante_letra': 'B',
    'tipo_comprobante_nombre': 'FACTURA',
    'numero_comprobante': 1234,
    'cae': '71234567891234',
    'vencimiento_cae': (datetime.now() + timedelta(days=10)).strftime('%d/%m/%Y'),
    'neto': neto,
    'iva': iva,
    'qr_base64': QR_BASE64_PLACEHOLDER,
}

context = {
    'emisor': to_ns(emisor),
    'receptor': to_ns(receptor),
    'transaccion': to_ns(transaccion),
    'afip': to_ns(afip),
    'fecha_emision': datetime.now(),
}

# Jinja2 environment
loader = FileSystemLoader(searchpath=os.path.join(BASE_DIR, 'gestion', 'reportes', 'plantillas'))
env = Environment(loader=loader, autoescape=select_autoescape(['html']))

# Custom date filter (since 'date' filter may not be registered by default in plain Jinja2)
def date_filter(value, fmt='%d/%m/%Y'):
    if value is None:
        return ''
    if isinstance(value, (int, float)):
        from datetime import datetime as _dt
        value = _dt.fromtimestamp(value)
    try:
        return value.strftime(fmt)
    except Exception:
        return str(value)

env.filters['date'] = date_filter

# Map relative paths for env.get_template
# ticket template path inside loader root: 'ticket/factura.html'
# pdf template path inside loader root: 'pdf/factura.html'

outputs = [
    ('ticket/factura.html', 'ejemplo_ticket.html'),
    ('pdf/factura.html', 'ejemplo_factura_A4.html'),
]

VAR_EXCLUDE_PREFIXES = {"loop", "cycler", "namespace", "super"}

def extract_variable_chains(template_source: str):
    """Extrae expresiones de variables Jinja simples ({{ ... }}) y condiciones {% if ... %}.
    Devuelve un set de cadenas como 'emisor.razon_social'. Ignora filtros y llamadas."""
    vars_found = set()
    # {{ ... }} blocks
    for m in re.findall(r"{{\s*(.*?)\s*}}", template_source):
        expr = m.split('|')[0].strip()
        if not expr:
            continue
        # Saltar literales o expresiones complejas
        if any(ch in expr for ch in '()'):  # llamada a función u operación
            continue
        # Separar por espacios (tomar primera parte si hay operaciones)
        expr = expr.split()[0]
        if expr.startswith(('{', '[')):
            continue
        vars_found.add(expr)
    # {% if ... %} and {% for ... %}
    for m in re.findall(r"{%\s*if\s+(.*?)%}", template_source):
        tokens = re.split(r"\s+|==|!=|>=|<=|>|<|and|or|not|in", m)
        for t in tokens:
            t = t.strip()
            if not t or t.isdigit() or t in ('True','False','None'):
                continue
            # Saltar tokens que contienen caracteres que implican operaciones complejas
            if any(ch in t for ch in ['(', ')', '"', "'", '[', ']']):
                continue
            if t in VAR_EXCLUDE_PREFIXES:
                continue
            if '.' in t:
                vars_found.add(t)
    return vars_found

def validate_chain(chain: str, ctx: dict):
    """Verifica si la cadena de acceso existe en el contexto navegando atributos/keys."""
    root_name = chain.split('.')[0]
    if root_name not in ctx:
        return False, f"Raíz '{root_name}' ausente"
    current = ctx[root_name]
    for attr in chain.split('.')[1:]:
        if current is None:
            return False, f"'{chain}': valor intermedio None antes de '{attr}'"
        # dict o namespace o objeto genérico
        if isinstance(current, dict):
            if attr not in current:
                return False, f"'{chain}': key '{attr}' no encontrada"
            current = current[attr]
        else:
            if not hasattr(current, attr):
                return False, f"'{chain}': atributo '{attr}' no encontrado"
            current = getattr(current, attr)
    return True, 'OK'

def run_variable_audit():
    print('\n=== Auditoría de variables de plantillas ===')
    all_ok = True
    ctx_raw = {
        'emisor': emisor,
        'receptor': receptor,
        'transaccion': transaccion,
        'afip': afip,
        'fecha_emision': context['fecha_emision'],
    }
    for template_rel, _ in outputs:
        path = os.path.join(BASE_DIR, 'gestion', 'reportes', 'plantillas', template_rel)
        with open(path, 'r', encoding='utf-8') as f:
            source = f.read()
        chains = sorted(extract_variable_chains(source))
        print(f"\nPlantilla: {template_rel}")
        missing = []
        for c in chains:
            ok, detail = validate_chain(c, ctx_raw)
            status = 'OK' if ok else 'FALTA'
            if not ok:
                all_ok = False
                missing.append((c, detail))
            print(f"  {c:35} -> {status}")
        if missing:
            print('  -- Detalles faltantes --')
            for c, d in missing:
                print(f"    {c}: {d}")
        else:
            print('  Todas las variables resueltas correctamente.')
    print('\nResultado global:', 'SIN FALTANTES' if all_ok else 'HAY VARIABLES FALTANTES')
    return all_ok

def render_all():
    for template_name, outfile in outputs:
        tpl = env.get_template(template_name)
        html = tpl.render(**context)
        out_path = os.path.join(OUTPUT_DIR, outfile)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"Generado: {out_path}")

if __name__ == '__main__':
    render_all()
    run_variable_audit()
    print('\nListo. Abre los archivos HTML generados en un navegador para revisar el formato.')
