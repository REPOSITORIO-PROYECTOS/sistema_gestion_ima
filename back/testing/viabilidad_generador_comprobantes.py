"""Prueba de viabilidad del generador de comprobantes.
Valida el enriquecimiento de datos AFIP y de transacción sin depender de WeasyPrint.

Se prueban escenarios:
1. AFIP parcial (solo tipo y total) -> completa letra, nombre, neto e iva.
2. Nota de crédito (tipo 8) -> nombre "NOTA DE CRÉDITO".
3. Transacción sin descuentos ni subtotal -> calcula subtotal y defaults.
4. Items sin campos de descuento -> agrega campos con 0.

Si todo pasa, imprime 'VIABILIDAD OK'.
"""
from types import SimpleNamespace
from copy import deepcopy
import sys, os

# Ajustar sys.path para poder importar el paquete 'back'
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Importar funciones internas del generador
from back.gestion.reportes.generador_comprobantes import _afip_build_or_enrich, _enrich_transaccion


def as_ns(d):
    return SimpleNamespace(**d)


def assert_close(a, b, tol=0.02, msg=""):
    if abs(a - b) > tol:
        raise AssertionError(msg or f"Valores no cercanos: {a} vs {b}")


def escenario_afip_parcial():
    transaccion = as_ns({
        'total': 121.00,
        'items': [],
        'pagos': []
    })
    afip = {'tipo_afip': 6, 'total': 121.00}  # Factura B sin neto/iva/letra/nombre
    setattr(transaccion, 'afip', afip)

    enr = _afip_build_or_enrich(transaccion, qr_base64=None)
    assert enr['tipo_comprobante_letra'] == 'B', 'Letra esperada B'
    assert enr['tipo_comprobante_nombre'] == 'FACTURA', 'Nombre FACTURA'
    assert 'neto' in enr and 'iva' in enr, 'Debe calcular neto e iva'
    assert_close(enr['neto'], 100.0, msg='Neto debería ~100')
    assert_close(enr['iva'], 21.0, msg='IVA debería ~21')


def escenario_nota_credito():
    transaccion = as_ns({'total': 242.0, 'items': [], 'pagos': []})
    afip = {'tipo_afip': 8, 'total': 242.0}  # Nota de crédito B
    setattr(transaccion, 'afip', afip)
    enr = _afip_build_or_enrich(transaccion, qr_base64='FAKEQR')
    assert enr['tipo_comprobante_letra'] == 'B', 'Letra B para tipo 8'
    assert enr['tipo_comprobante_nombre'] == 'NOTA DE CRÉDITO'
    assert enr['qr_base64'] == 'FAKEQR'


def escenario_transaccion_defaults():
    trans = as_ns({
        'total': 950.0,
        'descuento_general': 50.0,  # subtotal debería ser 1000
        'items': [
            {'cantidad': 1, 'descripcion': 'Prod X', 'precio_unitario': 500.0},
            {'cantidad': 1, 'descripcion': 'Prod Y', 'precio_unitario': 500.0},
        ],
        # pagos omitido a propósito
    })
    enriched = _enrich_transaccion(trans)
    assert enriched.subtotal == 1000.0, 'Subtotal esperado 1000'
    assert isinstance(enriched.pagos, list) and len(enriched.pagos) == 0, 'Pagos debe ser lista vacía'
    for it in enriched.items:
        assert 'descuento_especifico' in it and it['descuento_especifico'] == 0.0
        assert 'descuento_especifico_por' in it and it['descuento_especifico_por'] == 0.0


def run_all():
    escenario_afip_parcial()
    escenario_nota_credito()
    escenario_transaccion_defaults()
    print('VIABILIDAD OK - Enriquecimiento consistente.')

if __name__ == '__main__':
    run_all()
