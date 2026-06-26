#!/usr/bin/env python3
"""
Genera un instructivo HTML a partir de pantallas.py y una carpeta de capturas.

Uso:
  python scripts/capturas_pantallas/generar_instructivo_html.py \\
    --capturas docs/manual/capturas/la_esquina/20260624_201944 \\
    --empresa la_esquina
"""
from __future__ import annotations

import argparse
import html
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

_SCRIPTS_DIR = Path(__file__).resolve().parent
_ROOT = _SCRIPTS_DIR.parents[1]
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from pantallas import PANTALLAS, Pantalla  # noqa: E402

EMPRESAS_INFO: Dict[str, Dict[str, str]] = {
    "la_esquina": {
        "nombre": "LA ESQUINA",
        "url": "https://sistema-ima.sistemataup.online",
        "usuario_ejemplo": "LA_ESQUINA",
        "modo": "Modo especial (catálogo manual, sin Google Sheets)",
        "detalle": (
            "Catálogo de 5.295 productos cargado por importación CSV. "
            "Desde Stock podés consultar productos, ingresar mercadería, "
            "actualizar precios e importar/exportar el listado."
        ),
    },
}

SECCIONES: List[Dict[str, object]] = [
    {
        "id": "acceso",
        "titulo": "Acceso al sistema",
        "intro": "Primeros pasos para entrar y orientarse en el menú principal.",
        "pantallas": ["login", "dashboard"],
    },
    {
        "id": "operacion",
        "titulo": "Operación diaria",
        "intro": "Ventas de mostrador y emisión de comprobantes.",
        "pantallas": ["ventas"],
    },
    {
        "id": "contabilidad",
        "titulo": "Contabilidad",
        "intro": "Movimientos, proveedores, clientes y arqueo de caja.",
        "pantallas": [
            "contabilidad_movimientos",
            "contabilidad_proveedores",
            "contabilidad_clientes",
            "contabilidad_arqueo",
        ],
    },
    {
        "id": "stock",
        "titulo": "Stock y catálogo",
        "intro": "Gestión de productos, precios y existencias.",
        "pantallas": ["stock"],
        "extra_html": """
        <div class="callout callout-info">
          <strong>La Esquina — importación CSV</strong>
          <p>Columnas del archivo: <code>Codigo</code>, <code>Producto</code>, <code>Precio</code>,
          <code>Costo</code>, <code>Categorias</code>, <code>Stock</code>, <code>StockMinimo</code>,
          <code>CodigoBarras</code>, <code>Unidad</code>, <code>CantidadEnvase</code>, <code>Ubicacion</code>.</p>
          <ul>
            <li>En Stock → Modo especial → <em>Importar CSV</em>.</li>
            <li>La columna <code>Unidad</code> puede decir «Unidades»; el sistema la normaliza.</li>
            <li>Stock negativo en el CSV se guarda como <strong>0</strong>.</li>
            <li>Importación masiva (~5.000 filas): puede tardar ~90 segundos; no cerrar la pestaña.</li>
          </ul>
        </div>
        """,
    },
    {
        "id": "administracion",
        "titulo": "Administración",
        "intro": "Usuarios, configuración del negocio y datos fiscales.",
        "pantallas": [
            "gestion_usuarios",
            "gestion_negocio_fiscales",
            "gestion_negocio_personalizacion",
            "gestion_negocio_integraciones",
            "panel_usuario",
        ],
    },
]

ROLES_LEYENDA = {
    "Admin": "Acceso completo a configuración, contabilidad y stock.",
    "Gerente": "Contabilidad, stock y supervisión operativa.",
    "Cajero": "Ventas, mesas y cocina.",
    "Soporte": "Soporte técnico IMA (configuración avanzada).",
    "Todos": "Cualquier usuario con credenciales válidas.",
}


def _esc(texto: str) -> str:
    return html.escape(texto, quote=True)


def _pantalla_por_id() -> Dict[str, Pantalla]:
    return {p.id: p for p in PANTALLAS}


def _render_pantalla(p: Pantalla, idx: int, capturas_dir: Path) -> str:
    img_path = capturas_dir / p.archivo
    img_tag = (
        f'<img src="{_esc(p.archivo)}" alt="{_esc(p.titulo)}" loading="lazy">'
        if img_path.is_file()
        else f'<div class="img-missing">Imagen no encontrada: {_esc(p.archivo)}</div>'
    )
    roles = "".join(f'<span class="badge">{_esc(r)}</span>' for r in p.roles)
    pasos = "".join(f"<li>{_esc(paso)}</li>" for paso in p.procedimiento)
    nota = (
        f'<p class="nota"><strong>Nota:</strong> {_esc(p.notas)}</p>'
        if p.notas
        else ""
    )

    return f"""
    <article class="pantalla" id="{_esc(p.id)}">
      <header class="pantalla-header">
        <span class="numero">{idx:02d}</span>
        <div>
          <h3>{_esc(p.titulo)}</h3>
          <p class="ruta"><code>{_esc(p.ruta)}</code></p>
        </div>
      </header>
      <div class="pantalla-body">
        <figure class="captura">{img_tag}<figcaption>Captura de pantalla</figcaption></figure>
        <div class="detalle">
          <div class="roles">{roles}</div>
          <h4>¿Para qué sirve?</h4>
          <p>{_esc(p.para_que_sirve)}</p>
          <h4>Procedimiento</h4>
          <ol>{pasos}</ol>
          {nota}
        </div>
      </div>
    </article>
    """


def generar_html(
    capturas_dir: Path,
    empresa_key: Optional[str] = "la_esquina",
    titulo: str = "Instructivo — Sistema IMA",
) -> str:
    empresa = EMPRESAS_INFO.get(empresa_key or "", {})
    por_id = _pantalla_por_id()
    fecha = datetime.now().strftime("%d/%m/%Y")

    toc_items: List[str] = []
    secciones_html: List[str] = []
    contador = 1

    for sec in SECCIONES:
        sec_id = str(sec["id"])
        sec_titulo = str(sec["titulo"])
        toc_items.append(f'<li><a href="#{_esc(sec_id)}">{_esc(sec_titulo)}</a></li>')

        pantallas_html: List[str] = []
        for pid in sec["pantallas"]:
            p = por_id.get(str(pid))
            if not p:
                continue
            if not (capturas_dir / p.archivo).is_file():
                continue
            pantallas_html.append(_render_pantalla(p, contador, capturas_dir))
            contador += 1

        extra = str(sec.get("extra_html") or "")
        secciones_html.append(
            f"""
        <section class="seccion" id="{_esc(sec_id)}">
          <h2>{_esc(sec_titulo)}</h2>
          <p class="seccion-intro">{_esc(str(sec.get("intro") or ""))}</p>
          {extra}
          {"".join(pantallas_html)}
        </section>
        """
        )

    leyenda_roles = "".join(
        f"<li><span class=\"badge\">{_esc(rol)}</span> {_esc(desc)}</li>"
        for rol, desc in ROLES_LEYENDA.items()
    )

    empresa_block = ""
    if empresa:
        empresa_block = f"""
        <div class="hero-meta">
          <div><span>Empresa</span><strong>{_esc(empresa.get("nombre", ""))}</strong></div>
          <div><span>URL</span><strong><a href="{_esc(empresa.get("url", ""))}">{_esc(empresa.get("url", ""))}</a></strong></div>
          <div><span>Usuario</span><strong>{_esc(empresa.get("usuario_ejemplo", ""))}</strong></div>
          <div><span>Catálogo</span><strong>{_esc(empresa.get("modo", ""))}</strong></div>
        </div>
        <p class="hero-detalle">{_esc(empresa.get("detalle", ""))}</p>
        """

    flujo = """
    <div class="flujo">
      <div class="flujo-paso"><span>1</span><p>Login</p></div>
      <div class="flujo-flecha">→</div>
      <div class="flujo-paso"><span>2</span><p>Abrir caja</p></div>
      <div class="flujo-flecha">→</div>
      <div class="flujo-paso"><span>3</span><p>Vender</p></div>
      <div class="flujo-flecha">→</div>
      <div class="flujo-paso"><span>4</span><p>Cierre y arqueo</p></div>
    </div>
    """

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_esc(titulo)} — {_esc(empresa.get("nombre", "Sistema IMA"))}</title>
  <style>
    :root {{
      --verde-900: #14532d;
      --verde-700: #15803d;
      --verde-100: #dcfce7;
      --gris-50: #f8fafc;
      --gris-200: #e2e8f0;
      --gris-600: #475569;
      --gris-900: #0f172a;
      --sombra: 0 10px 30px rgba(15, 23, 42, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", system-ui, sans-serif;
      color: var(--gris-900);
      background: var(--gris-50);
      line-height: 1.6;
    }}
    a {{ color: var(--verde-700); }}
    .layout {{
      display: grid;
      grid-template-columns: 280px 1fr;
      min-height: 100vh;
    }}
    .sidebar {{
      position: sticky;
      top: 0;
      height: 100vh;
      overflow-y: auto;
      background: white;
      border-right: 1px solid var(--gris-200);
      padding: 1.5rem;
    }}
    .sidebar h1 {{
      font-size: 1.1rem;
      margin: 0 0 .25rem;
      color: var(--verde-900);
    }}
    .sidebar .sub {{
      font-size: .85rem;
      color: var(--gris-600);
      margin-bottom: 1rem;
    }}
    .sidebar nav ul {{
      list-style: none;
      padding: 0;
      margin: 0;
    }}
    .sidebar nav li {{ margin-bottom: .5rem; }}
    .sidebar nav a {{
      text-decoration: none;
      color: var(--gris-900);
      display: block;
      padding: .45rem .65rem;
      border-radius: .5rem;
    }}
    .sidebar nav a:hover {{ background: var(--verde-100); }}
    main {{ padding: 2rem 2.5rem 4rem; max-width: 1100px; }}
    .hero {{
      background: linear-gradient(135deg, var(--verde-900), var(--verde-700));
      color: white;
      border-radius: 1rem;
      padding: 2rem;
      margin-bottom: 2rem;
      box-shadow: var(--sombra);
    }}
    .hero h2 {{ margin: 0 0 .5rem; font-size: 1.8rem; }}
    .hero p {{ margin: 0; opacity: .95; }}
    .hero-meta {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 1rem;
      margin-top: 1.5rem;
    }}
    .hero-meta div {{
      background: rgba(255,255,255,.12);
      border-radius: .75rem;
      padding: .85rem 1rem;
    }}
    .hero-meta span {{
      display: block;
      font-size: .75rem;
      opacity: .8;
      text-transform: uppercase;
      letter-spacing: .04em;
    }}
    .hero-meta a {{ color: white; }}
    .hero-detalle {{ margin-top: 1rem; opacity: .95; }}
    .flujo {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: .75rem;
      margin: 1.5rem 0 2rem;
    }}
    .flujo-paso {{
      background: white;
      border: 1px solid var(--gris-200);
      border-radius: .75rem;
      padding: .75rem 1rem;
      min-width: 110px;
      text-align: center;
      box-shadow: var(--sombra);
    }}
    .flujo-paso span {{
      display: inline-flex;
      width: 1.75rem;
      height: 1.75rem;
      align-items: center;
      justify-content: center;
      border-radius: 999px;
      background: var(--verde-700);
      color: white;
      font-weight: 700;
      margin-bottom: .35rem;
    }}
    .flujo-paso p {{ margin: 0; font-size: .9rem; }}
    .flujo-flecha {{ color: var(--gris-600); font-size: 1.2rem; }}
    .seccion {{ margin-bottom: 3rem; }}
    .seccion h2 {{
      font-size: 1.5rem;
      color: var(--verde-900);
      border-bottom: 3px solid var(--verde-100);
      padding-bottom: .5rem;
      margin-bottom: .75rem;
    }}
    .seccion-intro {{ color: var(--gris-600); margin-bottom: 1.5rem; }}
    .pantalla {{
      background: white;
      border: 1px solid var(--gris-200);
      border-radius: 1rem;
      margin-bottom: 1.5rem;
      overflow: hidden;
      box-shadow: var(--sombra);
    }}
    .pantalla-header {{
      display: flex;
      gap: 1rem;
      align-items: center;
      padding: 1rem 1.25rem;
      background: var(--gris-50);
      border-bottom: 1px solid var(--gris-200);
    }}
    .numero {{
      width: 2.5rem;
      height: 2.5rem;
      border-radius: .75rem;
      background: var(--verde-700);
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      flex-shrink: 0;
    }}
    .pantalla-header h3 {{ margin: 0; font-size: 1.15rem; }}
    .ruta {{ margin: .15rem 0 0; font-size: .85rem; color: var(--gris-600); }}
    .pantalla-body {{
      display: grid;
      grid-template-columns: minmax(280px, 1.1fr) minmax(260px, .9fr);
      gap: 0;
    }}
    .captura {{
      margin: 0;
      background: #eef2f7;
      border-right: 1px solid var(--gris-200);
    }}
    .captura img {{
      width: 100%;
      display: block;
      object-fit: contain;
      max-height: 520px;
      background: #dbeafe;
    }}
    .captura figcaption {{
      padding: .5rem 1rem;
      font-size: .8rem;
      color: var(--gris-600);
      background: white;
    }}
    .img-missing {{
      padding: 2rem;
      color: #b91c1c;
      background: #fef2f2;
    }}
    .detalle {{ padding: 1.25rem; }}
    .detalle h4 {{
      margin: 1rem 0 .35rem;
      font-size: .95rem;
      color: var(--verde-900);
    }}
    .detalle h4:first-of-type {{ margin-top: 0; }}
    .detalle ol {{ margin: 0; padding-left: 1.2rem; }}
    .detalle li {{ margin-bottom: .35rem; }}
    .roles {{ display: flex; flex-wrap: wrap; gap: .35rem; margin-bottom: .5rem; }}
    .badge {{
      display: inline-block;
      background: var(--verde-100);
      color: var(--verde-900);
      font-size: .75rem;
      font-weight: 600;
      padding: .2rem .55rem;
      border-radius: 999px;
    }}
    .nota {{
      margin-top: 1rem;
      padding: .75rem .9rem;
      background: #fffbeb;
      border-left: 4px solid #f59e0b;
      border-radius: .35rem;
      font-size: .92rem;
    }}
    .callout {{
      border-radius: .75rem;
      padding: 1rem 1.15rem;
      margin-bottom: 1.25rem;
    }}
    .callout-info {{
      background: #eff6ff;
      border: 1px solid #bfdbfe;
    }}
    .callout ul {{ margin: .5rem 0 0; padding-left: 1.2rem; }}
    .leyenda {{
      background: white;
      border: 1px solid var(--gris-200);
      border-radius: 1rem;
      padding: 1.25rem;
      margin-bottom: 2rem;
    }}
    .leyenda ul {{ margin: .5rem 0 0; padding-left: 0; list-style: none; }}
    .leyenda li {{ margin-bottom: .45rem; }}
    footer {{
      margin-top: 2rem;
      color: var(--gris-600);
      font-size: .85rem;
    }}
    @media (max-width: 960px) {{
      .layout {{ grid-template-columns: 1fr; }}
      .sidebar {{ position: static; height: auto; }}
      .pantalla-body {{ grid-template-columns: 1fr; }}
      .captura {{ border-right: none; border-bottom: 1px solid var(--gris-200); }}
      main {{ padding: 1rem; }}
    }}
    @media print {{
      .sidebar {{ display: none; }}
      .layout {{ display: block; }}
      main {{ max-width: none; padding: 0; }}
      .pantalla {{ break-inside: avoid; box-shadow: none; page-break-inside: avoid; }}
      .pantalla-body {{ grid-template-columns: 1fr; }}
      .captura img {{ max-height: 380px; }}
      .hero {{ break-after: page; }}
    }}
  </style>
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      <h1>{_esc(titulo)}</h1>
      <p class="sub">{_esc(empresa.get("nombre", "Sistema IMA"))} · {fecha}</p>
      <nav>
        <ul>
          <li><a href="#inicio">Inicio</a></li>
          {''.join(toc_items)}
          <li><a href="#roles">Roles</a></li>
        </ul>
      </nav>
    </aside>
    <main>
      <section class="hero" id="inicio">
        <h2>Manual de uso del sistema</h2>
        <p>Instructivo visual con capturas reales de cada pantalla, explicando para qué sirve y cómo operar.</p>
        {empresa_block}
        {flujo}
      </section>

      <section class="leyenda" id="roles">
        <h2>Roles del sistema</h2>
        <ul>{leyenda_roles}</ul>
      </section>

      {''.join(secciones_html)}

      <footer>
        <p>Generado el {fecha} · IMA Consultoría · Sistema de gestión comercial</p>
        <p>Las capturas corresponden al entorno de producción. La Esquina opera con modo especial (sin módulo de mesas/cocina).</p>
      </footer>
    </main>
  </div>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera instructivo HTML desde capturas")
    parser.add_argument(
        "--capturas",
        type=Path,
        required=True,
        help="Carpeta con PNG y capturas",
    )
    parser.add_argument(
        "--empresa",
        default="la_esquina",
        choices=list(EMPRESAS_INFO.keys()) + ["none"],
        help="Preset de empresa para el encabezado",
    )
    parser.add_argument(
        "--salida",
        type=Path,
        default=None,
        help="Archivo HTML de salida (default: INSTRUCTIVO.html en carpeta capturas)",
    )
    parser.add_argument(
        "--pdf",
        action="store_true",
        help="Generar también INSTRUCTIVO.pdf con Playwright",
    )
    args = parser.parse_args()

    capturas_dir = args.capturas.resolve()
    if not capturas_dir.is_dir():
        raise SystemExit(f"No existe la carpeta: {capturas_dir}")

    empresa_key = None if args.empresa == "none" else args.empresa
    contenido = generar_html(capturas_dir, empresa_key=empresa_key)
    salida = args.salida or (capturas_dir / "INSTRUCTIVO.html")
    salida.write_text(contenido, encoding="utf-8")
    print(f"Instructivo generado: {salida}")

    if args.pdf:
        pdf_path = capturas_dir / "INSTRUCTIVO.pdf"
        _generar_pdf(salida, pdf_path)
        print(f"PDF generado: {pdf_path}")


async def _generar_pdf_async(html_path: Path, pdf_path: Path) -> None:
    from playwright.async_api import async_playwright

    url = html_path.resolve().as_uri()
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle", timeout=120000)
        await page.pdf(
            path=str(pdf_path),
            format="A4",
            print_background=True,
            margin={"top": "12mm", "bottom": "12mm", "left": "10mm", "right": "10mm"},
        )
        await browser.close()


def _generar_pdf(html_path: Path, pdf_path: Path) -> None:
    import asyncio

    asyncio.run(_generar_pdf_async(html_path, pdf_path))


if __name__ == "__main__":
    main()
