# gestion/caja/cliente_publico.py
# Este módulo podría usarse para seleccionar un cliente o usar "Público General".
# Eventualmente, podría interactuar con el módulo de Contabilidad/Clientes.

#ACA TENGO QUE TOMAR LOS DATOS DE LA TABLA CLIENTE , DEVULEVO EL NOMBRE DEL CLIENTE

from typing import Dict, List
from back.utils.tablas_handler import TablasHandler

caller = TablasHandler()

def obtener_cliente_por_cuit(cuit_cliente=None):  #NOTA DE LUCAS: usemos el CUIT del cliente, en el caso que haya 
                                                            #varios nombres con el mismo CUIT, los envio todos en forma de lista
    """
    Determina el cliente para una venta.
    Si no se provee id_cliente_o_nombre, se asume "Público General".
    Más adelante, podría buscar en una base de datos/hoja de clientes.
    """
    if cuit_cliente:
        datos_clientes = caller.cargar_clientes()
        resultados = []
        for cliente in datos_clientes:
            if str(cliente.get("CUIT-CUIL", "")).strip() == str(cuit_cliente).strip():
              nombre = cliente.get("nombre-usuario")
              resultados.append(nombre)
        if (len(resultados) == 1):
        
            return str(nombre)
        else :
            return resultados
    else:
        return "Público General"
    

def obtener_cliente_por_id(id_cliente=None):  #NOTA DE LUCAS: asumo que no se repiten ids?

    if id_cliente:
        datos_clientes = caller.cargar_clientes()
        for cliente in datos_clientes:
            if str(cliente.get("id-cliente", "")).strip() == str(id_cliente).strip():
                return cliente
        
    else:
        return "Público General"