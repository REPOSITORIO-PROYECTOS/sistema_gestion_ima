# back/gestion/caja/consultas_caja.py
# VERSIÓN CORREGIDA Y UNIFICADA

import logging
from sqlalchemy import text
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
    
def obtener_todos_los_movimientos_de_caja(db: Session, usuario_actual: Usuario) -> List[Dict]:
    """
    Obtiene todos los movimientos de caja usando una consulta SQL pura para asegurar
    que todos los datos, incluyendo el 'tipo_comprobante_solicitado', se carguen.
    """
    print(f"Buscando todos los movimientos con SQL puro para la empresa ID: {usuario_actual.id_empresa}")

    query_sql = text("""
        SELECT
            cm.id AS movimiento_id,
            cm.timestamp AS movimiento_timestamp,
            cm.tipo AS movimiento_tipo,
            cm.concepto AS movimiento_concepto,
            cm.monto AS movimiento_monto,
            cm.metodo_pago AS movimiento_metodo_pago,
            v.id AS venta_id,
            v.facturada AS venta_facturada,
            v.datos_factura AS venta_datos_factura,
            v.tipo_comprobante_solicitado AS venta_tipo_comprobante,
            cli.id AS cliente_id,
            cli.nombre_razon_social AS cliente_nombre
        FROM
            caja_movimientos AS cm
        JOIN
            caja_sesiones AS cs ON cm.id_caja_sesion = cs.id
        LEFT JOIN
            ventas AS v ON cm.id_venta = v.id
        LEFT JOIN
            terceros AS cli ON v.id_cliente = cli.id
        WHERE
            cs.id_empresa = :id_empresa_actual
        ORDER BY
            cm.timestamp DESC;
    """)

    # Ejecutamos la consulta. .mappings() devuelve los resultados como diccionarios.
    resultados_crudos = db.exec(
        query_sql,
        params={"id_empresa_actual": usuario_actual.id_empresa}
    ).mappings().all()

    # Ahora, procesamos los resultados crudos para construir la estructura que FastAPI espera
    movimientos_procesados = []
    for row in resultados_crudos:
        movimiento_dict = {
            "id": row["movimiento_id"],
            "timestamp": row["movimiento_timestamp"],
            "tipo": row["movimiento_tipo"],
            "concepto": row["movimiento_concepto"],
            "monto": row["movimiento_monto"],
            "metodo_pago": row["movimiento_metodo_pago"],
            "venta": None  # Por defecto no hay venta
        }

        # Si el movimiento tiene una venta asociada (venta_id no es NULL)
        if row["venta_id"]:
            venta_dict = {
                "id": row["venta_id"],
                "facturada": row["venta_facturada"],
                "datos_factura": row["venta_datos_factura"],
                "tipo_comprobante_solicitado": row["venta_tipo_comprobante"], # ¡Aquí está!
                "cliente": None # Por defecto no hay cliente
            }

            # Si la venta tiene un cliente asociado
            if row["cliente_id"]:
                venta_dict["cliente"] = {
                    "id": row["cliente_id"],
                    "nombre_razon_social": row["cliente_nombre"]
                }
            
            movimiento_dict["venta"] = venta_dict
        
        movimientos_procesados.append(movimiento_dict)

    print(f"Se procesaron {len(movimientos_procesados)} movimientos con SQL puro.")
    return movimientos_procesados