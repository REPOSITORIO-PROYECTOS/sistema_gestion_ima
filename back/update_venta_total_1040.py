import sys
import os
from sqlalchemy import text
from decimal import Decimal
#
# Script de corrección puntual:
# Actualiza el total de la venta con id=1040 a 32500.0
# Verifica el valor previo y reporta los movimientos de caja asociados.
#
# Uso:
#   Ejecutar desde el directorio "back":
#     venv/bin/python update_venta_total_1040.py
#

# Asegurar imports del módulo database
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import engine  # type: ignore

VENTA_ID = 1040
NUEVO_TOTAL = 32500.0


def main():
    with engine.connect() as conn:
        # Leer el total actual
        row = conn.execute(
            text("SELECT id, total FROM ventas WHERE id = :id"),
            {"id": VENTA_ID},
        ).mappings().first()

        if not row:
            print(f"❌ No se encontró la venta con id={VENTA_ID}")
            return

        total_actual = float(row["total"])
        print(f"Venta {VENTA_ID} total actual: {total_actual}")

        # Actualizar el total
        result = conn.execute(
            text(
                "UPDATE ventas SET total = :nuevo_total WHERE id = :id"
            ),
            {"nuevo_total": NUEVO_TOTAL, "id": VENTA_ID},
        )
        conn.commit()
        print(f"✅ Total actualizado a {NUEVO_TOTAL}. Filas afectadas: {result.rowcount}")

        # Releer para confirmar
        verif = conn.execute(
            text("SELECT total FROM ventas WHERE id = :id"),
            {"id": VENTA_ID},
        ).scalar()
        print(f"Verificación total en DB: {float(verif) if verif is not None else 'N/A'}")

        # Reportar movimientos de caja relacionados (si los hay)
        movs = conn.execute(
            text(
                "SELECT id, monto FROM caja_movimientos WHERE id_venta = :id"
            ),
            {"id": VENTA_ID},
        ).mappings().all()

        if movs:
            suma_montos = float(sum(Decimal(str(m["monto"])) for m in movs))
            print("Movimientos de caja asociados:")
            for m in movs:
                print(f"  - Movimiento {m['id']}: monto={m['monto']}")
            print(f"Σ Suma montos de caja: {suma_montos}")
            if abs(suma_montos - NUEVO_TOTAL) > 0.001:
                print("⚠️ Aviso: la suma de montos de caja no coincide con el nuevo total de la venta.")
                if len(movs) == 1:
                    mov_id = movs[0]["id"]
                    print(f"Actualizando movimiento de caja {mov_id} para que coincida con el total de la venta…")
                    upd = conn.execute(
                        text("UPDATE caja_movimientos SET monto = :nuevo_total WHERE id = :id"),
                        {"nuevo_total": NUEVO_TOTAL, "id": mov_id},
                    )
                    conn.commit()
                    print(f"✅ Movimiento {mov_id} actualizado. Filas afectadas: {upd.rowcount}")
                    # Verificar nuevamente
                    nueva_suma = conn.execute(
                        text("SELECT SUM(monto) FROM caja_movimientos WHERE id_venta = :id"),
                        {"id": VENTA_ID},
                    ).scalar() or 0.0
                    print(f"Verificación suma montos de caja: {float(nueva_suma)}")
                else:
                    print("ℹ️ Hay múltiples movimientos de caja; no se ajustan automáticamente.")
        else:
            print("No hay movimientos de caja asociados a la venta.")


if __name__ == "__main__":
    main()
