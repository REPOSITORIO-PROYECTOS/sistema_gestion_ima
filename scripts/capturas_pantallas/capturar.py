#!/usr/bin/env python3
"""
Captura automática de pantallas de la aplicación IMA y generación de guía en Markdown.

Requisitos:
  pip install playwright httpx
  playwright install chromium

Uso:
  python scripts/capturas_pantallas/capturar.py --usuario LA_ESQUINA --password '***'
  python scripts/capturas_pantallas/capturar.py --base-url http://127.0.0.1:3000 --solo login,ventas
  CAPTURAS_USER=admin CAPTURAS_PASSWORD=*** python scripts/capturas_pantallas/capturar.py

Salida (default):
  docs/manual/capturas/<timestamp>/
    *.png
    GUIA_PANTALLAS.md
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from pantallas import PANTALLAS, Pantalla  # noqa: E402

DEFAULT_BASE_URL = os.environ.get("CAPTURAS_BASE_URL", "https://sistema-ima.sistemataup.online")
DEFAULT_API_URL = os.environ.get(
    "CAPTURAS_API_URL",
    "https://sistema-ima.sistemataup.online/api",
)
DEFAULT_OUTPUT = _ROOT / "docs" / "manual" / "capturas"

EMPRESAS_PRESET: Dict[str, Dict[str, str]] = {
    "la_esquina": {
        "usuario": "LA_ESQUINA",
        "slug": "la_esquina",
        "nombre": "LA ESQUINA (id=35)",
    },
}
VIEWPORT = {"width": 1440, "height": 900}


def login_api(api_url: str, usuario: str, password: str) -> Dict[str, Any]:
    """Obtiene token, usuario y empresa vía API REST."""
    api = api_url.rstrip("/")
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        token_res = client.post(
            f"{api}/auth/token",
            data={"username": usuario, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_res.status_code != 200:
            raise SystemExit(
                f"Login fallido ({token_res.status_code}): {token_res.text[:300]}"
            )
        token = token_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        me_res = client.get(f"{api}/users/me", headers=headers)
        if me_res.status_code != 200:
            raise SystemExit(f"No se pudo obtener /users/me: {me_res.text[:300]}")
        usuario_data = me_res.json()

        empresa_res = client.get(f"{api}/configuracion/mi-empresa", headers=headers)
        if empresa_res.status_code != 200:
            raise SystemExit(
                f"No se pudo obtener /configuracion/mi-empresa: {empresa_res.text[:300]}"
            )
        empresa_data = empresa_res.json()

    return {
        "token": token,
        "usuario": usuario_data,
        "empresa": {
            "id_empresa": empresa_data.get("id_empresa"),
            "nombre_negocio": empresa_data.get("nombre_negocio"),
            "color_principal": empresa_data.get("color_principal") or "bg-sky-800",
            **{k: v for k, v in empresa_data.items() if k not in ("id_empresa",)},
        },
    }


def login_desde_db(usuario: str) -> Dict[str, Any]:
    """Genera sesión desde la DB local (útil cuando no hay contraseña a mano)."""
    from datetime import timedelta

    from sqlalchemy.orm import selectinload
    from sqlmodel import Session, select

    from back.database import engine
    from back.gestion import configuracion_manager
    from back.modelos import Usuario
    from back.schemas.configuracion_schemas import ConfiguracionResponse
    from back.schemas.usuario_schemas import UsuarioResponse
    from back.security import ACCESS_TOKEN_EXPIRE_MINUTES, crear_access_token

    with Session(engine) as db:
        user = db.exec(
            select(Usuario)
            .where(Usuario.nombre_usuario == usuario)
            .options(selectinload(Usuario.rol))
        ).first()
        if not user or not user.activo or not user.rol:
            raise SystemExit(f"Usuario '{usuario}' no encontrado o inactivo en la DB local.")
        if not user.id_empresa:
            raise SystemExit(f"Usuario '{usuario}' no tiene empresa asociada.")

        config = configuracion_manager.obtener_configuracion_empresa(db, user.id_empresa)
        if not config:
            raise SystemExit(f"No hay configuración para la empresa id={user.id_empresa}.")

        token = crear_access_token(
            data={"sub": user.nombre_usuario},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        usuario_data = UsuarioResponse.model_validate(user, from_attributes=True).model_dump()
        empresa_data = ConfiguracionResponse.model_validate(config, from_attributes=True).model_dump()

    return {
        "token": token,
        "usuario": usuario_data,
        "empresa": {
            "id_empresa": empresa_data.get("id_empresa"),
            "nombre_negocio": empresa_data.get("nombre_negocio"),
            "color_principal": empresa_data.get("color_principal") or "bg-sky-800",
            **{k: v for k, v in empresa_data.items() if k not in ("id_empresa",)},
        },
    }


def _auth_storage_payload(session: Dict[str, Any]) -> Dict[str, Any]:
    usuario = session["usuario"]
    return {
        "state": {
            "token": session["token"],
            "role": usuario.get("rol"),
            "nombre_usuario": usuario.get("nombre_usuario"),
            "usuario": usuario,
        },
        "version": 0,
    }


def _empresa_storage_payload(session: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "state": {"empresa": session["empresa"]},
        "version": 0,
    }


async def login_ui(page, base_url: str, usuario: str, password: str) -> None:
    """Login por formulario (misma UX que el usuario final)."""
    await page.goto(base_url, wait_until="networkidle", timeout=90000)
    await page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
    await page.goto(base_url, wait_until="networkidle", timeout=90000)
    await page.wait_for_selector("#username", timeout=20000)
    await page.fill("#username", usuario)
    await page.fill("#password", password)
    await page.get_by_role("button", name="Ingresar").click()
    await page.wait_for_url("**/dashboard**", timeout=60000)
    await page.wait_for_selector("#main-content, nav", timeout=30000)


async def _leer_sesion_desde_navegador(page) -> Dict[str, Any]:
    raw = await page.evaluate(
        """() => ({
            auth: localStorage.getItem('auth-storage'),
            empresa: sessionStorage.getItem('empresa-storage'),
        })"""
    )
    auth = json.loads(raw["auth"]) if raw.get("auth") else {}
    empresa_wrap = json.loads(raw["empresa"]) if raw.get("empresa") else {}
    state = auth.get("state") or {}
    if not state.get("token"):
        raise RuntimeError("No hay sesión activa en el navegador tras el login.")
    return {
        "token": state["token"],
        "usuario": state.get("usuario") or {},
        "empresa": (empresa_wrap.get("state") or {}).get("empresa") or {},
    }


async def _limpiar_sesion(page, base_url: str) -> None:
    await page.goto(base_url, wait_until="domcontentloaded")
    await page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
async def _inyectar_sesion(page, session: Dict[str, Any]) -> None:
    auth_json = json.dumps(_auth_storage_payload(session))
    empresa_json = json.dumps(_empresa_storage_payload(session))
    await page.evaluate(
        """([auth, empresa]) => {
            localStorage.setItem('auth-storage', auth);
            sessionStorage.setItem('empresa-storage', empresa);
        }""",
        [auth_json, empresa_json],
    )


async def _ejecutar_acciones(page, pantalla: Pantalla) -> None:
    for accion in pantalla.acciones_previas:
        if accion.tipo == "wait_ms":
            await page.wait_for_timeout(int(accion.valor))
        elif accion.tipo == "wait_selector":
            await page.wait_for_selector(accion.valor, timeout=15000)
        elif accion.tipo == "click_text":
            await page.get_by_text(accion.valor, exact=False).first.click(timeout=10000)
            await page.wait_for_timeout(400)


async def capturar_pantalla(
    page,
    base_url: str,
    pantalla: Pantalla,
    destino: Path,
    session: Optional[Dict[str, Any]],
) -> None:
    url = urljoin(base_url.rstrip("/") + "/", pantalla.ruta.lstrip("/"))

    if not pantalla.requiere_auth:
        await _limpiar_sesion(page, base_url)
    elif session:
        await page.goto(base_url, wait_until="domcontentloaded")
        await _inyectar_sesion(page, session)

    await page.goto(url, wait_until="networkidle", timeout=90000)

    if pantalla.esperar_selector:
        try:
            await page.wait_for_selector(pantalla.esperar_selector, timeout=20000)
        except Exception:
            pass

    await _ejecutar_acciones(page, pantalla)
    await page.wait_for_timeout(800)

    ruta_png = destino / pantalla.archivo
    timeout_ms = 120000 if pantalla.id == "stock" else 30000
    page.set_default_timeout(timeout_ms)
    await page.screenshot(path=str(ruta_png), full_page=pantalla.full_page, timeout=timeout_ms)
    print(f"  ✓ {pantalla.archivo} — {pantalla.titulo}")


def _filtrar_pantallas(filtro: Optional[List[str]]) -> List[Pantalla]:
    if not filtro:
        return PANTALLAS
    ids = {f.strip().lower() for f in filtro}
    return [p for p in PANTALLAS if p.id in ids or p.id.split("_")[0] in ids]


def generar_guia(
    pantallas: List[Pantalla],
    destino: Path,
    meta: Dict[str, Any],
) -> Path:
    lineas = [
        "# Guía de pantallas — Sistema IMA",
        "",
        f"Generado: {meta['fecha']}",
        f"URL base: `{meta['base_url']}`",
        f"Usuario de captura: `{meta['usuario']}`",
        f"Empresa: **{meta.get('empresa', '—')}**",
        "",
        "Este documento explica para qué sirve cada pantalla y el procedimiento recomendado.",
        "",
        "---",
        "",
    ]

    for i, p in enumerate(pantallas, 1):
        roles = ", ".join(p.roles)
        lineas.extend(
            [
                f"## {i}. {p.titulo}",
                "",
                f"![{p.titulo}]({p.archivo})",
                "",
                f"**Ruta:** `{p.ruta}`  ",
                f"**Roles:** {roles}",
                "",
                "### Para qué sirve",
                "",
                p.para_que_sirve,
                "",
                "### Procedimiento",
                "",
            ]
        )
        for j, paso in enumerate(p.procedimiento, 1):
            lineas.append(f"{j}. {paso}")
        lineas.append("")
        if p.notas:
            lineas.extend([f"> **Nota:** {p.notas}", ""])
        lineas.append("---")
        lineas.append("")

    guia_path = destino / "GUIA_PANTALLAS.md"
    guia_path.write_text("\n".join(lineas), encoding="utf-8")
    return guia_path


async def main_async(args: argparse.Namespace) -> None:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise SystemExit(
            "Falta playwright. Instalá con:\n"
            "  pip install playwright httpx\n"
            "  playwright install chromium"
        ) from exc

    pantallas = _filtrar_pantallas(args.solo)
    if not pantallas:
        raise SystemExit("Ninguna pantalla coincide con --solo")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    subcarpeta = args.empresa_slug or "general"
    destino = Path(args.output) / subcarpeta / timestamp
    destino.mkdir(parents=True, exist_ok=True)

    session: Optional[Dict[str, Any]] = None
    necesita_auth = any(p.requiere_auth for p in pantallas)

    print(f"\nCapturando {len(pantallas)} pantalla(s) → {destino}\n")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=not args.visible)
        context = await browser.new_context(viewport=VIEWPORT, locale="es-AR")
        page = await context.new_page()

        if necesita_auth:
            usuario = args.usuario
            if not usuario:
                raise SystemExit("Indique --usuario, --empresa la_esquina o CAPTURAS_USER.")

            if args.desde_db:
                print(f"Generando sesión desde DB local para {usuario}...")
                session = login_desde_db(usuario)
                print(f"  Empresa: {session['empresa'].get('nombre_negocio', '—')}")
            elif args.login_api:
                if not args.password:
                    raise SystemExit("Se requiere --password para --login-api.")
                print(f"Autenticando por API como {usuario}...")
                session = login_api(args.api_url, usuario, args.password)
                print(f"  Empresa: {session['empresa'].get('nombre_negocio', '—')}")
            else:
                if not args.password:
                    raise SystemExit(
                        "Se requiere --password, --desde-db o --login-api con contraseña."
                    )
                print(f"Autenticando por UI como {usuario}...")
                await login_ui(page, args.base_url, usuario, args.password)
                session = await _leer_sesion_desde_navegador(page)
                print(f"  Empresa: {session['empresa'].get('nombre_negocio', '—')}")

        for pantalla in pantallas:
            try:
                await capturar_pantalla(
                    page,
                    args.base_url,
                    pantalla,
                    destino,
                    session if pantalla.requiere_auth else None,
                )
            except Exception as exc:
                print(f"  ✗ {pantalla.id}: {exc}")

        await browser.close()

    meta = {
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "base_url": args.base_url,
        "usuario": args.usuario or "(sin login)",
        "empresa": session["empresa"].get("nombre_negocio") if session else getattr(args, "empresa_nombre", None),
    }
    guia = generar_guia(pantallas, destino, meta)
    print(f"\nGuía generada: {guia}")
    print(f"Carpeta de capturas: {destino}")

    try:
        from generar_instructivo_html import generar_html as generar_instructivo

        empresa_key = getattr(args, "empresa_slug", None) or "none"
        if empresa_key == "general":
            empresa_key = "none"
        instructivo_path = destino / "INSTRUCTIVO.html"
        instructivo_path.write_text(
            generar_instructivo(destino, empresa_key=None if empresa_key == "none" else empresa_key),
            encoding="utf-8",
        )
        print(f"Instructivo HTML: {instructivo_path}")
    except Exception as exc:
        print(f"(No se pudo generar INSTRUCTIVO.html: {exc})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Captura pantallas de la app y genera guía")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="URL del front")
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help="URL base de la API (default: producción IMA)",
    )
    parser.add_argument("--usuario", default=os.environ.get("CAPTURAS_USER"), help="Usuario")
    parser.add_argument("--password", default=os.environ.get("CAPTURAS_PASSWORD"), help="Contraseña")
    parser.add_argument(
        "--empresa",
        choices=sorted(EMPRESAS_PRESET.keys()),
        help="Preset de empresa (ej: la_esquina → usuario LA_ESQUINA)",
    )
    parser.add_argument(
        "--desde-db",
        action="store_true",
        help="Generar token JWT desde la DB local (no requiere contraseña)",
    )
    parser.add_argument(
        "--login-api",
        action="store_true",
        help="Login por API (más rápido). Default: login por formulario UI",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Directorio base de salida",
    )
    parser.add_argument(
        "--solo",
        nargs="*",
        help="IDs de pantallas a capturar (ej: login ventas stock). Default: todas",
    )
    parser.add_argument(
        "--visible",
        action="store_true",
        help="Mostrar navegador (no headless)",
    )
    args = parser.parse_args()

    if args.empresa:
        preset = EMPRESAS_PRESET[args.empresa]
        args.usuario = args.usuario or preset["usuario"]
        args.empresa_slug = preset["slug"]
        args.empresa_nombre = preset["nombre"]
        if not os.environ.get("CAPTURAS_BASE_URL"):
            args.base_url = DEFAULT_BASE_URL
        if not args.password and not args.login_api:
            args.desde_db = True
    else:
        args.empresa_slug = None
        args.empresa_nombre = None

    import asyncio

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
