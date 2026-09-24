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


def _rango_semana_ar_utc_naive(dia: date) -> Tuple[date, date, datetime, datetime]:
    """Semana lunes–domingo AR. Devuelve (lunes, domingo, desde_utc, hasta_utc exclusive)."""
    lunes = dia - timedelta(days=dia.weekday())
    domingo = lunes + timedelta(days=6)
    desde, _ = _rango_dia_ar_utc_naive(lunes)
    _, hasta = _rango_dia_ar_utc_naive(domingo)
    return lunes, domingo, desde, hasta


def _resolver_periodo_estadisticas(
    modo: str,
    fecha_ref: Optional[date],
) -> Tuple[str, date, datetime, datetime, str]:
    """
    Resuelve rango UTC naive para estadísticas.
    modo: dia | semana | mes. fecha_ref ancla el período (default: hoy AR).
    """
    ahora = _ahora_ar()
    hoy = ahora.date()
    ancla = fecha_ref or hoy
    modo_n = (modo or "mes").strip().lower()
    if modo_n not in ("dia", "semana", "mes"):
        modo_n = "mes"

    if modo_n == "dia":
        desde, hasta = _rango_dia_ar_utc_naive(ancla)
        label = ancla.isoformat()
    elif modo_n == "semana":
        lunes, domingo, desde, hasta = _rango_semana_ar_utc_naive(ancla)
        label = f"{lunes.isoformat()}_a_{domingo.isoformat()}"
    else:
        desde, hasta_fin = _rango_mes_ar_utc_naive(ancla.year, ancla.month)
        if ancla.year == hoy.year and ancla.month == hoy.month:
            hasta = ahora.astimezone(timezone.utc).replace(tzinfo=None)
        else:
            hasta = hasta_fin
        label = f"{ancla.year}-{ancla.month:02d}"
    return modo_n, ancla, desde, hasta, label


def _bucket_metodo_pago(metodo: Optional[str]) -> str:
    """Normaliza a efectivo | transferencia | pos | otros."""
    m = (metodo or "").strip().upper()
    if m in ("EFECTIVO", "CASH"):
        return "efectivo"
    if m in ("TRANSFERENCIA", "TRANSFER", "TRANSFERENCIAS"):
        return "transferencia"
    if m in ("BANCARIO", "POS", "TARJETA", "DEBITO", "CRÉDITO", "CREDITO"):
        return "pos"
    return "otros"


def _desglose_medios_vacio() -> Dict[str, float]:
    return {"efectivo": 0.0, "transferencia": 0.0, "pos": 0.0, "otros": 0.0}


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
    del usuario actual (y el grupo de transferencia si aplica).
    """
    ids_empresas = _ids_empresas_para_estadisticas(db, usuario_actual.id_empresa)
    logging.info(
        "Solicitando informe de cajas para empresas %s (usuario emp=%s).",
        ids_empresas,
        usuario_actual.id_empresa,
    )
    
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
            # Multi-empresa: misma empresa o grupo de transferencia (modo especial).
            .where(CajaSesion.id_empresa.in_(ids_empresas))
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
            .where(CajaSesion.id_empresa.in_(ids_empresas))
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
    Panel de supervisión: cajas abiertas de la empresa (y grupo de transferencia)
    con totales de ventas y movimientos. Incluye desglose por medio por sesión.
    """
    ids_empresas = _ids_empresas_para_estadisticas(db, usuario_actual.id_empresa)
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
        .where(CajaSesion.id_empresa.in_(ids_empresas))
        .where(CajaSesion.estado == "ABIERTA")
        .order_by(CajaSesion.fecha_apertura.asc())
    )

    resultados = db.exec(consulta).all()
    ids_sesiones = [sesion.id for sesion, *_ in resultados]

    desglose_por_sesion: Dict[int, Dict[str, float]] = {
        sid: _desglose_medios_vacio() for sid in ids_sesiones
    }
    if ids_sesiones:
        filas_medio = db.exec(
            select(
                CajaMovimiento.id_caja_sesion,
                CajaMovimiento.metodo_pago,
                func.coalesce(func.sum(CajaMovimiento.monto), 0.0),
            )
            .where(CajaMovimiento.id_caja_sesion.in_(ids_sesiones))
            .where(CajaMovimiento.tipo == "VENTA")
            .where(func.upper(func.coalesce(CajaMovimiento.estado, "ACTIVO")) != "ANULADO")
            .group_by(CajaMovimiento.id_caja_sesion, CajaMovimiento.metodo_pago)
        ).all()
        for id_sesion, metodo, monto in filas_medio:
            bucket = _bucket_metodo_pago(metodo)
            desglose_por_sesion.setdefault(int(id_sesion), _desglose_medios_vacio())
            desglose_por_sesion[int(id_sesion)][bucket] = round(
                float(desglose_por_sesion[int(id_sesion)][bucket]) + float(monto or 0.0),
                2,
            )

    cajas_abiertas: List[Dict[str, Any]] = []
    resumen_desglose = _desglose_medios_vacio()

    for sesion, nombre_apertura, cant_mov, total_ventas, cant_ventas in resultados:
        desglose = desglose_por_sesion.get(sesion.id, _desglose_medios_vacio())
        for key in resumen_desglose:
            resumen_desglose[key] = round(resumen_desglose[key] + desglose[key], 2)
        cajas_abiertas.append({
            "id_sesion": sesion.id,
            "fecha_apertura": sesion.fecha_apertura,
            "usuario_apertura": nombre_apertura,
            "saldo_inicial": sesion.saldo_inicial,
            "cantidad_movimientos": int(cant_mov or 0),
            "cantidad_ventas": int(cant_ventas or 0),
            "total_ventas": float(total_ventas or 0.0),
            "desglose_medios": desglose,
        })

    return {
        "cajas_abiertas": cajas_abiertas,
        "resumen": {
            "total_cajas_abiertas": len(cajas_abiertas),
            "total_ventas": sum(c["total_ventas"] for c in cajas_abiertas),
            "total_movimientos": sum(c["cantidad_movimientos"] for c in cajas_abiertas),
            "desglose_medios": resumen_desglose,
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


def obtener_estadisticas_generales(
    db: Session,
    usuario_actual: Usuario,
    modo: str = "mes",
    fecha: Optional[date] = None,
) -> Dict[str, Any]:
    """
    KPIs del período (día / semana / mes), top productos/categorías, ranking vendedoras,
    medios de pago, alertas de stock y diferencias de caja.
    Respeta checklist de secciones del perfil.
    """
    from back.gestion.perfil_operativo_manager import obtener_perfil_resuelto
    from back.modelos import Empresa, ConfiguracionEmpresa

    perfil = obtener_perfil_resuelto(db, usuario_actual.id_empresa)
    secciones: PanelEstadisticasSecciones = (
        perfil.panel_estadisticas_secciones
        if perfil.panel_estadisticas_secciones is not None
        else secciones_estadisticas_todas_on()
    )

    modo_n, ancla, desde_periodo, hasta_periodo, periodo_label = _resolver_periodo_estadisticas(
        modo, fecha
    )

    ahora_ar = _ahora_ar()
    hoy = ahora_ar.date()
    desde_hoy, hasta_hoy = _rango_dia_ar_utc_naive(hoy)
    desde_ayer, hasta_ayer = _rango_dia_ar_utc_naive(hoy - timedelta(days=1))
    desde_mes_ancla, hasta_mes_ancla = _rango_mes_ar_utc_naive(ancla.year, ancla.month)
    if ancla.year == hoy.year and ancla.month == hoy.month:
        hasta_mes_ancla = ahora_ar.astimezone(timezone.utc).replace(tzinfo=None)
    if ancla.month == 1:
        desde_mes_ant, hasta_mes_ant = _rango_mes_ar_utc_naive(ancla.year - 1, 12)
    else:
        desde_mes_ant, hasta_mes_ant = _rango_mes_ar_utc_naive(ancla.year, ancla.month - 1)

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

    tickets_periodo, total_periodo = _agregar_ventas_periodo(
        db, ids_empresas, desde_periodo, hasta_periodo
    )
    ticket_promedio = round(total_periodo / tickets_periodo, 2) if tickets_periodo else 0.0

    por_establecimiento: List[Dict[str, Any]] = []
    tiene_multi_sucursal = len(ids_empresas) > 1
    if secciones.por_establecimiento and tiene_multi_sucursal:
        ventas_periodo = db.exec(
            _filtro_ventas_validas(select(Venta), ids_empresas, desde_periodo, hasta_periodo)
        ).all()
        por_empresa: Dict[int, Dict[str, float]] = {
            eid: {"cantidad": 0, "total": 0.0} for eid in ids_empresas
        }
        for v in ventas_periodo:
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
        if modo_n == "dia":
            tickets_sel, venta_sel = tickets_periodo, total_periodo
            prev = ancla - timedelta(days=1)
            desde_prev, hasta_prev = _rango_dia_ar_utc_naive(prev)
            _, venta_prev = _agregar_ventas_periodo(db, ids_empresas, desde_prev, hasta_prev)
            tickets_mes, venta_mes = _agregar_ventas_periodo(
                db, ids_empresas, desde_mes_ancla, hasta_mes_ancla
            )
            _, venta_mes_ant = _agregar_ventas_periodo(
                db, ids_empresas, desde_mes_ant, hasta_mes_ant
            )
        elif modo_n == "semana":
            tickets_sel, venta_sel = tickets_periodo, total_periodo
            lunes, _, _, _ = _rango_semana_ar_utc_naive(ancla)
            _, _, desde_prev, hasta_prev = _rango_semana_ar_utc_naive(lunes - timedelta(days=1))
            _, venta_prev = _agregar_ventas_periodo(db, ids_empresas, desde_prev, hasta_prev)
            tickets_mes, venta_mes = _agregar_ventas_periodo(
                db, ids_empresas, desde_mes_ancla, hasta_mes_ancla
            )
            _, venta_mes_ant = _agregar_ventas_periodo(
                db, ids_empresas, desde_mes_ant, hasta_mes_ant
            )
        else:
            tickets_sel, venta_sel = _agregar_ventas_periodo(
                db, ids_empresas, desde_hoy, hasta_hoy
            )
            _, venta_prev = _agregar_ventas_periodo(db, ids_empresas, desde_ayer, hasta_ayer)
            tickets_mes, venta_mes = tickets_periodo, total_periodo
            _, venta_mes_ant = _agregar_ventas_periodo(
                db, ids_empresas, desde_mes_ant, hasta_mes_ant
            )

        pct: Optional[float] = None
        if venta_mes_ant > 0:
            pct = round(((venta_mes - venta_mes_ant) / venta_mes_ant) * 100.0, 2)
        elif venta_mes > 0:
            pct = 100.0
        kpis = {
            "venta_hoy": venta_sel,
            "venta_ayer": venta_prev,
            "venta_mes": venta_mes,
            "venta_mes_anterior": venta_mes_ant,
            "pct_vs_mes_anterior": pct,
            "tickets_hoy": tickets_sel,
            "tickets_mes": tickets_mes,
            "ticket_promedio_hoy": round(venta_sel / tickets_sel, 2) if tickets_sel else 0.0,
            "ticket_promedio_mes": round(venta_mes / tickets_mes, 2) if tickets_mes else 0.0,
            "modo": modo_n,
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
            .where(Venta.timestamp >= desde_periodo)
            .where(Venta.timestamp < hasta_periodo)
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
            .select_from(Articulo)
            .join(VentaDetalle, VentaDetalle.id_articulo == Articulo.id)
            .join(Venta, Venta.id == VentaDetalle.id_venta)
            .outerjoin(Categoria, Categoria.id == Articulo.id_categoria)
            .where(Venta.id_empresa.in_(ids_empresas))
            .where(Venta.timestamp >= desde_periodo)
            .where(Venta.timestamp < hasta_periodo)
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
            .where(Venta.timestamp >= desde_periodo)
            .where(Venta.timestamp < hasta_periodo)
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
            .where(CajaMovimiento.timestamp >= desde_periodo)
            .where(CajaMovimiento.timestamp < hasta_periodo)
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
            .where(Articulo.stock_minimo > 0)
            .where(Articulo.stock_actual > 0)
            .where(Articulo.stock_actual <= Articulo.stock_minimo)
            .order_by(Articulo.stock_actual.asc())
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
        "periodo": periodo_label,
        "modo": modo_n,
        "desde": desde_periodo,
        "hasta": hasta_periodo,
        "cantidad_ventas": tickets_periodo,
        "total_ventas": total_periodo,
        "ticket_promedio": ticket_promedio,
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


def _xlsx_col(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _xlsx_sheet_xml(rows: List[List[Any]]) -> str:
    from xml.sax.saxutils import escape

    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        "<sheetData>",
    ]
    for r_idx, row in enumerate(rows, 1):
        parts.append(f'<row r="{r_idx}">')
        for c_idx, val in enumerate(row, 1):
            ref = f"{_xlsx_col(c_idx)}{r_idx}"
            if isinstance(val, bool):
                text = "1" if val else "0"
                parts.append(f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>')
            elif isinstance(val, (int, float)) and not isinstance(val, bool):
                parts.append(f'<c r="{ref}" t="n"><v>{val}</v></c>')
            else:
                text = escape("" if val is None else str(val))
                parts.append(f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>')
        parts.append("</row>")
    parts.append("</sheetData></worksheet>")
    return "".join(parts)


def _build_xlsx(sheets: Dict[str, List[List[Any]]]) -> bytes:
    """XLSX mínimo (stdlib) con una o más hojas."""
    import zipfile
    from io import BytesIO

    names = list(sheets.keys())
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/xl/workbook.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                + "".join(
                    f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
                    'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                    for i in range(1, len(names) + 1)
                )
                + "</Types>"
            ),
        )
        zf.writestr(
            "_rels/.rels",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                'Target="xl/workbook.xml"/>'
                "</Relationships>"
            ),
        )
        workbook_sheets = "".join(
            f'<sheet name="{name[:31]}" sheetId="{i}" r:id="rId{i}"/>'
            for i, name in enumerate(names, 1)
        )
        zf.writestr(
            "xl/workbook.xml",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                f"<sheets>{workbook_sheets}</sheets></workbook>"
            ),
        )
        rels = "".join(
            f'<Relationship Id="rId{i}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{i}.xml"/>'
            for i in range(1, len(names) + 1)
        )
        zf.writestr(
            "xl/_rels/workbook.xml.rels",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                f"{rels}</Relationships>"
            ),
        )
        for i, name in enumerate(names, 1):
            zf.writestr(f"xl/worksheets/sheet{i}.xml", _xlsx_sheet_xml(sheets[name]))
    return buf.getvalue()


def _fmt_dt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.astimezone(TZ_AR).strftime("%Y-%m-%d %H:%M:%S") if value.tzinfo else value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


def exportar_cierres_y_movimientos_mes_xlsx(
    db: Session,
    usuario_actual: Usuario,
    anio: int,
    mes: int,
) -> bytes:
    """
    Excel con 2 hojas: cierres de caja del mes y movimientos del mes.
    Solo empresa del usuario (modo especial / panel estadísticas).
    """
    if mes < 1 or mes > 12:
        raise ValueError("Mes inválido")
    if anio < 2000 or anio > 2100:
        raise ValueError("Año inválido")

    desde, hasta = _rango_mes_ar_utc_naive(anio, mes)
    id_empresa = usuario_actual.id_empresa

    UsuarioApertura = aliased(Usuario, name="usuario_apertura_export")
    UsuarioCierre = aliased(Usuario, name="usuario_cierre_export")

    filas_cierres = db.exec(
        select(
            CajaSesion,
            UsuarioApertura.nombre_usuario,
            UsuarioCierre.nombre_usuario,
        )
        .join(UsuarioApertura, CajaSesion.id_usuario_apertura == UsuarioApertura.id)
        .outerjoin(UsuarioCierre, CajaSesion.id_usuario_cierre == UsuarioCierre.id)
        .where(CajaSesion.id_empresa == id_empresa)
        .where(CajaSesion.estado == "CERRADA")
        .where(CajaSesion.fecha_cierre >= desde)
        .where(CajaSesion.fecha_cierre < hasta)
        .order_by(CajaSesion.fecha_cierre.asc())
    ).all()

    hoja_cierres: List[List[Any]] = [[
        "id_sesion",
        "fecha_apertura",
        "fecha_cierre",
        "usuario_apertura",
        "usuario_cierre",
        "saldo_inicial",
        "saldo_final_efectivo",
        "saldo_final_transferencias",
        "saldo_final_pos",
        "saldo_final_declarado",
        "saldo_final_calculado",
        "diferencia",
        "revisado",
    ]]
    for sesion, nom_ap, nom_ci in filas_cierres:
        hoja_cierres.append([
            sesion.id,
            _fmt_dt(sesion.fecha_apertura),
            _fmt_dt(sesion.fecha_cierre),
            nom_ap or "",
            nom_ci or "",
            float(sesion.saldo_inicial or 0.0),
            float(sesion.saldo_final_efectivo or 0.0),
            float(sesion.saldo_final_transferencias or 0.0),
            float(sesion.saldo_final_bancario or 0.0),
            float(sesion.saldo_final_declarado or 0.0) if sesion.saldo_final_declarado is not None else "",
            float(sesion.saldo_final_calculado or 0.0) if sesion.saldo_final_calculado is not None else "",
            float(sesion.diferencia or 0.0) if sesion.diferencia is not None else "",
            "SI" if sesion.revisado else "NO",
        ])

    filas_mov = db.exec(
        select(CajaMovimiento, Usuario.nombre_usuario)
        .join(CajaSesion, CajaSesion.id == CajaMovimiento.id_caja_sesion)
        .outerjoin(Usuario, Usuario.id == CajaMovimiento.id_usuario)
        .where(CajaSesion.id_empresa == id_empresa)
        .where(CajaMovimiento.timestamp >= desde)
        .where(CajaMovimiento.timestamp < hasta)
        .order_by(CajaMovimiento.timestamp.asc())
    ).all()

    hoja_mov: List[List[Any]] = [[
        "id_movimiento",
        "id_sesion",
        "timestamp",
        "tipo",
        "concepto",
        "monto",
        "metodo_pago",
        "estado",
        "usuario",
        "id_venta",
    ]]
    for mov, nom_usu in filas_mov:
        hoja_mov.append([
            mov.id,
            mov.id_caja_sesion,
            _fmt_dt(mov.timestamp),
            mov.tipo or "",
            mov.concepto or "",
            float(mov.monto or 0.0),
            (mov.metodo_pago or "").upper(),
            (mov.estado or "").upper(),
            nom_usu or "",
            mov.id_venta or "",
        ])

    return _build_xlsx({
        "Cierres de caja": hoja_cierres,
        "Movimientos": hoja_mov,
    })


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
