"""Agregar trazabilidad de anulacion de movimientos y edicion de sesiones de caja

Revision ID: k5l6m7n8o9p0
Revises: j4k5l6m7n8o9
Create Date: 2026-07-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "k5l6m7n8o9p0"
down_revision: Union[str, Sequence[str], None] = "j4k5l6m7n8o9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    return any(col["name"] == column for col in inspect(bind).get_columns(table))


def _has_fk(table: str, name: str) -> bool:
    bind = op.get_bind()
    return any(fk.get("name") == name for fk in inspect(bind).get_foreign_keys(table))


def upgrade() -> None:
    # --- caja_movimientos: estado + trazabilidad de anulacion ---
    if not _has_column("caja_movimientos", "estado"):
        op.add_column(
            "caja_movimientos",
            sa.Column("estado", sa.String(length=20), nullable=False, server_default="ACTIVO"),
        )
    if not _has_column("caja_movimientos", "id_usuario_anulacion"):
        op.add_column(
            "caja_movimientos",
            sa.Column("id_usuario_anulacion", sa.Integer(), nullable=True),
        )
    if not _has_column("caja_movimientos", "fecha_anulacion"):
        op.add_column(
            "caja_movimientos",
            sa.Column("fecha_anulacion", sa.DateTime(), nullable=True),
        )
    if not _has_column("caja_movimientos", "motivo_anulacion"):
        op.add_column(
            "caja_movimientos",
            sa.Column("motivo_anulacion", sa.String(length=500), nullable=True),
        )
    if not _has_fk("caja_movimientos", "fk_caja_movimientos_usuario_anulacion"):
        op.create_foreign_key(
            "fk_caja_movimientos_usuario_anulacion",
            "caja_movimientos",
            "usuarios",
            ["id_usuario_anulacion"],
            ["id"],
        )

    # --- caja_sesiones: trazabilidad de edicion ---
    if not _has_column("caja_sesiones", "id_usuario_ultima_edicion"):
        op.add_column(
            "caja_sesiones",
            sa.Column("id_usuario_ultima_edicion", sa.Integer(), nullable=True),
        )
    if not _has_column("caja_sesiones", "fecha_ultima_edicion"):
        op.add_column(
            "caja_sesiones",
            sa.Column("fecha_ultima_edicion", sa.DateTime(), nullable=True),
        )
    if not _has_fk("caja_sesiones", "fk_caja_sesiones_usuario_ultima_edicion"):
        op.create_foreign_key(
            "fk_caja_sesiones_usuario_ultima_edicion",
            "caja_sesiones",
            "usuarios",
            ["id_usuario_ultima_edicion"],
            ["id"],
        )


def downgrade() -> None:
    if _has_fk("caja_sesiones", "fk_caja_sesiones_usuario_ultima_edicion"):
        op.drop_constraint(
            "fk_caja_sesiones_usuario_ultima_edicion", "caja_sesiones", type_="foreignkey"
        )
    if _has_column("caja_sesiones", "fecha_ultima_edicion"):
        op.drop_column("caja_sesiones", "fecha_ultima_edicion")
    if _has_column("caja_sesiones", "id_usuario_ultima_edicion"):
        op.drop_column("caja_sesiones", "id_usuario_ultima_edicion")

    if _has_fk("caja_movimientos", "fk_caja_movimientos_usuario_anulacion"):
        op.drop_constraint(
            "fk_caja_movimientos_usuario_anulacion", "caja_movimientos", type_="foreignkey"
        )
    if _has_column("caja_movimientos", "motivo_anulacion"):
        op.drop_column("caja_movimientos", "motivo_anulacion")
    if _has_column("caja_movimientos", "fecha_anulacion"):
        op.drop_column("caja_movimientos", "fecha_anulacion")
    if _has_column("caja_movimientos", "id_usuario_anulacion"):
        op.drop_column("caja_movimientos", "id_usuario_anulacion")
    if _has_column("caja_movimientos", "estado"):
        op.drop_column("caja_movimientos", "estado")
