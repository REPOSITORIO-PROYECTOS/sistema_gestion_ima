# gestion/caja/cliente_publico.py
# Este módulo podría usarse para seleccionar un cliente o usar "Público General".
# Eventualmente, podría interactuar con el módulo de Contabilidad/Clientes.

#ACA TENGO QUE TOMAR LOS DATOS DE LA TABLA CLIENTE , DEVULEVO EL NOMBRE DEL CLIENTE

from typing import Dict, List, Union

from requests import Session, session
from back.utils.tablas_handler import TablasHandler


def obtener_cliente_por_cuit(db: Session,id_empresa: int, cuit_cliente: str = None) -> Union[str, List[str]]:
    """
    Devuelve el nombre o lista de nombres de clientes cuyo CUIT coincida, para una empresa.
    Si no se provee un CUIT, devuelve "Público General".
    """
    if not cuit_cliente:
        return "Público General"

    caller = TablasHandler(id_empresa=id_empresa, db=session)
    datos_clientes = caller.cargar_clientes()

    resultados = []
    for cliente in datos_clientes:
        if str(cliente.get("CUIT-CUIL", "")).strip() == str(cuit_cliente).strip():
            nombre = cliente.get("nombre-usuario")
            if nombre:
                resultados.append(nombre)

    if len(resultados) == 1:
        return resultados[0]
    elif resultados:
        return resultados
    else:
        return "Cliente no encontrado"
    

def obtener_cliente_por_id(db: Session,id_empresa: int, id_cliente: str = None) -> Union[str, Dict]:
    """
    Devuelve los datos completos del cliente buscado por ID, para una empresa.
    Si no se encuentra o no se proporciona un ID, devuelve "Público General".
    """
    if not id_cliente:
        return "Público General"

    caller = TablasHandler(id_empresa=id_empresa, db=session)
    datos_clientes = caller.cargar_clientes()

    for cliente in datos_clientes:
        if str(cliente.get("id-cliente", "")).strip() == str(id_cliente).strip():
            return cliente

    return "Cliente no encontrado"