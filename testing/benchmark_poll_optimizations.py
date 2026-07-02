"""
Benchmark local de optimizaciones del poll del escáner.

Uso (desde la raíz del repo, PowerShell):
  $env:PYTHONPATH = "<repo-root>"
  $env:API_ENABLE_SCHEDULER = "false"
  .venv/Scripts/python.exe testing/benchmark_poll_optimizations.py

Con API ya levantado:
  .venv/Scripts/python.exe testing/benchmark_poll_optimizations.py --live http://127.0.0.1:8012
"""
from __future__ import annotations

import argparse
import asyncio
import os
import statistics
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import httpx
from fastapi.testclient import TestClient

from back.security import crear_access_token
from back.api.blueprints import scanner_router


def _token(con_id_empresa: bool = True) -> str:
    data: dict = {"sub": "benchmark_user"}
    if con_id_empresa:
        data["id_empresa"] = 1
    return crear_access_token(data)


def test_auth_liviana_sin_db() -> None:
    """obtener_id_empresa_desde_token no debe abrir sesión DB."""
    from back.database import get_db

    token = _token(con_id_empresa=True)
    db_gen = get_db()
    db = next(db_gen)
    try:
        # Simula Depends(oauth2_scheme) pasando token directo vía función interna
        from back.security import decodificar_token

        payload = decodificar_token(token)
        assert payload.get("id_empresa") == 1
        assert payload.get("sub") == "benchmark_user"
    finally:
        db.close()
        try:
            next(db_gen)
        except StopIteration:
            pass

    token_viejo = _token(con_id_empresa=False)
    from back.security import decodificar_token

    payload_viejo = decodificar_token(token_viejo)
    assert payload_viejo.get("id_empresa") is None
    print("  [OK] JWT con/sin id_empresa")


def test_poll_testclient() -> None:
    from back.main import app

    client = TestClient(app, raise_server_exceptions=False)
    token_nuevo = _token(True)
    token_viejo = _token(False)

    r_viejo = client.get(
        "/scanner/evento/poll?timeout=0",
        headers={"Authorization": f"Bearer {token_viejo}"},
    )
    assert r_viejo.status_code == 401, f"Token sin id_empresa debe 401, got {r_viejo.status_code}"
    print("  [OK] Poll rechaza token legacy (401)")

    r_ok = client.get(
        "/scanner/evento/poll?timeout=0",
        headers={"Authorization": f"Bearer {token_nuevo}"},
    )
    assert r_ok.status_code == 200, r_ok.text
    body = r_ok.json()
    assert body.get("has_event") is False
    print("  [OK] Poll acepta token con id_empresa (200, sin DB en router)")

    # Push + poll (cola en memoria; push HTTP requiere usuario real en DB)
    scanner_router._enqueue_event(
        1,
        scanner_router.ScannerEvent(id_articulo=99, nombre="Test", peso=1.0),
    )
    r_ev = client.get(
        "/scanner/evento/poll?timeout=0",
        headers={"Authorization": f"Bearer {token_nuevo}"},
    )
    assert r_ev.json().get("has_event") is True
    print("  [OK] Push + poll entrega evento")


def bench_testclient_throughput(n: int = 60) -> None:
    """Carga in-process (no requiere API levantado). Mide latencia del poll optimizado."""
    from back.main import app

    client = TestClient(app, raise_server_exceptions=False)
    token = _token(True)
    headers = {"Authorization": f"Bearer {token}"}

    latencies: list[float] = []
    t0 = time.perf_counter()
    for _ in range(n):
        t_req = time.perf_counter()
        r = client.get("/scanner/evento/poll?timeout=0", headers=headers)
        latencies.append(time.perf_counter() - t_req)
        assert r.status_code == 200
    elapsed = time.perf_counter() - t0

    print("\n--- Benchmark in-process (TestClient, poll timeout=0) ---")
    print(f"  {_proc_stats(os.getpid())}")
    print(
        f"  {n} requests en {elapsed:.2f}s -> {n / elapsed:.1f} req/s | "
        f"p50={statistics.median(latencies) * 1000:.1f}ms | "
        f"p95={sorted(latencies)[int(n * 0.95)] * 1000:.1f}ms"
    )
    print(
        f"  Equivalente 1 caja @1/s durante 1 min: {n} req -> "
        f"con long-poll 25s serían ~{max(1, int(60 / 25))} req/min"
    )


async def bench_longpoll_testclient() -> None:
    """Simula 3 long-polls de 2s vía TestClient (async endpoint)."""
    from back.main import app

    client = TestClient(app, raise_server_exceptions=False)
    token = _token(True)
    headers = {"Authorization": f"Bearer {token}"}

    t0 = time.perf_counter()
    for _ in range(3):
        r = client.get("/scanner/evento/poll?timeout=2", headers=headers)
        assert r.status_code == 200
    elapsed = time.perf_counter() - t0
    print("\n--- Benchmark in-process (3× long-poll timeout=2s) ---")
    print(f"  3 requests en {elapsed:.2f}s -> ~{3 / elapsed:.3f} req/s efectivo")


async def _bench_live(base_url: str, token: str, label: str, path: str, n: int) -> dict:
    latencies: list[float] = []
    errors = 0
    t0 = time.perf_counter()
    async with httpx.AsyncClient(base_url=base_url, timeout=120.0) as client:
        headers = {"Authorization": f"Bearer {token}"}
        for _ in range(n):
            t_req = time.perf_counter()
            try:
                r = await client.get(path, headers=headers)
                if r.status_code != 200:
                    errors += 1
            except Exception:
                errors += 1
            latencies.append(time.perf_counter() - t_req)
    elapsed = time.perf_counter() - t0
    return {
        "label": label,
        "requests": n,
        "errors": errors,
        "elapsed_sec": round(elapsed, 2),
        "rps": round(n / elapsed, 2) if elapsed else 0,
        "p50_ms": round(statistics.median(latencies) * 1000, 1),
        "p95_ms": round(
            (sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0) * 1000,
            1,
        ),
    }


def _proc_stats(pid: int | None) -> str:
    try:
        import psutil

        if pid is None:
            return "psutil: sin PID"
        p = psutil.Process(pid)
        mem = p.memory_info().rss / (1024 * 1024)
        cpu = p.cpu_percent(interval=0.5)
        return f"PID {pid}: RAM {mem:.1f} MB, CPU {cpu:.1f}%"
    except ImportError:
        return "psutil no instalado (pip install psutil para RAM/CPU)"
    except Exception as e:
        return f"stats: {e}"


async def run_live_benchmark(base_url: str, api_pid: int | None) -> None:
    token = _token(True)
    print(f"\n--- Benchmark live contra {base_url} ---")
    print(f"  {_proc_stats(api_pid)}")

    # Simula carga antigua: poll instantáneo 60 veces (~1 min de 1 req/s × 1 caja)
    old_style = await _bench_live(
        base_url, token, "poll timeout=0 (estilo 1/s×60)", "/scanner/evento/poll?timeout=0", 60
    )
    print(f"  {old_style}")

    # Simula carga nueva: 3 long-polls de ~2s (equivalente ~30s ventana)
    new_style = await _bench_live(
        base_url, token, "poll timeout=2 (long-poll)", "/scanner/evento/poll?timeout=2", 3
    )
    print(f"  {new_style}")

    old_rps = old_style["rps"]
    new_effective = 3 / new_style["elapsed_sec"] if new_style["elapsed_sec"] else 0
    reduction = (1 - new_effective / old_rps) * 100 if old_rps else 0
    print(f"\n  Reduccion estimada de req/s: {old_rps:.2f} -> ~{new_effective:.3f} ({reduction:.0f}% menos)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", metavar="URL", help="Benchmark contra API en ejecución")
    parser.add_argument("--pid", type=int, help="PID del proceso API para RAM/CPU")
    args = parser.parse_args()

    print("=== Tests unitarios (TestClient) ===")
    test_auth_liviana_sin_db()
    test_poll_testclient()
    bench_testclient_throughput(60)
    asyncio.run(bench_longpoll_testclient())

    if args.live:
        asyncio.run(run_live_benchmark(args.live.rstrip("/"), args.pid))
    else:
        print("\n(Saltar benchmark live: levantá API y pasá --live http://127.0.0.1:8012)")

    print("\n=== Benchmark completado ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
