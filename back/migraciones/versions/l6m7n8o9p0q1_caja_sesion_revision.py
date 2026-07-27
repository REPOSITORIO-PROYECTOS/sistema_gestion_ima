"""Agregar checklist de revision a sesiones de caja

Revision ID: l6m7n8o9p0q1
Revises: k5l6m7n8o9p0
Create Date: 2026-07-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "l6m7n8o9p0q1"
down_revision: Union[str, Sequence[str], None] = "k5l6m7n8o9p0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    return any(col["name"] == column for col in inspect(bind).get_columns(table))


def _has_fk(table: str, name: str) -> bool:
    bind = op.get_bind()
    return any(fk.get("name") == name for fk in inspect(bind).get_foreign_keys(table))


def upgrade() -> None:
    if not _has_column("caja_sesiones", "revisado"):
        op.add_column(
            "caja_sesiones",
            sa.Column("revisado", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    if not _has_column("caja_sesiones", "id_usuario_revision"):
        op.add_column(
            "caja_sesiones",
            sa.Column("id_usuario_revision", sa.Integer(), nullable=True),
        )
    if not _has_column("caja_sesiones", "fecha_revision"):
        op.add_column(
            "caja_sesiones",
            sa.Column("fecha_revision", sa.DateTime(), nullable=True),
        )
    if not _has_column("caja_sesiones", "nota_revision"):
        op.add_column(
            "caja_sesiones",
            sa.Column("nota_revision", sa.String(length=500), nullable=True),
        )
    if not _has_fk("caja_sesiones", "fk_caja_sesiones_usuario_revision"):
        op.create_foreign_key(
            "fk_caja_sesiones_usuario_revision",
            "caja_sesiones",
            "usuarios",
            ["id_usuario_revision"],
            ["id"],
        )


def downgrade() -> None:
    if _has_fk("caja_sesiones", "fk_caja_sesiones_usuario_revision"):
        op.drop_constraint(
            "fk_caja_sesiones_usuario_revision", "caja_sesiones", type_="foreignkey"
        )
    if _has_column("caja_sesiones", "nota_revision"):
        op.drop_column("caja_sesiones", "nota_revision")
    if _has_column("caja_sesiones", "fecha_revision"):
        op.drop_column("caja_sesiones", "fecha_revision")
    if _has_column("caja_sesiones", "id_usuario_revision"):
        op.drop_column("caja_sesiones", "id_usuario_revision")
    if _has_column("caja_sesiones", "revisado"):
        op.drop_column("caja_sesiones", "revisado")
