"""
Worker dedicado para APScheduler (sync Google Sheets + cola sync_nube).

Correr aparte del API HTTP para no competir con polling/ventas:
  API_ENABLE_SCHEDULER=false en gestion-ima-api
  python -m back.sync_worker   (o PM2 gestion-ima-sync)
"""
from __future__ import annotations

import logging
import signal
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [sync-worker] %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    from back.scheduler import init_scheduler, shutdown_scheduler

    logger.info("Iniciando worker de sincronización...")
    init_scheduler()

    def _shutdown(*_args: object) -> None:
        logger.info("Deteniendo scheduler...")
        shutdown_scheduler()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    logger.info("Scheduler activo. Esperando jobs...")
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
