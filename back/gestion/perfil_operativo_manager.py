# back/gestion/perfil_operativo_manager.py

import logging
from typing import Any, Optional

from sqlmodel import Session, select

from back.gestion import configuracion_manager
from back.gestion.plantillas_perfil import DESCRIPCIONES_PLANTILLAS, PLANTILLAS
from back.modelos import ConfiguracionEmpresa
from back.schemas.configuracion_resuelta_schemas import (
    ConfiguracionEmpresaResuelta,
    ConfiguracionEstandarResponse,
)
from back.schemas.perfil_operativo_schemas import (
    MigrarEsquemaRequest,
    PanelEstadisticasSecciones,
    PerfilOperativoAdminResponse,
    PerfilOperativoEmpresa,
    PerfilOperativoResuelto,
    PerfilOperativoUpdate,
    PlantillaPerfilResponse,
    TipoEsquemaEmpresa,
    secciones_estadisticas_todas_on,
)

logger = logging.getLogger(__name__)

EMPRESAS_ESPECIAL_PROD = frozenset({35, 36})
EMPRESAS_ESPECIAL_DEMO = frozenset({37, 38})


def _parse_tipo_esquema(config: ConfiguracionEmpresa) -> TipoEsquemaEmpresa:
    raw = getattr(config, "tipo_esquema_empresa", None) or TipoEsquemaEmpresa.ESTANDAR.value
    try:
        return TipoEsquemaEmpresa(str(raw))
    except ValueError:
        logger.warning("tipo_esquema_empresa inválido %r en empresa %s", raw, config.id_empresa)
        return TipoEsquemaEmpresa.ESTANDAR


def _perfil_raw_dict(config: ConfiguracionEmpresa) -> dict[str, Any]:
    raw = getattr(config, "perfil_operativo", None)
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    return {}


def _backfill_perfil_desde_plantilla(
    data: dict[str, Any],
    perfil: PerfilOperativoEmpresa,
) -> PerfilOperativoEmpresa:
    """Completa flags nuevos ausentes en JSON persistido (p. ej. cache_degradado)."""
    plantilla_id = data.get("plantilla_origen")
    plantilla = PLANTILLAS.get(plantilla_id) if plantilla_id else None

    updates: dict[str, Any] = {}
    if plantilla is not None:
        if "cache_degradado" not in data:
            updates["cache_degradado"] = plantilla.cache_degradado
        if "factura_auto_transferencia_pos" not in data:
            updates["factura_auto_transferencia_pos"] = plantilla.factura_auto_transferencia_pos

    if "panel_estadisticas_secciones" not in data:
        if plantilla is not None and plantilla.panel_estadisticas_caja:
            updates["panel_estadisticas_secciones"] = plantilla.panel_estadisticas_secciones.model_copy(
                deep=True
            )
        elif perfil.panel_estadisticas_caja:
            updates["panel_estadisticas_secciones"] = secciones_estadisticas_todas_on()

    if not updates:
        return perfil
    return perfil.model_copy(update=updates)


def cargar_perfil_desde_json(config: ConfiguracionEmpresa) -> PerfilOperativoEmpresa:
    data = _perfil_raw_dict(config)
    if not data:
        return PerfilOperativoEmpresa()
    try:
        perfil = PerfilOperativoEmpresa.model_validate(data)
        return _backfill_perfil_desde_plantilla(data, perfil)
    except Exception as exc:
        logger.warning(
            "perfil_operativo inválido en empresa %s: %s",
            config.id_empresa,
            exc,
        )
        return PerfilOperativoEmpresa()


def _valor_aclaracion_bool(aclaraciones: Optional[dict], key: str) -> bool:
    if not aclaraciones:
        return False
    valor = str(aclaraciones.get(key, "")).lower()
    return valor in {"true", "1", "si", "sí", "yes"}


def aplicar_fallback_legacy(
    config: ConfiguracionEmpresa,
    perfil: PerfilOperativoEmpresa,
) -> PerfilOperativoEmpresa:
    """Durante transición: columna modo_especial y aclaraciones_legales operativas."""
    actualizado = perfil.model_copy(deep=True)
    data = _perfil_raw_dict(config)

    if not data and bool(getattr(config, "modo_especial_habilitado", False)):
        plantilla_id = "modo_especial_pos"
        if config.id_empresa in EMPRESAS_ESPECIAL_DEMO:
            plantilla_id = "modo_especial_demo"
        base = PLANTILLAS[plantilla_id].model_copy(deep=True)
        base.empresas_transferencia_ids = list(
            EMPRESAS_ESPECIAL_DEMO if config.id_empresa in EMPRESAS_ESPECIAL_DEMO else EMPRESAS_ESPECIAL_PROD
        )
        actualizado = base

    if _valor_aclaracion_bool(config.aclaraciones_legales, "bloquear_descuentos_cajero"):
        actualizado.bloquear_descuentos_cajero = True

    if _valor_aclaracion_bool(config.aclaraciones_legales, "mesas_enabled"):
        actualizado.mesas_habilitado = True

    if _valor_aclaracion_bool(config.aclaraciones_legales, "balanza_auto_agregar"):
        actualizado.balanza_auto_agregar = True

    if _valor_aclaracion_bool(config.aclaraciones_legales, "balanza_auto_facturar"):
        actualizado.balanza_auto_facturar = True

    aclaraciones = config.aclaraciones_legales or {}
    for key in ("balanza_articulo_id", "balanza_precio_fuente"):
        valor = aclaraciones.get(key)
        if valor is not None and str(valor).strip():
            actualizado.casos_especiales[key] = valor

    if bool(getattr(config, "modo_especial_habilitado", False)):
        actualizado.modo_especial = True
        if not data:
            actualizado.sincronizar_google_sheets = False

    return actualizado


def aplicar_computados(
    db: Session,
    config: ConfiguracionEmpresa,
    perfil: PerfilOperativoEmpresa,
) -> PerfilOperativoResuelto:
    facturacion_afip = configuracion_manager.empresa_tiene_facturacion_afip_habilitada(
        db, config.id_empresa
    )
    caja_puede_facturar = (not perfil.caja_solo_comprobante) and facturacion_afip
    caja_puede_remito = perfil.caja_permitir_remito_presupuesto and facturacion_afip
    return PerfilOperativoResuelto(
        **perfil.model_dump(),
        facturacion_afip_habilitada=facturacion_afip,
        caja_puede_facturar=caja_puede_facturar,
        caja_puede_remito_presupuesto=caja_puede_remito,
    )


def resolver_configuracion_empresa(
    db: Session,
    id_empresa: int,
) -> ConfiguracionEmpresaResuelta:
    config = configuracion_manager.obtener_configuracion_empresa(db, id_empresa)
    tipo = _parse_tipo_esquema(config)

    if tipo == TipoEsquemaEmpresa.ESTANDAR:
        perfil_base = PLANTILLAS["retail_estandar"].model_copy(deep=True)
    else:
        perfil_base = cargar_perfil_desde_json(config)
        if not _perfil_raw_dict(config):
            plantilla_id = "modo_especial_demo" if id_empresa in EMPRESAS_ESPECIAL_DEMO else "modo_especial_pos"
            perfil_base = PLANTILLAS[plantilla_id].model_copy(deep=True)

    perfil = aplicar_fallback_legacy(config, perfil_base)
    perfil_resuelto = aplicar_computados(db, config, perfil)

    return ConfiguracionEmpresaResuelta(
        tipo_esquema=tipo,
        estandar=ConfiguracionEstandarResponse.model_validate(config),
        perfil_operativo=perfil_resuelto,
    )


def _sync_modo_especial_columna(config: ConfiguracionEmpresa, perfil: PerfilOperativoEmpresa) -> None:
    config.modo_especial_habilitado = bool(perfil.modo_especial)


def _guardar_perfil_en_config(
    config: ConfiguracionEmpresa,
    perfil: PerfilOperativoEmpresa,
    tipo: TipoEsquemaEmpresa,
) -> None:
    config.tipo_esquema_empresa = tipo.value
    config.perfil_operativo = perfil.model_dump()
    _sync_modo_especial_columna(config, perfil)


def migrar_empresa_a_esquema_estandar(db: Session, id_empresa: int) -> ConfiguracionEmpresa:
    config = configuracion_manager.obtener_configuracion_por_id_empresa(db, id_empresa)
    perfil_actual = _perfil_raw_dict(config)
    if perfil_actual:
        config.perfil_operativo_archivado = perfil_actual

    config.tipo_esquema_empresa = TipoEsquemaEmpresa.ESTANDAR.value
    config.perfil_operativo = {}
    config.modo_especial_habilitado = False

    db.add(config)
    db.commit()
    db.refresh(config)
    logger.info("Empresa %s migrada a esquema estándar", id_empresa)
    return config


def migrar_empresa_a_esquema_especial(
    db: Session,
    id_empresa: int,
    plantilla_id: str,
) -> ConfiguracionEmpresa:
    if plantilla_id not in PLANTILLAS:
        raise ValueError(f"Plantilla desconocida: {plantilla_id}")

    config = configuracion_manager.obtener_configuracion_por_id_empresa(db, id_empresa)
    perfil = PLANTILLAS[plantilla_id].model_copy(deep=True)
    perfil.plantilla_origen = plantilla_id

    if plantilla_id == "modo_especial_demo" and id_empresa not in EMPRESAS_ESPECIAL_DEMO:
        perfil.empresas_transferencia_ids = [id_empresa]
    elif plantilla_id == "modo_especial_pos" and id_empresa not in EMPRESAS_ESPECIAL_PROD:
        perfil.empresas_transferencia_ids = [id_empresa]

    _guardar_perfil_en_config(config, perfil, TipoEsquemaEmpresa.ESPECIAL)
    db.add(config)
    db.commit()
    db.refresh(config)
    logger.info("Empresa %s migrada a esquema especial (%s)", id_empresa, plantilla_id)
    return config


def aplicar_plantilla_perfil(
    db: Session,
    id_empresa: int,
    plantilla_id: str,
    merge: bool = False,
) -> ConfiguracionEmpresa:
    if plantilla_id not in PLANTILLAS:
        raise ValueError(f"Plantilla desconocida: {plantilla_id}")

    config = configuracion_manager.obtener_configuracion_por_id_empresa(db, id_empresa)
    tipo = _parse_tipo_esquema(config)
    if tipo != TipoEsquemaEmpresa.ESPECIAL:
        raise ValueError("Solo empresas con esquema especial pueden aplicar plantillas.")

    plantilla = PLANTILLAS[plantilla_id].model_copy(deep=True)
    plantilla.plantilla_origen = plantilla_id

    if merge:
        actual = aplicar_fallback_legacy(config, cargar_perfil_desde_json(config))
        merged = plantilla.model_dump()
        for key in ("casos_especiales", "empresas_transferencia_ids"):
            if key == "casos_especiales" and actual.casos_especiales:
                merged["casos_especiales"] = {**plantilla.casos_especiales, **actual.casos_especiales}
            if key == "empresas_transferencia_ids" and actual.empresas_transferencia_ids:
                merged["empresas_transferencia_ids"] = actual.empresas_transferencia_ids
        perfil = PerfilOperativoEmpresa.model_validate(merged)
    else:
        perfil = plantilla

    _guardar_perfil_en_config(config, perfil, TipoEsquemaEmpresa.ESPECIAL)
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def actualizar_perfil_operativo(
    db: Session,
    id_empresa: int,
    data: PerfilOperativoUpdate,
) -> ConfiguracionEmpresa:
    config = configuracion_manager.obtener_configuracion_por_id_empresa(db, id_empresa)
    tipo = _parse_tipo_esquema(config)
    if tipo != TipoEsquemaEmpresa.ESPECIAL:
        raise ValueError("Solo empresas con esquema especial tienen perfil editable.")

    perfil = aplicar_fallback_legacy(config, cargar_perfil_desde_json(config))
    patch = data.model_dump(exclude_unset=True)
    if "panel_estadisticas_secciones" in patch and patch["panel_estadisticas_secciones"] is not None:
        patch["panel_estadisticas_secciones"] = PanelEstadisticasSecciones.model_validate(
            patch["panel_estadisticas_secciones"]
        )
    perfil = perfil.model_copy(update=patch)
    _guardar_perfil_en_config(config, perfil, TipoEsquemaEmpresa.ESPECIAL)

    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def migrar_esquema(db: Session, id_empresa: int, req: MigrarEsquemaRequest) -> ConfiguracionEmpresa:
    if req.tipo_esquema == TipoEsquemaEmpresa.ESTANDAR:
        return migrar_empresa_a_esquema_estandar(db, id_empresa)

    plantilla_id = req.plantilla_id or "modo_especial_pos"
    return migrar_empresa_a_esquema_especial(db, id_empresa, plantilla_id)


def listar_plantillas() -> list[PlantillaPerfilResponse]:
    items: list[PlantillaPerfilResponse] = []
    for plantilla_id, perfil in PLANTILLAS.items():
        nombre, descripcion = DESCRIPCIONES_PLANTILLAS.get(
            plantilla_id,
            (plantilla_id, ""),
        )
        items.append(
            PlantillaPerfilResponse(
                id=plantilla_id,
                nombre=nombre,
                descripcion=descripcion,
                perfil=perfil,
            )
        )
    return items


def obtener_perfil_admin(db: Session, id_empresa: int) -> PerfilOperativoAdminResponse:
    config = configuracion_manager.obtener_configuracion_por_id_empresa(db, id_empresa)
    resuelto = resolver_configuracion_empresa(db, id_empresa)
    perfil_raw = cargar_perfil_desde_json(config)
    return PerfilOperativoAdminResponse(
        id_empresa=id_empresa,
        tipo_esquema=resuelto.tipo_esquema,
        perfil_operativo=perfil_raw if _perfil_raw_dict(config) else resuelto.perfil_operativo,
        perfil_operativo_resuelto=resuelto.perfil_operativo,
        modo_especial_habilitado=bool(getattr(config, "modo_especial_habilitado", False)),
        tiene_archivo=bool(getattr(config, "perfil_operativo_archivado", None)),
    )


def obtener_perfil_resuelto(db: Session, id_empresa: int) -> PerfilOperativoResuelto:
    return resolver_configuracion_empresa(db, id_empresa).perfil_operativo


METODOS_AUTOFACTURA_TRANSFERENCIA_POS = frozenset({"transferencia", "bancario", "pos"})


def normalizar_metodo_pago(metodo: str | None) -> str:
    return (metodo or "").strip().lower()


def metodos_disparan_autofactura_transferencia_pos(metodos: list[str]) -> bool:
    """True si algún medio es transferencia o POS/bancario."""
    return any(normalizar_metodo_pago(m) in METODOS_AUTOFACTURA_TRANSFERENCIA_POS for m in metodos)


def aplicar_autofactura_transferencia_pos_a_request(
    perfil: PerfilOperativoResuelto,
    *,
    quiere_factura: bool,
    tipo_comprobante_solicitado: Optional[str],
    metodo_pago: Optional[str],
    pagos_multiples: Optional[list[Any]],
    cuit_receptor: Optional[str] = None,
) -> tuple[bool, Optional[str]]:
    """
    Si el perfil lo pide y el pago es transferencia/POS, fuerza factura AFIP.
    No pisa remito/presupuesto. Devuelve (quiere_factura, tipo_comprobante).
    """
    tipo = (tipo_comprobante_solicitado or "").strip().lower()
    if tipo in {"remito", "presupuesto"}:
        return quiere_factura, tipo_comprobante_solicitado

    if quiere_factura:
        return True, tipo_comprobante_solicitado

    if not perfil.factura_auto_transferencia_pos or not perfil.caja_puede_facturar:
        return False, tipo_comprobante_solicitado

    metodos: list[str] = []
    if pagos_multiples:
        for pago in pagos_multiples:
            metodo = getattr(pago, "metodo_pago", None)
            if metodo is None and isinstance(pago, dict):
                metodo = pago.get("metodo_pago")
            if metodo:
                metodos.append(str(metodo))
    elif metodo_pago:
        metodos.append(metodo_pago)

    if not metodos_disparan_autofactura_transferencia_pos(metodos):
        return False, tipo_comprobante_solicitado

    cuit = "".join(ch for ch in str(cuit_receptor or "") if ch.isdigit())
    tipo_factura = "factura_a" if len(cuit) == 11 else "factura_b"
    return True, tipo_factura


def es_modo_especial_empresa(db: Session, id_empresa: int) -> bool:
    return obtener_perfil_resuelto(db, id_empresa).modo_especial


def empresa_sincroniza_google_sheets(db: Session, id_empresa: int) -> bool:
    return obtener_perfil_resuelto(db, id_empresa).sincronizar_google_sheets


def empresa_tiene_panel_estadisticas_caja(db: Session, id_empresa: int) -> bool:
    return obtener_perfil_resuelto(db, id_empresa).panel_estadisticas_caja


def empresa_caja_solo_comprobante(db: Session, id_empresa: int) -> bool:
    return obtener_perfil_resuelto(db, id_empresa).caja_solo_comprobante


def empresa_bloquea_descuentos_cajero(db: Session, id_empresa: int) -> bool:
    return obtener_perfil_resuelto(db, id_empresa).bloquear_descuentos_cajero


def obtener_grupo_transferencia(db: Session, id_empresa: int) -> frozenset[int]:
    ids = obtener_perfil_resuelto(db, id_empresa).empresas_transferencia_ids
    if not ids or id_empresa not in ids:
        raise ValueError("Esta empresa no participa en transferencias de stock.")
    return frozenset(ids)


OPERATIONAL_ACLARACION_KEYS: dict[str, str] = {
    "bloquear_descuentos_cajero": "bloquear_descuentos_cajero",
    "mesas_enabled": "mesas_habilitado",
    "balanza_auto_agregar": "balanza_auto_agregar",
    "balanza_auto_facturar": "balanza_auto_facturar",
}

OPERATIONAL_CASOS_KEYS = ("balanza_articulo_id", "balanza_precio_fuente")


def migrar_aclaraciones_operativas_a_perfil(
    db: Session,
    id_empresa: int,
    *,
    limpiar_aclaraciones: bool = True,
) -> dict[str, object]:
    """
    Copia flags operativos de aclaraciones_legales → perfil_operativo.
    Idempotente. Recomendado para empresas con esquema especial o modo_especial activo.
    """
    config = configuracion_manager.obtener_configuracion_por_id_empresa(db, id_empresa)
    aclaraciones = dict(config.aclaraciones_legales or {})
    if not aclaraciones:
        return {"id_empresa": id_empresa, "cambios": 0, "mensaje": "sin aclaraciones"}

    tipo = _parse_tipo_esquema(config)
    perfil = cargar_perfil_desde_json(config)
    if tipo == TipoEsquemaEmpresa.ESTANDAR and not bool(getattr(config, "modo_especial_habilitado", False)):
        perfil = PLANTILLAS["retail_estandar"].model_copy(deep=True)

    perfil = aplicar_fallback_legacy(config, perfil)
    cambios = 0

    for acl_key, perfil_field in OPERATIONAL_ACLARACION_KEYS.items():
        if acl_key not in aclaraciones:
            continue
        if _valor_aclaracion_bool(aclaraciones, acl_key):
            if not getattr(perfil, perfil_field):
                setattr(perfil, perfil_field, True)
                cambios += 1
        if limpiar_aclaraciones and acl_key in aclaraciones:
            del aclaraciones[acl_key]

    for key in OPERATIONAL_CASOS_KEYS:
        valor = aclaraciones.get(key)
        if valor is None or not str(valor).strip():
            continue
        if perfil.casos_especiales.get(key) != valor:
            perfil.casos_especiales[key] = valor
            cambios += 1
        if limpiar_aclaraciones and key in aclaraciones:
            del aclaraciones[key]

    if cambios == 0 and not limpiar_aclaraciones:
        return {"id_empresa": id_empresa, "cambios": 0, "mensaje": "ya migrado"}

    if tipo == TipoEsquemaEmpresa.ESPECIAL or bool(getattr(config, "modo_especial_habilitado", False)):
        if tipo != TipoEsquemaEmpresa.ESPECIAL:
            config.tipo_esquema_empresa = TipoEsquemaEmpresa.ESPECIAL.value
        _guardar_perfil_en_config(config, perfil, TipoEsquemaEmpresa.ESPECIAL)

    if limpiar_aclaraciones:
        config.aclaraciones_legales = aclaraciones

    db.add(config)
    db.commit()
    db.refresh(config)
    return {"id_empresa": id_empresa, "cambios": cambios, "mensaje": "ok"}


def migrar_aclaraciones_todas_empresas(db: Session) -> list[dict[str, object]]:
    configs = db.exec(select(ConfiguracionEmpresa)).all()
    resultados: list[dict[str, object]] = []
    for config in configs:
        if not config.id_empresa:
            continue
        acl = config.aclaraciones_legales or {}
        tiene_operativo = any(k in acl for k in (*OPERATIONAL_ACLARACION_KEYS, *OPERATIONAL_CASOS_KEYS))
        if not tiene_operativo:
            continue
        resultados.append(migrar_aclaraciones_operativas_a_perfil(db, config.id_empresa))
    return resultados


def seed_empresas_especiales_prod(db: Session) -> dict[str, int]:
    """Idempotente: empresas 35-38 → esquema especial con plantilla correcta."""
    resultados: dict[str, int] = {}
    mapping = {
        35: "modo_especial_pos",
        36: "modo_especial_pos",
        37: "modo_especial_demo",
        38: "modo_especial_demo",
    }
    for id_empresa, plantilla_id in mapping.items():
        config = db.get(ConfiguracionEmpresa, id_empresa)
        if not config:
            resultados[f"skip_{id_empresa}"] = 0
            continue
        ya_especial = (
            _parse_tipo_esquema(config) == TipoEsquemaEmpresa.ESPECIAL
            and bool(_perfil_raw_dict(config))
        )
        if ya_especial and id_empresa in EMPRESAS_ESPECIAL_DEMO:
            # Demo 37/38: re-aplicar plantilla (p. ej. habilitar factura en caja)
            aplicar_plantilla_perfil(db, id_empresa, plantilla_id, merge=False)
            resultados[f"resync_{id_empresa}"] = id_empresa
            continue
        if ya_especial:
            resultados[f"ok_{id_empresa}"] = id_empresa
            continue
        migrar_empresa_a_esquema_especial(db, id_empresa, plantilla_id)
        resultados[f"seed_{id_empresa}"] = id_empresa
    return resultados
