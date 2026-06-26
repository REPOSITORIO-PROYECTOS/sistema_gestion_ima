"""Agregar columna precio_manual a articulos (PANADERIA, GOLOSINAS, etc.)

Revision ID: g1h2i3j4k5l6
Revises: f3a4b5c6d7e8
Create Date: 2026-06-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "g1h2i3j4k5l6"
down_revision: Union[str, Sequence[str], None] = "f3a4b5c6d7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "articulos",
        sa.Column("precio_manual", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute("""
        UPDATE articulos
        SET precio_manual = 1,
            auto_actualizar_precio = 0
        WHERE UPPER(TRIM(descripcion)) IN ('GOLOSINAS', 'PANADERIA')
           OR codigo_interno IN ('000498', '002992')
    """)


def downgrade() -> None:
    op.drop_column("articulos", "precio_manual")
