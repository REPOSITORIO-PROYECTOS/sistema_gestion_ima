#!/usr/bin/env python3
"""
Diagnóstico de alineación MOVIMIENTOS (solo lectura).

Uso:
  python testing/diag_movimientos_columnas.py
  python testing/diag_movimientos_columnas.py --id-empresa 1
  python testing/diag_movimientos_columnas.py --buscar-swing
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sqlmodel import Session, select

from back.database import engine
from back.modelos import ConfiguracionEmpresa, Empresa
from back.utils.tablas_handler import TablasHandler

PAYLOAD_EJEMPLO: Dict[str, Any] = {
    "id_cliente": "0",
    "id_ingresos": "99999",
    "id_repartidor": "",
    "Repartidor": "cajero_swing",
    "cliente": "cliente final",
    "cuit": "-",
    "razon_social": "-",
    "Tipo_movimiento": "[ticket] Venta en EFECTIVO",
    "nro_comprobante": "",
    "descripcion": "Venta de prueba diagnostico",
    "monto": 1500.50,
    "foto_comprobante": "",
    "observaciones": "",
}

FIXTURES_PATH = Path(__file__).parent / "fixtures" / "movimientos_encabezados_swing.json"


def _listar_empresas_con_sheets(db: Session) -> List[ConfiguracionEmpresa]:
    return list(
        db.exec(
            select(ConfiguracionEmpresa)
            .where(ConfiguracionEmpresa.link_google_sheets.isnot(None))
            .where(ConfiguracionEmpresa.link_google_sheets != "")
        ).all()
    )


def _resolver_id_empresa(db: Session, buscar_swing: bool, id_empresa: Optional[int]) -> int:
    if id_empresa is not None:
        return id_empresa

    if buscar_swing:
        empresas = db.exec(select(Empresa)).all()
        for emp in empresas:
            nombre = f"{emp.nombre_fantasia or ''} {emp.nombre_legal or ''}".lower()
            if "swing" in nombre:
                print(f"Empresa Swing detectada: id={emp.id} ({emp.nombre_fantasia or emp.nombre_legal})")
                return emp.id
        configs = _listar_empresas_con_sheets(db)
        for cfg in configs:
            negocio = (cfg.nombre_negocio or "").lower()
            if "swing" in negocio:
                print(f"Empresa Swing detectada por nombre_negocio: id={cfg.id_empresa} ({cfg.nombre_negocio})")
                return cfg.id_empresa
        raise SystemExit("No se encontró empresa con 'Swing' en nombre legal/fantasía/negocio.")

    configs = _listar_empresas_con_sheets(db)
    if not configs:
        raise SystemExit("No hay empresas con Google Sheets configurado.")
    if len(configs) == 1:
        return configs[0].id_empresa

    print("Empresas con Google Sheets:")
    for c in configs:
        emp = db.get(Empresa, c.id_empresa)
        nombre = (emp.nombre_fantasia or emp.nombre_legal) if emp else c.nombre_negocio
        print(f"  id={c.id_empresa}  {nombre}")
    raise SystemExit("Indique --id-empresa N o --buscar-swing")


def _letra_columna(indice: int) -> str:
    import gspread

    return gspread.utils.rowcol_to_a1(1, indice + 1)[:-1]


def diagnosticar_movimientos(id_empresa: int, guardar_fixture: bool) -> bool:
    with Session(engine) as db:
        config = db.get(ConfiguracionEmpresa, id_empresa)
        if not config or not config.link_google_sheets:
            print(f"Empresa {id_empresa} sin link_google_sheets")
            return False

        handler = TablasHandler(id_empresa=id_empresa, db=db)
        if not handler.client:
            print("Cliente Google Sheets no disponible (credenciales).")
            return False

        sheet = handler._abrir_planilla()
        hoja = handler._obtener_worksheet_flexible(
            sheet,
            ["MOVIMIENTOS", "Movimientos", "movimientos", "movimiento", "Movimiento"],
        )
        encabezados = hoja.row_values(1)
        ultima_fila: List[str] = []
        if hoja.row_count > 1:
            ultima_fila = hoja.row_values(hoja.row_count)

        diag = handler.diagnosticar_fila_movimiento(PAYLOAD_EJEMPLO, encabezados=encabezados)

        print(f"\n{'=' * 72}")
        print(f"DIAGNÓSTICO MOVIMIENTOS — empresa id={id_empresa}")
        print(f"Hoja: {hoja.title!r}  |  columnas fila 1: {len(encabezados)}")
        print(f"{'=' * 72}\n")

        print(f"{'Col':<5} {'Encabezado':<28} {'Clave norm.':<24} {'Mapea':<6} Valor simulado")
        print("-" * 72)
        for item in diag["detalle"]:
            valor = item["valor"][:40] + ("…" if len(item["valor"]) > 40 else "")
            print(
                f"{item['columna']:<5} {item['encabezado'][:28]:<28} "
                f"{item['clave_normalizada'][:24]:<24} {item['mapea']:<6} {valor}"
            )

        sin_mapeo = diag["sin_mapeo"]
        if sin_mapeo:
            print(f"\nEncabezados DESCONOCIDOS (sin clave en backend) ({len(sin_mapeo)}):")
            for h in sin_mapeo:
                print(f"  - {h!r}")
        else:
            print("\nTodos los encabezados con título están reconocidos por el backend.")

        if encabezados and encabezados[0].strip() == "":
            print("\nAVISO: A1 está vacío — las filas nuevas empiezan con columna A vacía (offset +1).")

        if ultima_fila:
            print(f"\nComparación con última fila de la hoja (fila {hoja.row_count}):")
            print(f"{'Col':<5} {'Encabezado':<22} {'Simulado':<22} {'Última fila':<22}")
            print("-" * 72)
            for idx, col in enumerate(encabezados):
                sim = diag["fila"][idx] if idx < len(diag["fila"]) else ""
                real = ultima_fila[idx] if idx < len(ultima_fila) else ""
                marca = "  " if str(sim) == str(real) or (not sim and not real) else "≠"
                print(
                    f"{_letra_columna(idx):<5} {(col or '(vacío)')[:22]:<22} "
                    f"{str(sim)[:22]:<22} {str(real)[:22]:<22}{marca}"
                )

        # Fórmulas en fila 2 (referencias legacy, ej. columna Y)
        if hoja.row_count >= 2:
            fila_formulas = hoja.row_values(2, value_render_option="FORMULA")
            con_formula = [
                (_letra_columna(i), encabezados[i] if i < len(encabezados) else "", fila_formulas[i])
                for i, val in enumerate(fila_formulas)
                if val and str(val).startswith("=")
            ]
            if con_formula:
                print(f"\nFórmulas detectadas en fila 2 ({len(con_formula)}):")
                for letra, enc, formula in con_formula[:15]:
                    print(f"  {letra} ({enc[:20]}): {formula[:60]}")
                cols_criticas = {"Y", "M", "N", "O", "P"}
                refs = [c for c, _, _ in con_formula if c in cols_criticas]
                if refs:
                    print(f"  Columnas con fórmulas legacy frecuentes: {', '.join(sorted(set(refs)))}")

        if guardar_fixture:
            FIXTURES_PATH.parent.mkdir(parents=True, exist_ok=True)
            FIXTURES_PATH.write_text(
                json.dumps({"encabezados": encabezados, "payload_ejemplo": PAYLOAD_EJEMPLO}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"\nFixture guardado: {FIXTURES_PATH}")

        return len(sin_mapeo) == 0 and (not encabezados or encabezados[0].strip() != "")


def diagnosticar_desde_fixture() -> bool:
    """Diagnóstico offline con fixture Swing (sin llamadas a Google Sheets)."""
    if not FIXTURES_PATH.exists():
        print(f"No existe fixture: {FIXTURES_PATH}")
        return False
    fixture = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    handler = TablasHandler.__new__(TablasHandler)
    diag = handler.diagnosticar_fila_movimiento(
        fixture.get("payload_ejemplo", PAYLOAD_EJEMPLO),
        encabezados=fixture["encabezados"],
    )
    print("Diagnóstico offline (fixture Swing)")
    for item in diag["detalle"]:
        print(f"  {item['columna']}: {item['encabezado']!r} -> {item['mapea']}")
    if diag["sin_mapeo"]:
        print("Encabezados desconocidos:", diag["sin_mapeo"])
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnóstico columnas MOVIMIENTOS")
    parser.add_argument("--id-empresa", type=int, default=None)
    parser.add_argument("--buscar-swing", action="store_true")
    parser.add_argument("--guardar-fixture", action="store_true")
    parser.add_argument(
        "--solo-fixture",
        action="store_true",
        help="Usar fixture local sin conectar a Google Sheets",
    )
    args = parser.parse_args()

    if args.solo_fixture:
        ok = diagnosticar_desde_fixture()
        sys.exit(0 if ok else 1)

    with Session(engine) as db:
        id_empresa = _resolver_id_empresa(db, args.buscar_swing, args.id_empresa)

    ok = diagnosticar_movimientos(id_empresa, guardar_fixture=args.guardar_fixture)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
