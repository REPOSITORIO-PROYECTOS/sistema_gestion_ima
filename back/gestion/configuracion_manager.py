# back/gestion/configuracion_manager.py

RAZONES_DE_EGRESO_COMUNES = [
    "Pago a proveedor menor",
    "Pago de delivery / mensajería",
    "Compra de artículos de limpieza",
    "Compra de insumos de oficina",
    "Adelanto de sueldo",
    "Retiro de socio",
    "Otros gastos"
]

def obtener_razones_de_egreso():
    """Devuelve la lista de razones de egreso predefinidas."""
    return RAZONES_DE_EGRESO_COMUNES