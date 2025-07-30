# back/gestion/caja/consultas_caja.py
# VERSIÓN CORREGIDA Y UNIFICADA

import logging
from sqlmodel import Session, select
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import aliased, selectinload  
# Importamos los modelos necesarios, creando alias para evitar conflictos en el JOIN
from back.modelos import Articulo, CajaSesion, Usuario, CajaMovimiento, Tercero, Venta
from back.modelos import Usuario as UsuarioApertura
from back.modelos import Usuario as UsuarioCierre
from back.schemas.caja_schemas import TipoMovimiento


def obtener_arqueos_de_caja(id_empresa,db: Session, usuario_actual: Usuario) -> Dict[str, List[Dict[str, Any]]]:
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
            .where(UsuarioApertura.id_empresa == usuario_actual.id_empresa,Articulo.id_empresa == id_empresa)
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
    
def obtener_todos_los_movimientos_de_caja(db: Session, usuario_actual: Usuario) -> List[CajaMovimiento]:
    """
    Función maestra actualizada. Obtiene TODOS los movimientos de caja de la empresa
    del usuario actual (ingresos, egresos, ventas) y carga eficientemente
    la información de la venta y el cliente asociado cuando corresponde.
    Es la fuente de datos para el tablero de contabilidad/libro mayor de caja.
    """
    print(f"Buscando todos los movimientos de caja para la empresa ID: {usuario_actual.id_empresa}")
    
    # 1. Creamos la consulta base.
    query = select(CajaMovimiento)

    # 2. **FILTRO DE SEGURIDAD OBLIGATORIO (MULTI-EMPRESA)**
    query = query.join(CajaSesion).join(Usuario, CajaSesion.id_usuario_apertura == Usuario.id)\
                 .where(Usuario.id_empresa == usuario_actual.id_empresa)
    # 3. Cargamos las relaciones necesarias de forma eficiente.
    query = query.options(
        selectinload(CajaMovimiento.venta).selectinload(Venta.cliente)
    )

    # 4. Ordenamos los resultados por fecha, lo más reciente primero.
    query = query.order_by(CajaMovimiento.timestamp.desc())

    # 5. Ejecutamos la consulta final.
    resultados = db.exec(query).all()
    print(f"Se encontraron {len(resultados)} movimientos en total para la empresa.")
    return resultados