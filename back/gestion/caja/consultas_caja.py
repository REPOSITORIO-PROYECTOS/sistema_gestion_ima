# back/gestion/caja/consultas_caja.py
# VERSIÓN CORREGIDA Y UNIFICADA

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy import case, func
from sqlalchemy.orm import aliased, selectinload
from sqlmodel import Session, select

# Importamos los modelos necesarios, creando alias para evitar conflictos en el JOIN
from back.modelos import (
    Articulo,
    CajaMovimiento,
    CajaSesion,
    Categoria,
    Tercero,
    Usuario,
    Venta,
    VentaDetalle,
)
from back.modelos import Usuario as UsuarioApertura
from back.modelos import Usuario as UsuarioCierre
from back.schemas.caja_schemas import TipoMovimiento
from back.schemas.perfil_operativo_schemas import PanelEstadisticasSecciones, secciones_estadisticas_todas_on

TZ_AR = ZoneInfo("America/Argentina/Buenos_Aires")


def _ahora_ar() -> datetime:
    return datetime.now(TZ_AR)


def _rango_dia_ar_utc_naive(dia: date) -> Tuple[datetime, datetime]:
    """Inicio inclusive / fin exclusive del día AR, como naive UTC (compatible con timestamp DB)."""
    start_ar = datetime(dia.year, dia.month, dia.day, 0, 0, 0, tzinfo=TZ_AR)
    end_ar = start_ar + timedelta(days=1)
    return (
        start_ar.astimezone(timezone.utc).replace(tzinfo=None),
        end_ar.astimezone(timezone.utc).replace(tzinfo=None),
    )


def _rango_mes_ar_utc_naive(year: int, month: int) -> Tuple[datetime, datetime]:
    start_ar = datetime(year, month, 1, 0, 0, 0, tzinfo=TZ_AR)
    if month == 12:
        end_ar = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=TZ_AR)
    else:
        end_ar = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=TZ_AR)
    return (
        start_ar.astimezone(timezone.utc).replace(tzinfo=None),
        end_ar.astimezone(timezone.utc).replace(tzinfo=None),
    )


def _filtro_ventas_validas(query, ids_empresas: List[int], desde: datetime, hasta: datetime):
    return (
        query.where(Venta.id_empresa.in_(ids_empresas))
        .where(Venta.timestamp >= desde)
        .where(Venta.timestamp < hasta)
        .where(func.upper(Venta.estado) != "ANULADA")
        .where(Venta.id_venta_lote_padre.is_(None))
    )


def _agregar_ventas_periodo(
    db: Session,
    ids_empresas: List[int],
    desde: datetime,
    hasta: datetime,
) -> Tuple[int, float]:
    row = db.exec(
        _filtro_ventas_validas(
            select(
                func.count(Venta.id),
                func.coalesce(func.sum(Venta.total), 0.0),
            ),
            ids_empresas,
            desde,
            hasta,
        )
    ).one()
    return int(row[0] or 0), round(float(row[1] or 0.0), 2)


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
        UsuarioRevision = aliased(Usuario, name="usuario_revision")
        consulta_cerradas = (
            select(
                CajaSesion,
                UsuarioApertura.nombre_usuario,
                UsuarioCierre.nombre_usuario,
                UsuarioRevision.nombre_usuario,
            )
            # ¡CAMBIO 1: JOIN de Apertura!
            .join(UsuarioApertura, CajaSesion.id_usuario_apertura == UsuarioApertura.id)
            # ¡CAMBIO 2: JOIN de Cierre ahora es un LEFT JOIN (isouter=True) para ser más seguro!
            # Esto evita errores si una caja cerrada no tiene un usuario de cierre asignado.
            .join(UsuarioCierre, CajaSesion.id_usuario_cierre == UsuarioCierre.id, isouter=True)
            .join(UsuarioRevision, CajaSesion.id_usuario_revision == UsuarioRevision.id, isouter=True)
            # ¡CAMBIO 3: FILTRO DE SEGURIDAD MULTI-EMPRESA!
            # Nos unimos a la tabla de usuarios de apertura para filtrar por empresa.
            .where(UsuarioApertura.id_empresa == usuario_actual.id_empresa)
            .where(CajaSesion.estado == "CERRADA")
            .order_by(CajaSesion.fecha_cierre.desc())
        )
        resultados_cerradas = db.exec(consulta_cerradas).all()
        
        for sesion, nombre_apertura, nombre_cierre, nombre_revision in resultados_cerradas:
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
                "revisado": bool(sesion.revisado),
                "fecha_revision": sesion.fecha_revision,
                "usuario_revision": nombre_revision,
                "nota_revision": sesion.nota_revision,
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


def obtener_panel_estadisticas_cajas(db: Session, usuario_actual: Usuario) -> Dict[str, Any]:
    """
    Panel de supervisión: cajas abiertas de la empresa con totales de ventas y movimientos.
    Pensado para gerentes/administradores en tiendas con múltiples cajeros (modo especial).
    """
    UsuarioApertura = aliased(Usuario, name="usuario_apertura_panel")

    mov_stats = (
        select(
            CajaMovimiento.id_caja_sesion,
            func.count(CajaMovimiento.id).label("cantidad_movimientos"),
            func.coalesce(
                func.sum(case((CajaMovimiento.tipo == "VENTA", CajaMovimiento.monto), else_=0.0)),
                0.0,
            ).label("total_ventas"),
            func.coalesce(
                func.sum(case((CajaMovimiento.tipo == "VENTA", 1), else_=0)),
                0,
            ).label("cantidad_ventas"),
        )
        .group_by(CajaMovimiento.id_caja_sesion)
        .subquery()
    )

    consulta = (
        select(
            CajaSesion,
            UsuarioApertura.nombre_usuario,
            func.coalesce(mov_stats.c.cantidad_movimientos, 0),
            func.coalesce(mov_stats.c.total_ventas, 0.0),
            func.coalesce(mov_stats.c.cantidad_ventas, 0),
        )
        .join(UsuarioApertura, CajaSesion.id_usuario_apertura == UsuarioApertura.id)
        .outerjoin(mov_stats, mov_stats.c.id_caja_sesion == CajaSesion.id)
        .where(CajaSesion.id_empresa == usuario_actual.id_empresa)
        .where(CajaSesion.estado == "ABIERTA")
        .order_by(CajaSesion.fecha_apertura.asc())
    )

    resultados = db.exec(consulta).all()
    cajas_abiertas: List[Dict[str, Any]] = []

    for sesion, nombre_apertura, cant_mov, total_ventas, cant_ventas in resultados:
        cajas_abiertas.append({
            "id_sesion": sesion.id,
            "fecha_apertura": sesion.fecha_apertura,
            "usuario_apertura": nombre_apertura,
            "saldo_inicial": sesion.saldo_inicial,
            "cantidad_movimientos": int(cant_mov or 0),
            "cantidad_ventas": int(cant_ventas or 0),
            "total_ventas": float(total_ventas or 0.0),
        })

    return {
        "cajas_abiertas": cajas_abiertas,
        "resumen": {
            "total_cajas_abiertas": len(cajas_abiertas),
            "total_ventas": sum(c["total_ventas"] for c in cajas_abiertas),
            "total_movimientos": sum(c["cantidad_movimientos"] for c in cajas_abiertas),
        },
    }


def _ids_empresas_para_estadisticas(db: Session, id_empresa: int) -> List[int]:
    """Empresa actual; si participa en grupo de transferencia, incluye el grupo."""
    from back.gestion.perfil_operativo_manager import obtener_perfil_resuelto

    perfil = obtener_perfil_resuelto(db, id_empresa)
    ids = [int(x) for x in (perfil.empresas_transferencia_ids or []) if x is not None]
    if ids and id_empresa in ids:
        return sorted(set(ids))
    return [id_empresa]


def obtener_estadisticas_generales(db: Session, usuario_actual: Usuario) -> Dict[str, Any]:
    """
    KPIs del mes/día, top productos/categorías, ranking vendedoras, medios de pago,
    alertas de stock y diferencias de caja. Respeta checklist de secciones del perfil.
    """
    from back.gestion.perfil_operativo_manager import obtener_perfil_resuelto
    from back.modelos import Empresa, ConfiguracionEmpresa

    perfil = obtener_perfil_resuelto(db, usuario_actual.id_empresa)
    secciones: PanelEstadisticasSecciones = (
        perfil.panel_estadisticas_secciones
        if perfil.panel_estadisticas_secciones is not None
        else secciones_estadisticas_todas_on()
    )

    ahora_ar = _ahora_ar()
    hoy = ahora_ar.date()
    ayer = hoy - timedelta(days=1)
    desde_hoy, hasta_hoy = _rango_dia_ar_utc_naive(hoy)
    desde_ayer, hasta_ayer = _rango_dia_ar_utc_naive(ayer)
    desde_mes, _hasta_mes = _rango_mes_ar_utc_naive(hoy.year, hoy.month)
    if hoy.month == 1:
        desde_mes_ant, hasta_mes_ant = _rango_mes_ar_utc_naive(hoy.year - 1, 12)
    else:
        desde_mes_ant, hasta_mes_ant = _rango_mes_ar_utc_naive(hoy.year, hoy.month - 1)

    # Tope superior del mes en curso: ahora (no fin de mes)
    hasta_ahora_utc = ahora_ar.astimezone(timezone.utc).replace(tzinfo=None)

    ids_empresas = _ids_empresas_para_estadisticas(db, usuario_actual.id_empresa)

    empresas = db.exec(select(Empresa).where(Empresa.id.in_(ids_empresas))).all()
    configs = {
        c.id_empresa: c
        for c in db.exec(
            select(ConfiguracionEmpresa).where(ConfiguracionEmpresa.id_empresa.in_(ids_empresas))
        ).all()
    }

    def _nombre_empresa(eid: int) -> str:
        cfg = configs.get(eid)
        if cfg and cfg.nombre_negocio:
            return cfg.nombre_negocio
        emp = next((e for e in empresas if e.id == eid), None)
        if not emp:
            return f"Empresa {eid}"
        return emp.nombre_fantasia or emp.nombre_legal or f"Empresa {eid}"

    nombres = {eid: _nombre_empresa(eid) for eid in ids_empresas}

    tickets_mes, total_mes = _agregar_ventas_periodo(db, ids_empresas, desde_mes, hasta_ahora_utc)
    ticket_promedio_mes = round(total_mes / tickets_mes, 2) if tickets_mes else 0.0

    por_establecimiento: List[Dict[str, Any]] = []
    tiene_multi_sucursal = len(ids_empresas) > 1
    if secciones.por_establecimiento and tiene_multi_sucursal:
        ventas_mes = db.exec(
            _filtro_ventas_validas(select(Venta), ids_empresas, desde_mes, hasta_ahora_utc)
        ).all()
        por_empresa: Dict[int, Dict[str, float]] = {
            eid: {"cantidad": 0, "total": 0.0} for eid in ids_empresas
        }
        for v in ventas_mes:
            bucket = por_empresa.setdefault(v.id_empresa, {"cantidad": 0, "total": 0.0})
            bucket["cantidad"] += 1
            bucket["total"] += float(v.total or 0.0)

        for eid in ids_empresas:
            cant = int(por_empresa[eid]["cantidad"])
            tot = float(por_empresa[eid]["total"])
            por_establecimiento.append({
                "id_empresa": eid,
                "nombre": nombres.get(eid, f"Empresa {eid}"),
                "cantidad_ventas": cant,
                "total_ventas": round(tot, 2),
                "ticket_promedio": round(tot / cant, 2) if cant else 0.0,
            })

    kpis = None
    if secciones.kpis_periodo:
        tickets_hoy, venta_hoy = _agregar_ventas_periodo(db, ids_empresas, desde_hoy, hasta_hoy)
        _, venta_ayer = _agregar_ventas_periodo(db, ids_empresas, desde_ayer, hasta_ayer)
        _, venta_mes_ant = _agregar_ventas_periodo(db, ids_empresas, desde_mes_ant, hasta_mes_ant)
        pct: Optional[float] = None
        if venta_mes_ant > 0:
            pct = round(((total_mes - venta_mes_ant) / venta_mes_ant) * 100.0, 2)
        elif total_mes > 0:
            pct = 100.0
        kpis = {
            "venta_hoy": venta_hoy,
            "venta_ayer": venta_ayer,
            "venta_mes": total_mes,
            "venta_mes_anterior": venta_mes_ant,
            "pct_vs_mes_anterior": pct,
            "tickets_hoy": tickets_hoy,
            "tickets_mes": tickets_mes,
            "ticket_promedio_hoy": round(venta_hoy / tickets_hoy, 2) if tickets_hoy else 0.0,
            "ticket_promedio_mes": ticket_promedio_mes,
        }

    monto_linea = (
        VentaDetalle.cantidad * VentaDetalle.precio_unitario
        - func.coalesce(VentaDetalle.descuento_aplicado, 0.0)
    )

    top_productos: List[Dict[str, Any]] = []
    if secciones.top_productos:
        top_rows = db.exec(
            select(
                Articulo.id,
                Articulo.descripcion,
                func.coalesce(func.sum(VentaDetalle.cantidad), 0.0).label("cantidad_vendida"),
                func.coalesce(func.sum(monto_linea), 0.0).label("monto_total"),
            )
            .join(VentaDetalle, VentaDetalle.id_articulo == Articulo.id)
            .join(Venta, Venta.id == VentaDetalle.id_venta)
            .where(Venta.id_empresa.in_(ids_empresas))
            .where(Venta.timestamp >= desde_mes)
            .where(Venta.timestamp < hasta_ahora_utc)
            .where(func.upper(Venta.estado) != "ANULADA")
            .where(Venta.id_venta_lote_padre.is_(None))
            .group_by(Articulo.id, Articulo.descripcion)
            .order_by(func.sum(monto_linea).desc())
            .limit(10)
        ).all()
        top_productos = [
            {
                "id_articulo": int(row[0]),
                "descripcion": row[1],
                "cantidad_vendida": float(row[2] or 0.0),
                "monto_total": round(float(row[3] or 0.0), 2),
            }
            for row in top_rows
        ]

    top_categorias: List[Dict[str, Any]] = []
    if secciones.top_categorias:
        nombre_cat = func.coalesce(Categoria.nombre, "Sin categoría")
        cat_rows = db.exec(
            select(
                nombre_cat.label("categoria"),
                func.coalesce(func.sum(VentaDetalle.cantidad), 0.0).label("cantidad_vendida"),
                func.coalesce(func.sum(monto_linea), 0.0).label("monto_total"),
            )
            .join(VentaDetalle, VentaDetalle.id_articulo == Articulo.id)
            .join(Venta, Venta.id == VentaDetalle.id_venta)
            .outerjoin(Categoria, Categoria.id == Articulo.id_categoria)
            .where(Venta.id_empresa.in_(ids_empresas))
            .where(Venta.timestamp >= desde_mes)
            .where(Venta.timestamp < hasta_ahora_utc)
            .where(func.upper(Venta.estado) != "ANULADA")
            .where(Venta.id_venta_lote_padre.is_(None))
            .group_by(nombre_cat)
            .order_by(func.sum(monto_linea).desc())
            .limit(10)
        ).all()
        top_categorias = [
            {
                "categoria": row[0] or "Sin categoría",
                "cantidad_vendida": float(row[1] or 0.0),
                "monto_total": round(float(row[2] or 0.0), 2),
            }
            for row in cat_rows
        ]

    ranking_vendedores: List[Dict[str, Any]] = []
    if secciones.ranking_vendedores:
        vend_rows = db.exec(
            select(
                Usuario.id,
                Usuario.nombre_usuario,
                func.count(Venta.id).label("cantidad_ventas"),
                func.coalesce(func.sum(Venta.total), 0.0).label("total_ventas"),
            )
            .join(Venta, Venta.id_usuario == Usuario.id)
            .where(Venta.id_empresa.in_(ids_empresas))
            .where(Venta.timestamp >= desde_mes)
            .where(Venta.timestamp < hasta_ahora_utc)
            .where(func.upper(Venta.estado) != "ANULADA")
            .where(Venta.id_venta_lote_padre.is_(None))
            .group_by(Usuario.id, Usuario.nombre_usuario)
            .order_by(func.sum(Venta.total).desc())
            .limit(15)
        ).all()
        ranking_vendedores = [
            {
                "id_usuario": int(row[0]),
                "nombre_usuario": row[1],
                "cantidad_ventas": int(row[2] or 0),
                "total_ventas": round(float(row[3] or 0.0), 2),
            }
            for row in vend_rows
        ]

    medios_pago: List[Dict[str, Any]] = []
    if secciones.medios_pago:
        medio_rows = db.exec(
            select(
                CajaMovimiento.metodo_pago,
                func.count(CajaMovimiento.id).label("cantidad"),
                func.coalesce(func.sum(CajaMovimiento.monto), 0.0).label("monto_total"),
            )
            .join(CajaSesion, CajaSesion.id == CajaMovimiento.id_caja_sesion)
            .where(CajaSesion.id_empresa.in_(ids_empresas))
            .where(CajaMovimiento.tipo == "VENTA")
            .where(func.upper(CajaMovimiento.estado) != "ANULADO")
            .where(CajaMovimiento.timestamp >= desde_mes)
            .where(CajaMovimiento.timestamp < hasta_ahora_utc)
            .group_by(CajaMovimiento.metodo_pago)
            .order_by(func.sum(CajaMovimiento.monto).desc())
        ).all()
        medios_pago = [
            {
                "metodo_pago": (row[0] or "SIN_METODO").upper(),
                "cantidad": int(row[1] or 0),
                "monto_total": round(float(row[2] or 0.0), 2),
            }
            for row in medio_rows
        ]

    stock_bajo: List[Dict[str, Any]] = []
    sin_stock: List[Dict[str, Any]] = []
    alertas_stock = None
    if secciones.alertas_stock:
        stock_bajo_rows = db.exec(
            select(Articulo)
            .where(Articulo.id_empresa.in_(ids_empresas))
            .where(Articulo.activo == True)  # noqa: E712
            .where(Articulo.stock_minimo.is_not(None))
            .where(Articulo.stock_actual < Articulo.stock_minimo)
            .where(Articulo.stock_actual > 0)
            .order_by((Articulo.stock_actual - Articulo.stock_minimo).asc())
            .limit(15)
        ).all()
        stock_bajo = [
            {
                "id_articulo": articulo.id,
                "descripcion": articulo.descripcion,
                "stock_actual": float(articulo.stock_actual or 0.0),
                "stock_minimo": float(articulo.stock_minimo or 0.0),
                "id_empresa": articulo.id_empresa,
                "nombre_empresa": nombres.get(articulo.id_empresa, f"Empresa {articulo.id_empresa}"),
            }
            for articulo in stock_bajo_rows
        ]

        sin_stock_rows = db.exec(
            select(Articulo)
            .where(Articulo.id_empresa.in_(ids_empresas))
            .where(Articulo.activo == True)  # noqa: E712
            .where(Articulo.stock_actual <= 0)
            .order_by(Articulo.descripcion.asc())
            .limit(15)
        ).all()
        sin_stock = [
            {
                "id_articulo": articulo.id,
                "descripcion": articulo.descripcion,
                "stock_actual": float(articulo.stock_actual or 0.0),
                "stock_minimo": float(articulo.stock_minimo or 0.0),
                "id_empresa": articulo.id_empresa,
                "nombre_empresa": nombres.get(articulo.id_empresa, f"Empresa {articulo.id_empresa}"),
            }
            for articulo in sin_stock_rows
        ]
        alertas_stock = {
            "sin_stock": sin_stock,
            "stock_bajo": stock_bajo,
            "cantidad_sin_stock": len(sin_stock),
            "cantidad_stock_bajo": len(stock_bajo),
        }
    else:
        # Compat: lista stock_bajo vacía si sección off
        pass

    # Compat legado: stock_bajo flat list (bajo mínimo o sin stock si no hay mínimos)
    if not stock_bajo and sin_stock:
        stock_bajo_legado = sin_stock
    else:
        stock_bajo_legado = stock_bajo

    alertas_diferencias: List[Dict[str, Any]] = []
    if secciones.alertas_diferencias_caja:
        UsuarioCierreAlias = aliased(Usuario, name="usuario_cierre_diff")
        diff_rows = db.exec(
            select(CajaSesion, UsuarioCierreAlias.nombre_usuario)
            .outerjoin(
                UsuarioCierreAlias,
                CajaSesion.id_usuario_cierre == UsuarioCierreAlias.id,
            )
            .where(CajaSesion.id_empresa.in_(ids_empresas))
            .where(CajaSesion.estado == "CERRADA")
            .where(CajaSesion.diferencia.is_not(None))
            .where(CajaSesion.diferencia != 0)
            .order_by(CajaSesion.fecha_cierre.desc())
            .limit(20)
        ).all()
        for sesion, nombre_cierre in diff_rows:
            alertas_diferencias.append({
                "id_sesion": sesion.id,
                "fecha_cierre": sesion.fecha_cierre,
                "usuario_cierre": nombre_cierre,
                "diferencia": float(sesion.diferencia or 0.0),
                "id_empresa": sesion.id_empresa,
                "nombre_empresa": nombres.get(sesion.id_empresa, f"Empresa {sesion.id_empresa}"),
            })

    return {
        "periodo": f"{hoy.year}-{hoy.month:02d}",
        "desde": desde_mes,
        "hasta": hasta_ahora_utc,
        "cantidad_ventas": tickets_mes,
        "total_ventas": total_mes,
        "ticket_promedio": ticket_promedio_mes,
        "por_establecimiento": por_establecimiento if (secciones.por_establecimiento and tiene_multi_sucursal) else [],
        "top_productos": top_productos,
        "stock_bajo": stock_bajo_legado,
        "kpis": kpis,
        "alertas_stock": alertas_stock,
        "alertas_diferencias_caja": alertas_diferencias,
        "top_categorias": top_categorias,
        "ranking_vendedores": ranking_vendedores,
        "medios_pago": medios_pago,
    }


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
        selectinload(CajaMovimiento.venta).selectinload(Venta.cliente),
        selectinload(CajaMovimiento.venta).selectinload(Venta.items).selectinload(VentaDetalle.articulo),
        selectinload(CajaMovimiento.usuario)
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
    total_propinas = 0.0
    for v in ventas:
        concepto = v.concepto or ""
        if "Incluye Propina:" in concepto:
            try:
                start = concepto.index("Incluye Propina:") + len("Incluye Propina:")
                end = concepto.find(")", start)
                fragment = concepto[start:end if end != -1 else None].strip()
                fragment = fragment.replace("$", "").replace(",", ".")
                total_propinas += float(fragment)
            except Exception:
                pass
    
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
            "propinas": total_propinas,
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

def obtener_estado_caja_actual_usuario(db: Session, usuario_actual: Usuario) -> dict:
    """
    Verifica de forma rápida y eficiente si un usuario tiene una caja abierta
    y devuelve su estado actual.
    """
    sesion_abierta = db.exec(
        select(CajaSesion).where(
            CajaSesion.id_usuario_apertura == usuario_actual.id,
            CajaSesion.estado == "ABIERTA"
        )
    ).first()

    if sesion_abierta:
        return {
            "caja_abierta": True,
            "id_sesion": sesion_abierta.id,
            "fecha_apertura": sesion_abierta.fecha_apertura
        }
    else:
        return {"caja_abierta": False}
