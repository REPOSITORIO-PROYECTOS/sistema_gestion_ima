#!/usr/bin/env python3
"""Alinea empresa 39 al CUIT del certificado subido a bóveda."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlmodel import Session

from back.cliente_boveda import ClienteBoveda
from back.config import API_KEY_INTERNA, URL_BOVEDA
from back.database import engine
from back.gestion import configuracion_manager, perfil_operativo_manager
from back.modelos import ConfiguracionEmpresa, Empresa

ID = 39
CUIT_VIEJO = "20999888776"


def _cuit_desde_cert(pem: str) -> str:
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend

    cert = x509.load_pem_x509_certificate(
        pem.encode() if isinstance(pem, str) else pem,
        default_backend(),
    )
    subject = cert.subject.rfc4514_string()
    m = re.search(r"(\d{11})", subject)
    if not m:
        raise RuntimeError(f"No se pudo leer CUIT del cert. Subject={subject}")
    return m.group(1)


def main() -> int:
    cliente = ClienteBoveda(base_url=URL_BOVEDA, api_key=API_KEY_INTERNA)

    with Session(engine) as db:
        emp = db.get(Empresa, ID)
        cfg = db.get(ConfiguracionEmpresa, ID)
        if not emp or not cfg:
            print("Empresa 39 no encontrada")
            return 1

        cuit_actual = "".join(filter(str.isdigit, emp.cuit or ""))
        print(f"CUIT actual empresa={cuit_actual}")

        # Leer secreto bajo el CUIT actual (donde lo subieron)
        sec = cliente.obtener_secreto(cuit_actual) or cliente.obtener_secreto(CUIT_VIEJO)
        if not sec or not sec.certificado:
            print("No hay certificado en bóveda")
            return 1

        cuit_cert = _cuit_desde_cert(sec.certificado)
        print(f"CUIT del certificado={cuit_cert}")

        # Guardar también bajo el CUIT real del cert (AFIP / lookup)
        if cuit_cert != cuit_actual:
            print(f"Copiando secreto bóveda {cuit_actual} → {cuit_cert}")
            cliente.guardar_secreto(cuit_cert, sec.certificado, sec.clave_privada)

        # Actualizar empresa + config
        emp.cuit = cuit_cert
        cfg.cuit = cuit_cert
        if cfg.ingresos_brutos and "".join(filter(str.isdigit, str(cfg.ingresos_brutos))) == cuit_actual:
            cfg.ingresos_brutos = cuit_cert
        db.add(emp)
        db.add(cfg)
        db.commit()
        print(f"Empresa/config CUIT actualizado → {cuit_cert}")

        # Re-verificar
        sec2 = cliente.obtener_secreto(cuit_cert)
        print(f"Bóveda bajo {cuit_cert}: cert={bool(sec2 and sec2.certificado)} key={bool(sec2 and sec2.clave_privada)}")
        afip = configuracion_manager.empresa_tiene_facturacion_afip_habilitada(db, ID)
        perfil = perfil_operativo_manager.obtener_perfil_resuelto(db, ID)
        print(
            f"facturacion_afip={afip} caja_puede_facturar={perfil.caja_puede_facturar} "
            f"solo_comprobante={perfil.caja_solo_comprobante}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
