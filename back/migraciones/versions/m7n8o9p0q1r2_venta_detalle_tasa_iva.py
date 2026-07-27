"""Agregar tasa_iva snapshot a venta_detalle

Revision ID: m7n8o9p0q1r2
Revises: l6m7n8o9p0q1
Create Date: 2026-07-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "m7n8o9p0q1r2"
down_revision: Union[str, Sequence[str], None] = "l6m7n8o9p0q1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    return any(col["name"] == column for col in inspect(bind).get_columns(table))


def upgrade() -> None:
    if not _has_column("venta_detalle", "tasa_iva"):
        op.add_column(
            "venta_detalle",
            sa.Column(
                "tasa_iva",
                sa.Float(),
                nullable=False,
                server_default="0.21",
            ),
        )


def downgrade() -> None:
    if _has_column("venta_detalle", "tasa_iva"):
        op.drop_column("venta_detalle", "tasa_iva")
