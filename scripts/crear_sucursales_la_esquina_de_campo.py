#!/usr/bin/env python3
"""DEPRECATED: usar scripts/revertir_y_crear_demo_esquina2.py (no toca prod 35/36)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "revertir_y_crear_demo_esquina2.py"

if __name__ == "__main__":
    print("Este script fue reemplazado por revertir_y_crear_demo_esquina2.py")
    raise SystemExit(
        subprocess.call([sys.executable, str(SCRIPT)], cwd=str(ROOT))
    )
