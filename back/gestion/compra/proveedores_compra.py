# gestion/compra/proveedores_compra.py

from back.utils.sheets_google_handler import GoogleSheetsHandler
from back.config import SHEET_NAME_TERCEROS
from datetime import datetime
import gspread

def generar_id_proveedor(g_handler):
    """Genera un nuevo ID de proveedor secuencial (ej. PROV001, PROV002)."""
    registros = g_handler.get_all_records(SHEET_NAME_TERCEROS)
    if not registros:
        return "PROV001"
    
    max_id_num = 0
    for reg in registros:
        id_prov = reg.get("ID_Proveedor", "")
        if id_prov.startswith("PROV") and id_prov[4:].isdigit():
            try:
                num = int(id_prov[4:])
                if num > max_id_num:
                    max_id_num = num
            except ValueError:
                continue # Ignorar IDs mal formados
    return f"PROV{(max_id_num + 1):03d}"


def agregar_proveedor(razon_social: str, cuit: str, direccion: str = "", telefono: str = "", email: str = "", 
                      persona_contacto: str = "", condiciones_pago: str = "", observaciones: str = ""):
    """Agrega un nuevo proveedor a la hoja de cálculo."""
    try:
        g_handler = GoogleSheetsHandler()
        if not g_handler.client:
            return {"status": "error", "message": "No se pudo conectar a Google Sheets."}

        # Validaciones básicas
        if not razon_social or not cuit:
            return {"status": "error", "message": "Razón Social y CUIT son obligatorios."}

        # Verificar si el CUIT ya existe (opcional, pero recomendado)
        proveedores = g_handler.get_all_records(SHEET_NAME_TERCEROS)
        for prov in proveedores:
            if prov.get('CUIT') == cuit and prov.get('Activo', 'SI').upper() == 'SI':
                return {"status": "error", "message": f"Ya existe un proveedor activo con CUIT {cuit}."}

        id_proveedor = generar_id_proveedor(g_handler)
        fecha_alta = datetime.now().strftime("%Y-%m-%d")

        data_row = [
            id_proveedor,
            razon_social,
            cuit,
            direccion,
            telefono,
            email,
            persona_contacto,
            condiciones_pago,
            observaciones,
            "SI", # Activo por defecto
            fecha_alta
        ]
        # Columnas esperadas: ID_Proveedor, RazonSocial, CUIT, Direccion, Telefono, Email,
        #                     PersonaContacto, CondicionesPago, Observaciones, Activo, FechaAlta

        if g_handler.append_row(SHEET_NAME_TERCEROS, data_row):
            print(f"Proveedor '{razon_social}' agregado con ID {id_proveedor}.")
            return {"status": "success", "id_proveedor": id_proveedor, "message": "Proveedor agregado exitosamente."}
        else:
            return {"status": "error", "message": "Error al guardar el proveedor en Google Sheets."}

    except Exception as e:
        print(f"Error en agregar_proveedor: {e}")
        return {"status": "error", "message": str(e)}


def buscar_proveedor(termino_busqueda: str, campo_busqueda: str = "RazonSocial"):
    """Busca proveedores por RazonSocial, CUIT o ID_Proveedor."""
    try:
        g_handler = GoogleSheetsHandler()
        if not g_handler.client:
            return [] # O un dict de error

        proveedores = g_handler.get_all_records(SHEET_NAME_TERCEROS)
        resultados = []

        if not termino_busqueda: # Devolver todos si no hay término
            return [p for p in proveedores if p.get('Activo', 'SI').upper() == 'SI']


        for prov in proveedores:
            if prov.get('Activo', 'SI').upper() != 'SI': # Solo buscar en activos
                continue

            valor_campo = str(prov.get(campo_busqueda, "")).lower()
            if termino_busqueda.lower() in valor_campo:
                resultados.append(prov)
        
        return resultados

    except Exception as e:
        print(f"Error en buscar_proveedor: {e}")
        return []


def obtener_proveedor_por_id(id_proveedor: str):
    """Obtiene un proveedor específico por su ID."""
    proveedores = buscar_proveedor(id_proveedor, "ID_Proveedor")
    if proveedores:
        return proveedores[0] # ID es único
    return None


def modificar_proveedor(id_proveedor: str, nuevos_datos: dict):
    """Modifica los datos de un proveedor existente."""
    try:
        g_handler = GoogleSheetsHandler()
        if not g_handler.client:
            return {"status": "error", "message": "No se pudo conectar a Google Sheets."}

        ws = g_handler.get_worksheet(SHEET_NAME_TERCEROS)
        if not ws:
            return {"status": "error", "message": f"Hoja '{SHEET_NAME_TERCEROS}' no encontrada."}

        try:
            # Asumiendo que ID_Proveedor es la columna 1
            cell = ws.find(id_proveedor, in_column=1)
        except gspread.exceptions.CellNotFound:
            return {"status": "error", "message": f"Proveedor con ID {id_proveedor} no encontrado."}
        
        if cell:
            row_index = cell.row
            # Actualizar las celdas correspondientes.
            # Necesitas mapear los nombres de `nuevos_datos.keys()` a los índices de columna.
            # O, si la hoja tiene encabezados, obtenerlos y usarlos.
            headers = ws.row_values(1) # Obtener encabezados de la fila 1
            
            updates_batch = []
            for key, value in nuevos_datos.items():
                if key in headers:
                    col_index = headers.index(key) + 1 # gspread es base 1
                    updates_batch.append({
                        'range': gspread.utils.rowcol_to_a1(row_index, col_index),
                        'values': [[value]],
                    })
            
            if updates_batch:
                ws.batch_update(updates_batch)
                print(f"Proveedor {id_proveedor} actualizado.")
                return {"status": "success", "message": "Proveedor actualizado exitosamente."}
            else:
                return {"status": "info", "message": "No hay datos válidos para actualizar."}
        else: # Ya cubierto por CellNotFound
            return {"status": "error", "message": f"Proveedor con ID {id_proveedor} no encontrado (inesperado)."}
            
    except Exception as e:
        print(f"Error en modificar_proveedor: {e}")
        return {"status": "error", "message": str(e)}


def cambiar_estado_proveedor(id_proveedor: str, activo: bool):
    """Activa o desactiva un proveedor."""
    estado_str = "SI" if activo else "NO"
    return modificar_proveedor(id_proveedor, {"Activo": estado_str})