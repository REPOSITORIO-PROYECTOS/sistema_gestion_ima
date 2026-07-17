#!/usr/bin/env python3
"""Smoke local para flujo offline: login, perfil, catálogo, caja."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

API = "http://127.0.0.1:8011"
ADMIN = "admin_local"
PASSWORD = "Local2026!"


def main() -> None:
    with httpx.Client(base_url=API, timeout=15.0) as client:
        token_res = client.post(
            "/auth/token",
            data={"username": ADMIN, "password": PASSWORD},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token_res.raise_for_status()
        token = token_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        empresa_res = client.get("/configuracion/mi-empresa", headers=headers)
        empresa_res.raise_for_status()
        empresa = empresa_res.json()

        perfil = empresa.get("perfil_operativo_resuelto") or {}
        empresa_id = empresa.get("id_empresa")
        tipo_esquema = empresa.get("tipo_esquema")
        cache_flag = perfil.get("cache_degradado")
        plantilla = perfil.get("plantilla_origen")
        offline_gate = (
            tipo_esquema == "especial"
            and (
                cache_flag is True
                or plantilla in {"modo_especial_demo", "modo_especial_pos"}
            )
        )

        if not offline_gate:
            migra = client.post(
                f"/empresas/admin/{empresa_id}/migrar-esquema",
                headers=headers,
                json={"tipo_esquema": "especial", "plantilla_id": "modo_especial_demo"},
            )
            if migra.status_code == 200:
                migra_body = migra.json()
                perfil = migra_body.get("perfil_operativo_resuelto") or perfil
                tipo_esquema = migra_body.get("tipo_esquema", tipo_esquema)
                cache_flag = perfil.get("cache_degradado")
                plantilla = perfil.get("plantilla_origen")
                offline_gate = (
                    tipo_esquema == "especial"
                    and (
                        cache_flag is True
                        or plantilla in {"modo_especial_demo", "modo_especial_pos"}
                    )
                )
                print("migrado_a_especial=true")
            else:
                print(f"migrado_a_especial=false status={migra.status_code}")

        empresa_res = client.get("/configuracion/mi-empresa", headers=headers)
        empresa_res.raise_for_status()
        empresa = empresa_res.json()
        perfil = empresa.get("perfil_operativo_resuelto") or perfil
        tipo_esquema = empresa.get("tipo_esquema", tipo_esquema)
        cache_flag = perfil.get("cache_degradado")
        plantilla = perfil.get("plantilla_origen")
        offline_gate = (
            tipo_esquema == "especial"
            and (
                cache_flag is True
                or plantilla in {"modo_especial_demo", "modo_especial_pos"}
            )
        )

        version_res = client.get("/articulos/version", headers=headers)
        version_res.raise_for_status()
        version = version_res.json()

        articulos_res = client.get("/articulos/obtener_todos?pagina=1&limite=5", headers=headers)
        articulos_res.raise_for_status()
        articulos = articulos_res.json()

        caja_res = client.get("/caja/estado-actual", headers=headers)
        caja_res.raise_for_status()
        caja = caja_res.json()

        abrir_res = None
        if not caja.get("caja_abierta"):
            abrir_res = client.post(
                "/caja/abrir",
                headers=headers,
                json={"saldo_inicial": 1000.0},
            )

        print("=== Smoke offline local OK ===")
        print(f"empresa_id={empresa_id}")
        print(f"tipo_esquema={tipo_esquema}")
        print(f"plantilla_origen={plantilla}")
        print(f"cache_degradado={cache_flag}")
        print(f"offline_gate_activo={offline_gate}")
        print(f"catalogo_version={version.get('version')}")
        print(f"articulos_muestra={len(articulos)}")
        if articulos:
            first = articulos[0]
            print(
                "primer_articulo="
                + json.dumps(
                    {
                        "id": first.get("id"),
                        "descripcion": first.get("descripcion"),
                        "stock_actual": first.get("stock_actual"),
                        "codigos": [c.get("codigo") for c in first.get("codigos", [])[:2]],
                    },
                    ensure_ascii=False,
                )
            )
        print(f"caja_antes={json.dumps(caja, ensure_ascii=False)}")
        if abrir_res is not None:
            print(f"abrir_caja_status={abrir_res.status_code}")
            if abrir_res.status_code == 200:
                print(f"abrir_caja={json.dumps(abrir_res.json(), ensure_ascii=False)}")


if __name__ == "__main__":
    main()
