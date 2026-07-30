#!/usr/bin/env python3
"""List users / open caja / RECARGA for empresas 37 y 38 (prod)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlmodel import Session, select

from back.database import engine
from back.modelos import Articulo, CajaSesion, Rol, Usuario


def main() -> int:
    with Session(engine) as db:
        for eid in (37, 38):
            users = db.exec(
                select(Usuario).where(Usuario.id_empresa == eid, Usuario.activo == True)  # noqa: E712
            ).all()
            print(f"=== emp {eid} users={len(users)} ===")
            for u in users[:10]:
                rol = db.get(Rol, u.id_rol) if u.id_rol else None
                print(f"  id={u.id} user={u.nombre_usuario!r} rol={getattr(rol, 'nombre', None)}")
            abiertas = db.exec(
                select(CajaSesion).where(
                    CajaSesion.id_empresa == eid,
                    CajaSesion.estado == "ABIERTA",
                )
            ).all()
            print(f"  cajas_abiertas={len(abiertas)}")
            for s in abiertas[:5]:
                print(f"    sesion={s.id} user_apertura={s.id_usuario_apertura} desde={s.fecha_apertura}")
            art = db.exec(
                select(Articulo).where(
                    Articulo.id_empresa == eid,
                    Articulo.codigo_interno == "RECARGA",
                )
            ).first()
            print(
                f"  RECARGA id={getattr(art, 'id', None)} "
                f"pm={getattr(art, 'precio_manual', None)} activo={getattr(art, 'activo', None)}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
