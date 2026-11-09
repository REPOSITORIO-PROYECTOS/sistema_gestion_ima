"""Agregar orden al código de barras para conservar el principal

Revision ID: n8o9p0q1r2s3
Revises: m7n8o9p0q1r2
Create Date: 2026-11-09

Los códigos ya existentes quedan en orden 0. El próximo guardado fija
cuál es el principal. No borra filas ni cambia la clave primaria.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "n8o9p0q1r2s3"
down_revision: Union[str, Sequence[str], None] = "m7n8o9p0q1r2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    return any(col["name"] == column for col in inspect(bind).get_columns(table))


def upgrade() -> None:
    if not _has_column("articulo_codigos", "orden"):
        op.add_column(
            "articulo_codigos",
            sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    if _has_column("articulo_codigos", "orden"):
        op.drop_column("articulo_codigos", "orden")
