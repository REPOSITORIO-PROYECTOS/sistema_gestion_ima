# gestion/caja/cliente_publico.py
# Este módulo podría usarse para seleccionar un cliente o usar "Público General".
# Eventualmente, podría interactuar con el módulo de Contabilidad/Clientes.

#ACA TENGO QUE TOMAR LOS DATOS DE LA TABLA CLIENTE , DEVULEVO EL NOMBRE DEL CLIENTE

from typing import Dict, List
from back.utils.sheets_google_handler import GoogleSheetsHandler

caller = GoogleSheetsHandler()

def obtener_cliente_para_venta(id_cliente_o_nombre=None):  #NOTA DE LUCAS: usemos el CUIT del cliente, en el caso que haya 
                                                            #varios nombres con el mismo CUIT, los envio todos en forma de lista
    """
    Determina el cliente para una venta.
    Si no se provee id_cliente_o_nombre, se asume "Público General".
    Más adelante, podría buscar en una base de datos/hoja de clientes.
    """
    if id_cliente_o_nombre:
        datos_clientes = caller.cargar_clientes()
        resultados = []
        for cliente in datos_clientes:
            if str(cliente.get("CUIT-CUIL", "")).strip() == str(id_cliente_o_nombre).strip():
              nombre = cliente.get("nombre-usuario")
              resultados.append(nombre)
        if (len(resultados) == 1):
        
            return str(nombre)
        else :
            return resultados
    else:
        return "Público General"