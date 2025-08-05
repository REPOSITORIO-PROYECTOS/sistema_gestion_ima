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
                "estado": sesion.estado,
                "saldo_final_transferencias": sesion.saldo_final_transferencias,
                "saldo_final_bancario": sesion.saldo_final_bancario,
                "saldo_final_efectivo": sesion.saldo_final_efectivo,

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
    query = query.join(CajaSesion).where(CajaSesion.id_empresa == usuario_actual.id_empresa)
    # 3. Cargamos las relaciones necesarias de forma eficiente.
    query = query.options(
        selectinload(CajaMovimiento.venta).selectinload(Venta.cliente)
    )

    # 4. Ordenamos los resultados por fecha, lo más reciente primero.
    query = query.order_by(CajaMovimiento.timestamp.desc())

    # 5. Ejecutamos la consulta final.
    resultados = db.exec(query).all()
    print(f"Se encontraron {len(resultados)} movimientos en total para la empresa.")
    print(resultados)
    return resultados

def obtener_datos_para_ticket_cierre_detallado(db: Session, id_sesion: int, usuario_actual: Usuario) -> dict:
    """
    Recopila TODOS los datos necesarios para generar un ticket de cierre de lote,
    incluyendo el desglose de ventas por método de pago y el detalle de
    ingresos y egresos.
    """
    print(f"\n--- [TRACE: PREPARAR DATOS TICKET CIERRE DETALLADO] ---")
    print(f"Buscando datos para Sesión ID: {id_sesion}")

    # 1. Obtener la sesión de caja y sus relaciones importantes (usuarios, empresa)
    declaracion = (
        select(CajaSesion)
        .options(
            selectinload(CajaSesion.usuario_apertura).selectinload(Usuario.empresa),
            selectinload(CajaSesion.usuario_cierre)
        )
        .where(CajaSesion.id == id_sesion)
    )
    sesion = db.exec(declaracion).first()

    if not sesion:
        raise ValueError("La sesión de caja no fue encontrada.")
    
    # 2. Seguridad: Validar que la sesión pertenece a la empresa del usuario que pide el ticket
    if sesion.usuario_apertura.id_empresa != usuario_actual.id_empresa:
        raise PermissionError("No tiene permiso para acceder a esta sesión de caja.")

    if sesion.estado != "CERRADA":
        raise ValueError("Solo se pueden generar tickets para cajas ya cerradas.")
    
    print("Sesión encontrada y validada.")

    # 3. Obtener todos los movimientos de esa sesión
    movimientos = db.exec(
        select(CajaMovimiento)
        .where(CajaMovimiento.id_caja_sesion == id_sesion)
        .order_by(CajaMovimiento.timestamp.asc())
    ).all()

    # ====================================================================
    # === 4. PROCESADO DE DATOS (CON LÓGICA DE MÉTODOS DE PAGO AÑADIDA) ===
    # ====================================================================
    
    # A. Desglose de Ventas por Método de Pago
    ventas = [m for m in movimientos if m.tipo == 'VENTA']
    total_ventas = sum(v.monto for v in ventas)
    
    total_ventas_efectivo = sum(v.monto for v in ventas if v.metodo_pago and v.metodo_pago.upper() == 'EFECTIVO')
    total_ventas_transferencia = sum(v.monto for v in ventas if v.metodo_pago and v.metodo_pago.upper() == 'TRANSFERENCIA')
    total_ventas_bancario = sum(v.monto for v in ventas if v.metodo_pago and v.metodo_pago.upper() == 'BANCARIO')
    # Puedes añadir más métodos de pago aquí si los tienes (ej: 'MERCADO PAGO')

    # B. Desglose de Ingresos y Egresos (como ya lo tenías)
    desglose_ingresos = [
        {"concepto": m.concepto, "monto": m.monto} 
        for m in movimientos if m.tipo == 'INGRESO'
    ]
    total_ingresos = sum(ingreso['monto'] for ingreso in desglose_ingresos)
    
    desglose_egresos = [
        {"concepto": m.concepto, "monto": m.monto} 
        for m in movimientos if m.tipo == 'EGRESO'
    ]
    total_egresos = sum(egreso['monto'] for egreso in desglose_egresos)
    
    print(f"Movimientos procesados: {len(ventas)} ventas, {len(desglose_ingresos)} ingresos, {len(desglose_egresos)} egresos.")

    # 5. Construir el diccionario final que se pasará a la plantilla HTML
    datos_ticket = {
        "sesion": sesion,
        "usuario_apertura": sesion.usuario_apertura.nombre_usuario,
        "usuario_cierre": sesion.usuario_cierre.nombre_usuario if sesion.usuario_cierre else "N/A",
        "empresa": sesion.usuario_apertura.empresa,
        "totales": {
            "ventas": total_ventas,
            "ingresos": total_ingresos,
            "egresos": total_egresos,
        },
        # --- AÑADIMOS EL NUEVO DESGLOSE ---
        "desglose_metodos_pago": {
            "efectivo": total_ventas_efectivo,
            "transferencia": total_ventas_transferencia,
            "bancario": total_ventas_bancario,
        },
        "desglose_ingresos": desglose_ingresos,
        "desglose_egresos": desglose_egresos
    }
    
    print("--- [FIN TRACE] ---\n")
    return datos_ticket