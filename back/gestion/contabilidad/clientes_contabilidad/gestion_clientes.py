# gestion/contabilidad/clientes_contabilidad/gestion_clientes.py
from utils.sheets_google_handler import GoogleSheetsHandler
from config import SHEET_NAME_CLIENTES
from datetime import datetime

# Similar a proveedores_compra.py, pero para clientes
def generar_id_cliente(g_handler):
    registros = g_handler.get_all_records(SHEET_NAME_CLIENTES)
    if not registros: return "CLI001"
    max_id_num = 0
    # ... (lógica similar a generar_id_proveedor) ...
    for reg in registros:
        id_cli = reg.get("ID_Cliente", "")
        if id_cli.startswith("CLI") and id_cli[3:].isdigit():
            try:
                num = int(id_cli[3:])
                if num > max_id_num: max_id_num = num
            except ValueError: continue
    return f"CLI{(max_id_num + 1):03d}"

def agregar_cliente(nombre_o_razon: str, tipo_doc: str, num_doc: str, cond_iva: str,
                    direccion: str = "", telefono: str = "", email: str = "",
                    permite_cc: bool = False, limite_credito: float = 0.0):
    try:
        g_handler = GoogleSheetsHandler() # Asumimos que está configurado
        # ... (validaciones)
        if not nombre_o_razon or not num_doc or not cond_iva:
            return {"status": "error", "message": "Nombre, Nro Documento y Condición IVA son obligatorios."}

        # Verificar si ya existe por Tipo y Nro Documento
        clientes = g_handler.get_all_records(SHEET_NAME_CLIENTES)
        for cli in clientes:
            if cli.get('NumeroDocumento') == num_doc and cli.get('TipoDocumento') == tipo_doc and cli.get('Activo', 'SI') == 'SI':
                return {"status": "error", "message": f"Ya existe un cliente activo con {tipo_doc} {num_doc}."}

        id_cliente = generar_id_cliente(g_handler)
        data_row = [
            id_cliente, nombre_o_razon, tipo_doc, num_doc, cond_iva, direccion, telefono, email,
            "SI" if permite_cc else "NO",
            limite_credito if permite_cc else 0.0,
            0.0, # SaldoCuentaCorriente inicial
            "SI" # Activo
        ]
        # Columnas: ID_Cliente, NombreApellido, TipoDocumento, NumeroDocumento, CondicionIVA, Direccion,
        #           Telefono, Email, PermiteCuentaCorriente, LimiteCredito, SaldoCuentaCorriente, Activo
        if g_handler.append_row(SHEET_NAME_CLIENTES, data_row):
            return {"status": "success", "id_cliente": id_cliente, "message": "Cliente agregado."}
        else:
            return {"status": "error", "message": "Error al guardar cliente."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def obtener_cliente_por_id(id_cliente: str):
    try:
        g_handler = GoogleSheetsHandler()
        clientes = g_handler.get_all_records(SHEET_NAME_CLIENTES)
        for cli in clientes:
            if cli.get('ID_Cliente') == id_cliente and cli.get('Activo', 'SI') == 'SI':
                # Convertir Saldo y Limite a float
                cli['SaldoCuentaCorriente'] = float(str(cli.get('SaldoCuentaCorriente', '0')).replace(',', '.'))
                cli['LimiteCredito'] = float(str(cli.get('LimiteCredito', '0')).replace(',', '.'))
                return cli
        return None
    except Exception as e:
        print(f"Error obteniendo cliente {id_cliente}: {e}")
        return None

def buscar_clientes(termino: str, campo: str = "NombreApellido"):
    # Similar a buscar_proveedor
    try:
        g_handler = GoogleSheetsHandler()
        clientes = g_handler.get_all_records(SHEET_NAME_CLIENTES)
        resultados = []
        for cli in clientes:
            if cli.get('Activo','SI') == 'SI' and termino.lower() in str(cli.get(campo, "")).lower():
                resultados.append(cli)
        return resultados
    except Exception: return []

