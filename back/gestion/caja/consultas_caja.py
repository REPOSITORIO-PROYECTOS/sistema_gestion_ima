# back/gestion/caja/consultas_caja.py
# VERSIÓN CORREGIDA Y UNIFICADA

import logging
from sqlmodel import Session, select
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import aliased  
# Importamos los modelos necesarios, creando alias para evitar conflictos en el JOIN
from back.modelos import CajaSesion, Usuario, CajaMovimiento
from back.modelos import Usuario as UsuarioApertura
from back.modelos import Usuario as UsuarioCierre
from back.schemas.caja_schemas import TipoMovimiento


def obtener_arqueos_de_caja(db: Session, usuario_actual: Usuario) -> Dict[str, List[Dict[str, Any]]]:
    """
    Obtiene un informe de cajas abiertas y cerradas, filtrando por la empresa
    del usuario actual y usando JOINs seguros.
    """
    logging.info(f"Solicitando informe de cajas para la Empresa ID: {usuario_actual.id_empresa}.")
    
    informe_final = {
        "cajas_abiertas": [],
        "arqueos_cerrados": []
    }

    try:
        # --- PREPARACIÓN DE ALIAS ---
        UsuarioApertura = aliased(Usuario, name="usuario_apertura")
        UsuarioCierre = aliased(Usuario, name="usuario_cierre")

        # --- CONSULTA 1: ARQUEOS DE CAJAS CERRADAS ---
        consulta_cerradas = (
            select(CajaSesion, UsuarioApertura.nombre_usuario, UsuarioCierre.nombre_usuario)
            # ¡CAMBIO 1: JOIN de Apertura!
            .join(UsuarioApertura, CajaSesion.id_usuario_apertura == UsuarioApertura.id)
            # ¡CAMBIO 2: JOIN de Cierre ahora es un LEFT JOIN (isouter=True) para ser más seguro!
            # Esto evita errores si una caja cerrada no tiene un usuario de cierre asignado.
            .join(UsuarioCierre, CajaSesion.id_usuario_cierre == UsuarioCierre.id, isouter=True)
            # ¡CAMBIO 3: FILTRO DE SEGURIDAD MULTI-EMPRESA!
            # Nos unimos a la tabla de usuarios de apertura para filtrar por empresa.
            .where(UsuarioApertura.id_empresa == usuario_actual.id_empresa)
            .where(CajaSesion.estado == "CERRADA")
            .order_by(CajaSesion.fecha_cierre.desc())
        )
        resultados_cerradas = db.exec(consulta_cerradas).all()
        
        for sesion, nombre_apertura, nombre_cierre in resultados_cerradas:
            informe_final["arqueos_cerrados"].append({
                "id_sesion": sesion.id,
                "fecha_apertura": sesion.fecha_apertura,
                "fecha_cierre": sesion.fecha_cierre,
                "usuario_apertura": nombre_apertura,
                # ¡CAMBIO 4: MANEJO SEGURO DE POSIBLES NULOS!
                "usuario_cierre": nombre_cierre if nombre_cierre else "N/A",
                "saldo_inicial": sesion.saldo_inicial,
                "saldo_final_declarado": sesion.saldo_final_declarado,
                "saldo_final_calculado": sesion.saldo_final_calculado,
                "diferencia": sesion.diferencia,
                "estado": sesion.estado
            })

        # --- CONSULTA 2: CAJAS ACTUALMENTE ABIERTAS ---
        consulta_abiertas = (
            select(CajaSesion, UsuarioApertura.nombre_usuario)
            .join(UsuarioApertura, CajaSesion.id_usuario_apertura == UsuarioApertura.id)
            # ¡CAMBIO 3 (REPETIDO): FILTRO DE SEGURIDAD MULTI-EMPRESA!
            .where(UsuarioApertura.id_empresa == usuario_actual.id_empresa)
            .where(CajaSesion.estado == "ABIERTA")
            .order_by(CajaSesion.fecha_apertura.asc())
        )
        resultados_abiertas = db.exec(consulta_abiertas).all()

        for sesion, nombre_apertura in resultados_abiertas:
            informe_final["cajas_abiertas"].append({
                "id_sesion": sesion.id,
                "fecha_apertura": sesion.fecha_apertura,
                "usuario_apertura": nombre_apertura,
                "saldo_inicial": sesion.saldo_inicial,
                "estado": sesion.estado
            })
            
        return informe_final

    except Exception as e:
        logging.error(f"Error al generar el informe de cajas para la empresa {usuario_actual.id_empresa}: {e}", exc_info=True)
        # Relanzamos la excepción para que el router devuelva un 500, pero con el log ya escrito.
        raise e
    
def obtener_movimientos_de_caja(
    db: Session,
    usuario_actual: Usuario, # <-- AÑADIDO: Para la seguridad Multi-Empresa
    *,
    tipo_movimiento: Optional[TipoMovimiento] = None,
    id_sesion: Optional[int] = None
) -> List[CajaMovimiento]:
    """
    Obtiene una lista de movimientos de caja para la empresa del usuario actual,
    aplicando filtros dinámicos y garantizando el aislamiento de datos.

    Args:
        db: La sesión activa de la base de datos.
        usuario_actual: El usuario autenticado que realiza la petición.
        facturado: (Opcional) Filtra movimientos que están o no facturados.
        tipo_movimiento: (Opcional) Filtra por tipo (VENTA, INGRESO, EGRESO).
        id_sesion: (Opcional) Filtra los movimientos de una sesión de caja específica.

    Returns:
        Una lista de objetos del modelo SQLModel 'CajaMovimiento' que coinciden
        con los criterios de búsqueda.
    """
    # 1. Creamos la consulta base.
    #    Unimos (JOIN) con CajaSesion para poder filtrar por el id_empresa.
    query = select(CajaMovimiento).join(CajaSesion)

    # 2. **FILTRO DE SEGURIDAD OBLIGATORIO (MULTI-EMPRESA)**
    query = query.join(Usuario, CajaSesion.id_usuario_apertura == Usuario.id)\
                 .where(Usuario.id_empresa == usuario_actual.id_empresa)


    # 3. Aplicamos los filtros opcionales de la API.
    if tipo_movimiento is not None:
        query = query.where(CajaMovimiento.tipo == tipo_movimiento.value)

    if id_sesion is not None:
        query = query.where(CajaMovimiento.id_caja_sesion == id_sesion)

    # 4. Ordenamos los resultados por el campo 'timestamp' de tu modelo.
    query = query.order_by(CajaMovimiento.timestamp.desc())

    # 5. Ejecutamos la consulta y devolvemos los resultados.
    resultados = db.exec(query).all()
    return resultados