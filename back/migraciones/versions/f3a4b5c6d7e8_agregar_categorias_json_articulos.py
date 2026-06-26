"""Agregar columna categorias JSON a articulos (multi-categoría estilo POS)

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-06-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f3a4b5c6d7e8"
down_revision: Union[str, Sequence[str], None] = "e2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("articulos", sa.Column("categorias", sa.JSON(), nullable=True))
    # Backfill: artículos legacy con una sola FK pasan a array JSON (como el POS paralelo)
    op.execute("""
        UPDATE articulos a
        INNER JOIN categorias c ON a.id_categoria = c.id
        SET a.categorias = JSON_ARRAY(c.nombre)
        WHERE a.categorias IS NULL AND a.id_categoria IS NOT NULL
    """)


def downgrade() -> None:
    op.drop_column("articulos", "categorias")
