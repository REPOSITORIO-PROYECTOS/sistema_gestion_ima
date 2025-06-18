# gestion/fiscal/afip_mappers.py

class AfipMappingError(Exception): # Excepción específica
    pass

def map_tipo_comprobante_afip(tipo_factura_sistema: str) -> int:
    """Mapea el tipo de factura de tu sistema al código numérico de AFIP para WSFEV1."""
    tipo_map = {
        "FACTURA_A": 1, "A": 1, "FACTURA_B": 6, "B": 6, "FACTURA_C": 11, "C": 11,
        "NOTA_CREDITO_A": 3, "NCA": 3, "NOTA_CREDITO_B": 8, "NCB": 8, "NOTA_CREDITO_C": 13, "NCC": 13,
        "NOTA_DEBITO_A": 2, "NDA": 2, "NOTA_DEBITO_B": 7, "NDB": 7, "NOTA_DEBITO_C": 12, "NDC": 12,
    }
    # Normalizar entrada: a mayúsculas y reemplazar espacios por guiones bajos
    key = str(tipo_factura_sistema).upper().replace(" ", "_")
    mapped_value = tipo_map.get(key)
    
    if mapped_value is None:
        raise AfipMappingError(f"Tipo de comprobante del sistema no mapeado a AFIP: '{tipo_factura_sistema}' (Normalizado: '{key}')")
    return mapped_value

def map_tipo_doc_receptor_afip(tipo_doc_sistema: str) -> int:
    """Mapea el tipo de documento del receptor al código de AFIP."""
    tipo_map = {
        "CUIT": 80, "CUIL": 86, "DNI": 96, "CONSUMIDOR_FINAL": 99, "PASAPORTE": 94, 
        "CDI": 87, "LE": 0, "LC": 1, "CI_EXTRANJERA": 91, "OTRO": 99 # Default a "Otro" si no es CF
    }
    key = str(tipo_doc_sistema).upper()
    mapped_value = tipo_map.get(key)
    
    if mapped_value is None:
        print(f"ADVERTENCIA (afip_mappers): Tipo de documento receptor '{tipo_doc_sistema}' no mapeado, usando Consumidor Final (99).")
        return 99 # Default a Consumidor Final
    return mapped_value

def map_codigo_iva_afip(tasa_iva_sistema) -> int:
    """Mapea la tasa de IVA al código de AFIP."""
    try:
        tasa_iva = float(tasa_iva_sistema)
        if tasa_iva == 0: return 3
        if tasa_iva == 10.5: return 4
        if tasa_iva == 21: return 5
        if tasa_iva == 27: return 6
        if tasa_iva == 5: return 8
        if tasa_iva == 2.5: return 9
    except (ValueError, TypeError):
        raise AfipMappingError(f"Tasa de IVA del sistema no es un número válido: '{tasa_iva_sistema}'")
    raise AfipMappingError(f"Tasa de IVA del sistema no mapeada a código AFIP: '{tasa_iva_sistema}'")

def map_concepto_afip(concepto_sistema: str or int) -> int:
    """Mapea el concepto de la operación (Productos, Servicios, Ambos) al código AFIP."""
    # 1: Productos, 2: Servicios, 3: Productos y Servicios
    if isinstance(concepto_sistema, int) and concepto_sistema in [1, 2, 3]:
        return concepto_sistema
    
    key = str(concepto_sistema).upper()
    if key in ["PRODUCTOS", "PRODUCTO", "1"]: return 1
    if key in ["SERVICIOS", "SERVICIO", "2"]: return 2
    if key in ["PRODUCTOS_Y_SERVICIOS", "AMBOS", "3"]: return 3
    
    print(f"ADVERTENCIA (afip_mappers): Concepto '{concepto_sistema}' no mapeado, usando Productos (1).")
    return 1 # Default a Productos si no se reconoce