from sqlmodel import Session
from back.database import engine
from back.gestion import perfil_operativo_manager, configuracion_manager

with Session(engine) as db:
    p = perfil_operativo_manager.obtener_perfil_resuelto(db, 39)
    c = configuracion_manager.obtener_configuracion_empresa(db, 39)
    print("tipo", getattr(c, "tipo_esquema_empresa", None))
    print("modo", p.modo_especial)
    print("solo_comp", p.caja_solo_comprobante)
    print("auto_tf", p.factura_auto_transferencia_pos)
    print("afip", p.facturacion_afip_habilitada)
    print("puede_fact", p.caja_puede_facturar)
    print("plantilla", p.plantilla_origen)
    print("cuit_cfg", getattr(c, "cuit", None))
    print("afip_ok_cfg", getattr(c, "afip_ok", None))
    raw = getattr(c, "perfil_operativo", None) or {}
    print("raw_keys", sorted(raw.keys()) if isinstance(raw, dict) else type(raw))
    if isinstance(raw, dict):
        print("raw_solo", raw.get("caja_solo_comprobante"))
        print("raw_panel", raw.get("panel_estadisticas_caja"))
