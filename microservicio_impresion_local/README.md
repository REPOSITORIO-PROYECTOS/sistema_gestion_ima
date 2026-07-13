# Microservicio Local de Impresion (Windows)

Este servicio corre localmente y recibe trabajos de impresion desde el frontend, evitando `window.print()` y el dialogo del navegador.

## Endpoints

- `GET /health`
- `GET /` (panel web de estado)
- `POST /print/html`
- `POST /print/pdf`

## Modo MVP de este sprint

- Guarda cada trabajo en `spool/`.
- Simula la impresion en consola (`simulate_only=true`).
- No toca calculos ni logica de comprobantes del backend.

## Configuracion

Archivo `config.json` (se crea automaticamente al primer arranque):

```json
{
  "enabled": true,
  "simulate_only": true,
  "host": "127.0.0.1",
  "port": 18777,
  "api_key": null
}
```

## Ejecutar en desarrollo

```powershell
cd microservicio_impresion_local
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python print_service.py
```

## Compilar .exe

```powershell
cd microservicio_impresion_local
build_exe.bat
```

Genera: `dist/microservicio_impresion_local.exe`

## Ejecutar en segundo plano

Inicio manual en segundo plano:

```powershell
cd microservicio_impresion_local
powershell -ExecutionPolicy Bypass -File .\run_background.ps1
```

Detener servicio:

```powershell
cd microservicio_impresion_local
powershell -ExecutionPolicy Bypass -File .\stop_background.ps1
```

## Iniciar automaticamente con Windows (logon)

Instalar tarea programada:

```powershell
cd microservicio_impresion_local
powershell -ExecutionPolicy Bypass -File .\install_startup_task.ps1
```

Desinstalar tarea:

```powershell
cd microservicio_impresion_local
powershell -ExecutionPolicy Bypass -File .\uninstall_startup_task.ps1
```

## Panel web

Una vez corriendo, abrir:

- `http://127.0.0.1:18777/`

Vas a ver:

- Estado ACTIVO
- Modo de ejecucion (EXE/PYTHON)
- Uptime
- Cantidad de trabajos en spool
- Ruta de spool y endpoints

## Integracion con frontend

El frontend usa por defecto `http://127.0.0.1:18777`.

Si queres otro puerto/url:

- `NEXT_PUBLIC_LOCAL_PRINT_URL=http://127.0.0.1:18777`

Si definis `api_key` en `config.json`, el frontend debe enviarla:

- `NEXT_PUBLIC_LOCAL_PRINT_API_KEY=tu_clave_local`
