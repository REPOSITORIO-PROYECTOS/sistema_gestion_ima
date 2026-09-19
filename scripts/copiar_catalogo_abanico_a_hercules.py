#!/usr/bin/env python3
"""
Copia idempotente del catálogo de El Abanico (40) → Panadería Hercules (41).

Usa exportar_csv + importar_csv (modo especial): precios, costos, categorías y
códigos de barras. Stock destino = 0 (empresa nueva; no copia stock negativo
ni saldos de Abanico).

Conserva PANADERIA (002992) y GOLOSINAS (000498) ya cargados en Hercules.

Uso (S1):
  export PYTHONPATH=/home/dev_taup/proyectos/sistema_gestion_ima:$PYTHONPATH
  set -a && . .env && set +a
  back/venv/bin/python scripts/copiar_catalogo_abanico_a_hercules.py
  back/venv/bin/python scripts/copiar_catalogo_abanico_a_hercules.py --dry-run
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlmodel import Session, select

from back.database import engine
from back.gestion import modo_especial_manager
from back.modelos import Articulo, ConfiguracionEmpresa

ID_ORIGEN = 40  # El Abanico
ID_DESTINO = 41  # Panadería Hercules
# Productos base de Hercules: no pisar con el export de Abanico (no los tiene).
CODIGOS_RESERVADOS = frozenset({"002992", "000498"})


def _forzar_stock_cero_en_csv(contenido: str) -> str:
    """Reescribe Stock=0 en todas las filas del CSV exportado."""
    reader = csv.DictReader(io.StringIO(contenido))
    if not reader.fieldnames:
        return contenido
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=reader.fieldnames, lineterminator="\n")
    writer.writeheader()
    for fila in reader:
        if "Stock" in fila:
            fila["Stock"] = "0"
        writer.writerow(fila)
    return out.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Copiar catálogo El Abanico → Panadería Hercules"
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("=== Copiar catálogo Abanico → Hercules ===")
    print(f"  Origen:  empresa {ID_ORIGEN}")
    print(f"  Destino: empresa {ID_DESTINO}")
    print(f"  Stock destino: 0")
    print(f"  Reservados (no tocar): {', '.join(sorted(CODIGOS_RESERVADOS))}")

    with Session(engine) as db:
        n_origen = len(
            db.exec(
                select(Articulo).where(
                    Articulo.id_empresa == ID_ORIGEN, Articulo.activo == True  # noqa: E712
                )
            ).all()
        )
        n_destino_antes = len(
            db.exec(
                select(Articulo).where(
                    Articulo.id_empresa == ID_DESTINO, Articulo.activo == True  # noqa: E712
                )
            ).all()
        )
        print(f"  Activos origen: {n_origen}")
        print(f"  Activos destino (antes): {n_destino_antes}")

        csv_raw = modo_especial_manager.exportar_csv(db, ID_ORIGEN)
        csv_stock0 = _forzar_stock_cero_en_csv(csv_raw)
        filas = list(csv.DictReader(io.StringIO(csv_stock0)))
        print(f"  Filas CSV: {len(filas)}")

        if args.dry_run:
            print("  [dry-run] No se escribe nada.")
            muestra = filas[:5]
            for f in muestra:
                print(
                    f"    · {f.get('Codigo')} {f.get('Producto')} "
                    f"pv={f.get('Precio')} cat={f.get('Categorias')}"
                )
            return 0

        resumen = modo_especial_manager.importar_csv(db, ID_DESTINO, csv_stock0)
        print(
            f"  Import: creados={resumen.creados} "
            f"actualizados={resumen.actualizados} errores={resumen.errores}"
        )
        if resumen.detalle_errores:
            for err in resumen.detalle_errores[:20]:
                print(f"    ! {err}")
            if len(resumen.detalle_errores) > 20:
                print(f"    … +{len(resumen.detalle_errores) - 20} errores más")

        # Asegurar stock 0 en todo el destino (por si algún update dejó resto).
        arts = db.exec(
            select(Articulo).where(Articulo.id_empresa == ID_DESTINO)
        ).all()
        for art in arts:
            if art.codigo_interno in CODIGOS_RESERVADOS:
                continue
            if (art.stock_actual or 0) != 0:
                art.stock_actual = 0.0
                db.add(art)
        cfg = db.get(ConfiguracionEmpresa, ID_DESTINO)
        if cfg is not None:
            cfg.catalogo_version = int(cfg.catalogo_version or 0) + 1
            db.add(cfg)
        db.commit()

        n_destino = len(
            db.exec(
                select(Articulo).where(
                    Articulo.id_empresa == ID_DESTINO, Articulo.activo == True  # noqa: E712
                )
            ).all()
        )
        base = db.exec(
            select(Articulo).where(
                Articulo.id_empresa == ID_DESTINO,
                Articulo.codigo_interno.in_(list(CODIGOS_RESERVADOS)),
            )
        ).all()
        print("\n=== Resumen ===")
        print(f"  Activos destino (después): {n_destino}")
        print(f"  Esperado ≈ {n_origen + len(CODIGOS_RESERVADOS)} (Abanico + base)")
        for art in base:
            print(
                f"  Base OK: {art.codigo_interno} {art.descripcion} "
                f"pm={art.precio_manual}"
            )

    return 0 if resumen.errores == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
