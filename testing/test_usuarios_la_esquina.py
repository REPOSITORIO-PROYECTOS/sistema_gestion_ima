#!/usr/bin/env python3
"""
Tests de integración: usuarios La Esquina (empresa 35) y permisos por rol.

Uso:
  python testing/test_usuarios_la_esquina.py
  API_BASE=http://127.0.0.1:8011 python testing/test_usuarios_la_esquina.py
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Callable, Optional

import httpx

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8011").rstrip("/")
PASSWORD = os.environ.get("TEST_PASSWORD", "LaEsquina2026")
ID_EMPRESA = 35

USUARIOS = {
    "Franco": "Admin",
    "Joa": "Admin",
    "Sol": "Encargada",
    "Mabel": "Encargada",
    "Yuliana": "Vendedora",
    "Abigail": "Vendedora",
    "Guadalupe": "Vendedora",
    "Sofia": "Vendedora",
    "Rocio": "Vendedora",
    "Franquera": "Vendedora",
}


@dataclass
class Case:
    name: str
    fn: Callable[[], None]


def login(client: httpx.Client, username: str, password: str = PASSWORD) -> str:
    res = client.post(
        f"{API_BASE}/auth/token",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert res.status_code == 200, f"Login {username}: {res.status_code} {res.text[:200]}"
    token = res.json()["access_token"]
    assert token, f"Login {username}: token vacío"
    return token


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_login_todos_los_usuarios() -> None:
    with httpx.Client(timeout=30.0) as client:
        for username in USUARIOS:
            login(client, username)


def test_login_password_incorrecta() -> None:
    with httpx.Client(timeout=30.0) as client:
        res = client.post(
            f"{API_BASE}/auth/token",
            data={"username": "Franco", "password": "mal-password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert res.status_code == 401, res.text


def test_me_empresa_y_rol() -> None:
    with httpx.Client(timeout=30.0) as client:
        for username, rol_esperado in USUARIOS.items():
            token = login(client, username)
            res = client.get(f"{API_BASE}/users/me", headers=auth_headers(token))
            assert res.status_code == 200, res.text
            data = res.json()
            assert data["nombre_usuario"] == username
            assert data["id_empresa"] == ID_EMPRESA, f"{username}: empresa {data['id_empresa']}"
            assert data["rol"]["nombre"] == rol_esperado, f"{username}: rol {data['rol']['nombre']}"
            assert data["activo"] is True


def test_vendedora_accede_ventas_y_caja() -> None:
    with httpx.Client(timeout=30.0) as client:
        token = login(client, "Yuliana")
        headers = auth_headers(token)

        estado = client.get(f"{API_BASE}/caja/estado", headers=headers)
        assert estado.status_code == 200, estado.text

        articulos = client.get(f"{API_BASE}/articulos/obtener_todos", headers=headers)
        assert articulos.status_code == 200, articulos.text
        assert isinstance(articulos.json(), list)


def test_encargada_accede_stock_modo_especial() -> None:
    with httpx.Client(timeout=30.0) as client:
        token = login(client, "Sol")
        headers = auth_headers(token)

        productos = client.get(f"{API_BASE}/modo-especial/productos", headers=headers)
        assert productos.status_code == 200, productos.text
        assert isinstance(productos.json(), list)


def test_vendedora_no_accede_admin() -> None:
    with httpx.Client(timeout=30.0) as client:
        token = login(client, "Yuliana")
        res = client.get(f"{API_BASE}/admin/usuarios/listar", headers=auth_headers(token))
        assert res.status_code == 403, res.text


def test_encargada_no_accede_admin() -> None:
    with httpx.Client(timeout=30.0) as client:
        token = login(client, "Mabel")
        res = client.get(f"{API_BASE}/admin/usuarios/listar", headers=auth_headers(token))
        assert res.status_code == 403, res.text


def test_admin_accede_gestion_usuarios() -> None:
    with httpx.Client(timeout=30.0) as client:
        token = login(client, "Franco")
        res = client.get(f"{API_BASE}/admin/usuarios/listar", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        usuarios = res.json()
        nombres = {u["nombre_usuario"] for u in usuarios}
        assert "Yuliana" in nombres
        assert "Sol" in nombres
        assert len(usuarios) >= len(USUARIOS)


def test_vendedora_no_puede_importar_modo_especial() -> None:
    with httpx.Client(timeout=30.0) as client:
        token = login(client, "Abigail")
        res = client.post(
            f"{API_BASE}/modo-especial/importar",
            headers=auth_headers(token),
            files={"file": ("test.csv", "codigo,descripcion\n1,Test\n", "text/csv")},
        )
        assert res.status_code == 403, res.text


def test_admin_puede_listar_roles() -> None:
    with httpx.Client(timeout=30.0) as client:
        token = login(client, "Joa")
        res = client.get(f"{API_BASE}/admin/roles", headers=auth_headers(token))
        assert res.status_code == 200, res.text
        nombres = {r["nombre"] for r in res.json()}
        assert {"Admin", "Encargada", "Vendedora"}.issubset(nombres)


CASES: list[Case] = [
    Case("login de los 10 usuarios", test_login_todos_los_usuarios),
    Case("login rechaza contraseña incorrecta", test_login_password_incorrecta),
    Case("/users/me devuelve empresa 35 y rol correcto", test_me_empresa_y_rol),
    Case("Vendedora accede a caja y artículos", test_vendedora_accede_ventas_y_caja),
    Case("Encargada accede a modo especial (stock)", test_encargada_accede_stock_modo_especial),
    Case("Vendedora NO accede a /admin/usuarios", test_vendedora_no_accede_admin),
    Case("Encargada NO accede a /admin/usuarios", test_encargada_no_accede_admin),
    Case("Admin lista usuarios de la empresa", test_admin_accede_gestion_usuarios),
    Case("Vendedora NO puede importar CSV modo especial", test_vendedora_no_puede_importar_modo_especial),
    Case("Admin lista roles incluyendo Encargada/Vendedora", test_admin_puede_listar_roles),
]


def main() -> int:
    print(f"API: {API_BASE}")
    print(f"Empresa esperada: {ID_EMPRESA}\n")

    ok = 0
    fail = 0
    for case in CASES:
        try:
            case.fn()
            print(f"  OK  {case.name}")
            ok += 1
        except AssertionError as exc:
            print(f"  FAIL {case.name}: {exc}")
            fail += 1
        except httpx.ConnectError:
            print(f"  FAIL {case.name}: no se pudo conectar a {API_BASE}")
            fail += 1

    print(f"\nResultado: {ok} OK, {fail} FAIL de {len(CASES)} tests")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
