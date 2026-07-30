#!/usr/bin/env python3
"""
Alinea CUIT de de-campo (37) y La Esquina 2 (38) al real:
Elizabeth Herminia Córica — 27311993351.

También asegura que la bóveda tenga el secreto bajo esa key
(copia desde 20987654321 si hace falta, sin tocar el PEM).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlmodel import Session

from back.cliente_boveda import ClienteBoveda
from back.config import API_KEY_INTERNA, URL_BOVEDA
from back.database import engine
from back.gestion import configuracion_manager
from back.modelos import ConfiguracionEmpresa, Empresa

CUIT_REAL = "27311993351"
CUIT_VIEJO = "20987654321"
EMPRESAS = (37, 38)
NOMBRE_TITULAR = "Elizabeth Herminia Córica"


def _cuit_de_cert(pem: str) -> str | None:
    try:
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend

        raw = pem.encode() if isinstance(pem, str) else pem
        cert = x509.load_pem_x509_certificate(raw, default_backend())
        subj = cert.subject.rfc4514_string()
        m = re.search(r"CUIT[^\d]*(\d{11})", subj, re.I) or re.search(r"(\d{11})", subj)
        return m.group(1) if m else None
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    dry = bool(args.dry_run)

    cliente = ClienteBoveda(base_url=URL_BOVEDA, api_key=API_KEY_INTERNA)
    print(f"=== alinear CUIT {CUIT_REAL} ({NOMBRE_TITULAR}) dry={dry} ===")

    # 1) Bóveda
    sec_nuevo = None
    sec_viejo = None
    try:
        sec_nuevo = cliente.obtener_secreto(CUIT_REAL)
    except Exception as ex:
        print(f"boveda {CUIT_REAL}: {type(ex).__name__}: {ex}")
    try:
        sec_viejo = cliente.obtener_secreto(CUIT_VIEJO)
    except Exception as ex:
        print(f"boveda {CUIT_VIEJO}: {type(ex).__name__}: {ex}")

    has_nuevo = bool(
        sec_nuevo and getattr(sec_nuevo, "certificado", None) and getattr(sec_nuevo, "clave_privada", None)
    )
    has_viejo = bool(
        sec_viejo and getattr(sec_viejo, "certificado", None) and getattr(sec_viejo, "clave_privada", None)
    )
    print(f"boveda {CUIT_REAL}={has_nuevo} | {CUIT_VIEJO}={has_viejo}")
    if has_viejo:
        print(f"  cert bajo {CUIT_VIEJO} -> {_cuit_de_cert(sec_viejo.certificado)}")
    if has_nuevo:
        print(f"  cert bajo {CUIT_REAL} -> {_cuit_de_cert(sec_nuevo.certificado)}")

    if not has_nuevo and has_viejo:
        cert_cuit = _cuit_de_cert(sec_viejo.certificado)
        print(f"  plan: copiar secreto {CUIT_VIEJO} -> {CUIT_REAL} (cert_cuit={cert_cuit})")
        if not dry:
            if cert_cuit and cert_cuit != CUIT_REAL:
                print(f"  WARN: cert subject {cert_cuit} != {CUIT_REAL}")
            resultado = cliente.guardar_secreto(
                cuit=CUIT_REAL,
                certificado=sec_viejo.certificado,
                clave_privada=sec_viejo.clave_privada,
            )
            print(f"  guardar_secreto={resultado}")
            sec_check = cliente.obtener_secreto(CUIT_REAL)
            ok = bool(
                sec_check
                and getattr(sec_check, "certificado", None)
                and getattr(sec_check, "clave_privada", None)
            )
            print(f"  post_check boveda {CUIT_REAL}={ok} cert={_cuit_de_cert(sec_check.certificado) if ok else None}")
            if not ok:
                return 2
    elif not has_nuevo and not has_viejo:
        print("ERROR: no hay secreto usable en bóveda para copiar/usar")
        return 3

    # 2) DB empresas
    with Session(engine) as db:
        for eid in EMPRESAS:
            e = db.get(Empresa, eid)
            c = db.get(ConfiguracionEmpresa, eid)
            if not e or not c:
                print(f"[{eid}] falta empresa/config")
                continue
            print(f"[{eid}] {e.nombre_fantasia!r}")
            print(f"  antes emp={e.cuit} cfg={c.cuit} iibb={c.ingresos_brutos} pv={c.afip_punto_venta_predeterminado}")
            if dry:
                continue
            e.cuit = CUIT_REAL
            c.cuit = CUIT_REAL
            if (c.ingresos_brutos or "").strip() in {"", CUIT_VIEJO}:
                c.ingresos_brutos = CUIT_REAL
            db.add(e)
            db.add(c)
            db.commit()
            afip = configuracion_manager.empresa_tiene_facturacion_afip_habilitada(db, eid)
            e2 = db.get(Empresa, eid)
            c2 = db.get(ConfiguracionEmpresa, eid)
            print(f"  despues emp={e2.cuit} cfg={c2.cuit} iibb={c2.ingresos_brutos} afip_ok={afip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
