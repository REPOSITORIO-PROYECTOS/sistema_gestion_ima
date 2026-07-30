#!/usr/bin/env python3
"""
Smoke prod: venta RECARGA + TRANSFERENCIA en de-campo (37).
Deja quiere_factura=False para validar autofactura del backend.
"""
from __future__ import annotations

import json
import sys

import requests

API = "http://127.0.0.1:8011"
USER = "admin_campo"
PASSWORD = "decampo123"
MONTO = 100.0


def main() -> int:
    s = requests.Session()
    token_res = s.post(
        f"{API}/auth/token",
        data={"username": USER, "password": PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    print("login", token_res.status_code)
    if token_res.status_code != 200:
        print(token_res.text[:500])
        return 1
    token = token_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    emp = s.get(f"{API}/configuracion/mi-empresa", headers=headers, timeout=30)
    print("empresa", emp.status_code)
    emp_j = emp.json() if emp.status_code == 200 else {}
    perfil = emp_j.get("perfil_operativo") or {}
    estandar = emp_j.get("estandar") or {}
    print(
        "  id_empresa=",
        estandar.get("id_empresa"),
        "auto=",
        perfil.get("factura_auto_transferencia_pos"),
        "puede_fact=",
        perfil.get("caja_puede_facturar"),
        "afip=",
        perfil.get("facturacion_afip_habilitada"),
    )

    estado = s.get(f"{API}/caja/estado", headers=headers, timeout=30)
    print("caja", estado.status_code, estado.text[:300])

    arts = s.get(
        f"{API}/articulos/buscar",
        headers=headers,
        params={"termino": "RECARGA"},
        timeout=30,
    )
    print("articulos", arts.status_code)
    items = arts.json() if arts.status_code == 200 else []
    recarga = None
    for a in items if isinstance(items, list) else []:
        if str(a.get("codigo_interno") or "").strip().upper() == "RECARGA":
            recarga = a
            break
    if not recarga:
        recarga = {
            "id": 32397,
            "descripcion": "RECARGA DE TELEFONO",
            "codigo_interno": "RECARGA",
            "precio_manual": True,
        }
        print("  usando id hardcoded 32397")
    print(
        "  recarga=",
        recarga.get("id"),
        recarga.get("codigo_interno"),
        recarga.get("descripcion"),
        "pm=",
        recarga.get("precio_manual"),
    )

    body = {
        "id_cliente": 0,
        "total_venta": MONTO,
        "descuento_total": 0.0,
        "paga_con": MONTO,
        "metodo_pago": "TRANSFERENCIA",
        "quiere_factura": False,
        "tipo_comprobante_solicitado": "recibo",
        "articulos_vendidos": [
            {
                "id_articulo": int(recarga["id"]),
                "nombre": recarga.get("descripcion") or "RECARGA DE TELEFONO",
                "cantidad": 1,
                "precio_unitario": MONTO,
                "subtotal": MONTO,
                "tasa_iva": 21.0,
            }
        ],
    }
    print("POST /caja/ventas/registrar quiere_factura=False metodo=TRANSFERENCIA monto=", MONTO)
    venta = s.post(f"{API}/caja/ventas/registrar", headers=headers, json=body, timeout=90)
    print("venta", venta.status_code)
    try:
        data = venta.json()
    except Exception:
        print(venta.text[:1000])
        return 2
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str)[:4000])
    afip = (data.get("data") or {}).get("facturacion_afip") or {}
    estado_afip = afip.get("estado")
    print("RESULTADO_AFIP", estado_afip)
    if afip.get("cae") or str(estado_afip).upper() in {"APROBADO", "A", "OK", "ACEPTADO"}:
        print("SMOKE_OK facturo cae=", afip.get("cae"))
        return 0
    if str(estado_afip).upper() in {"FALLIDO", "R", "RECHAZADO"}:
        print("SMOKE_AFIP_FALLIDO", afip.get("error") or afip)
        return 3
    if estado_afip == "NO_SOLICITADA":
        print("SMOKE_FAIL autofactura no disparo")
        return 4
    print("SMOKE_CHECK_MANUAL", afip)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
