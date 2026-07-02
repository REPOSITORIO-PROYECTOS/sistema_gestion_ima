# Capturas de pantallas — Sistema IMA

Script para generar capturas automáticas de las pantallas principales y una guía Markdown con:

- Para qué sirve cada pantalla
- Procedimiento paso a paso
- Roles que pueden acceder

## Requisitos

```bash
cd /home/dev_taup/proyectos/sistema_gestion_ima
.venv/bin/pip install -r scripts/capturas_pantallas/requirements.txt
.venv/bin/playwright install chromium
```

El front debe estar corriendo (ej. `cd front && npm run dev` → `http://127.0.0.1:3000`).

## Uso

```bash
# Todas las pantallas de La Esquina (sin contraseña, token desde DB local)
.venv/bin/python scripts/capturas_pantallas/capturar.py --empresa la_esquina

# Solo algunas pantallas
.venv/bin/python scripts/capturas_pantallas/capturar.py \
  --usuario LA_ESQUINA --password 'tu_clave' \
  --solo login ventas stock

# Ver el navegador mientras captura
.venv/bin/python scripts/capturas_pantallas/capturar.py \
  --usuario LA_ESQUINA --password 'tu_clave' --visible
```

## Salida

```
docs/manual/capturas/<YYYYMMDD_HHMMSS>/
  01_login.png
  02_dashboard.png
  ...
  GUIA_PANTALLAS.md
```

## Pantallas incluidas

| ID | Pantalla |
|----|----------|
| `login` | Inicio de sesión |
| `dashboard` | Panel principal |
| `ventas` | POS / Caja |
| `mesas` | Mesas y consumos |
| `cocina` | Monitor de cocina |
| `contabilidad_movimientos` | Movimientos de caja |
| `contabilidad_proveedores` | Proveedores |
| `contabilidad_clientes` | Clientes |
| `contabilidad_arqueo` | Arqueo |
| `stock` | Stock / modo especial |
| `gestion_usuarios` | Usuarios |
| `gestion_negocio_*` | Pestañas de gestión de negocio |
| `panel_usuario` | Panel de usuario |

## Instructivo HTML

Tras capturar (o manualmente):

```bash
.venv/bin/python scripts/capturas_pantallas/generar_instructivo_html.py \
  --capturas docs/manual/capturas/la_esquina/20260624_201944 \
  --empresa la_esquina
```

Genera `INSTRUCTIVO.html` en la misma carpeta de las imágenes. Abrilo en el navegador: es un manual visual con índice lateral, capturas, procedimientos y notas específicas de La Esquina (modo especial, importación CSV).

El script `capturar.py` también intenta generarlo automáticamente al finalizar.

## Variables de entorno

| Variable | Descripción |
|----------|-------------|
| `CAPTURAS_BASE_URL` | URL del front (default `http://127.0.0.1:3000`) |
| `CAPTURAS_API_URL` | URL de la API para `--login-api` (default producción IMA) |
| `CAPTURAS_USER` | Usuario |
| `CAPTURAS_PASSWORD` | Contraseña |

## Notas

- Por defecto el login se hace **por el formulario** (más compatible con cualquier deploy).
- Usá `--login-api` si la API responde en `/api/auth/token` y querés ir más rápido.
- Si capturás `login` junto con otras pantallas, el script limpia la sesión solo para esa captura y re-inyecta el token para el resto.
