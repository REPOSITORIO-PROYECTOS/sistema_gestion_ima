"""Crear tablas transferencias_stock para modo especial

Revision ID: i3j4k5l6m7n8
Revises: h2i3j4k5l6m7
Create Date: 2026-06-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "i3j4k5l6m7n8"
down_revision: Union[str, Sequence[str], None] = "h2i3j4k5l6m7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "transferencias_stock",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(length=32), nullable=False, server_default="PENDIENTE"),
        sa.Column("observacion", sa.String(length=500), nullable=True),
        sa.Column("creada_en", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("recibida_en", sa.DateTime(), nullable=True),
        sa.Column("id_empresa_origen", sa.Integer(), nullable=False),
        sa.Column("id_empresa_destino", sa.Integer(), nullable=False),
        sa.Column("id_usuario_envio", sa.Integer(), nullable=False),
        sa.Column("id_usuario_recepcion", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["id_empresa_destino"], ["empresas.id"]),
        sa.ForeignKeyConstraint(["id_empresa_origen"], ["empresas.id"]),
        sa.ForeignKeyConstraint(["id_usuario_envio"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["id_usuario_recepcion"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transferencias_stock_estado", "transferencias_stock", ["estado"])
    op.create_index("ix_transferencias_stock_id_empresa_origen", "transferencias_stock", ["id_empresa_origen"])
    op.create_index("ix_transferencias_stock_id_empresa_destino", "transferencias_stock", ["id_empresa_destino"])

    op.create_table(
        "transferencias_stock_detalle",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("id_transferencia", sa.Integer(), nullable=False),
        sa.Column("codigo_interno", sa.String(length=64), nullable=False),
        sa.Column("descripcion", sa.String(length=255), nullable=False),
        sa.Column("cantidad", sa.Float(), nullable=False),
        sa.Column("cantidad_recibida", sa.Float(), nullable=True),
        sa.Column("precio_unitario", sa.Float(), nullable=True),
        sa.Column("id_articulo_origen", sa.Integer(), nullable=False),
        sa.Column("id_articulo_destino", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["id_articulo_destino"], ["articulos.id"]),
        sa.ForeignKeyConstraint(["id_articulo_origen"], ["articulos.id"]),
        sa.ForeignKeyConstraint(["id_transferencia"], ["transferencias_stock.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_transferencias_stock_detalle_id_transferencia",
        "transferencias_stock_detalle",
        ["id_transferencia"],
    )


def downgrade() -> None:
    op.drop_index("ix_transferencias_stock_detalle_id_transferencia", table_name="transferencias_stock_detalle")
    op.drop_table("transferencias_stock_detalle")
    op.drop_index("ix_transferencias_stock_id_empresa_destino", table_name="transferencias_stock")
    op.drop_index("ix_transferencias_stock_id_empresa_origen", table_name="transferencias_stock")
    op.drop_index("ix_transferencias_stock_estado", table_name="transferencias_stock")
    op.drop_table("transferencias_stock")
