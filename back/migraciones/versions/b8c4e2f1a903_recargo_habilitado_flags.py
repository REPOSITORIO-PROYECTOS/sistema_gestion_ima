"""Agregar flags habilitado para recargos en configuracion_empresa

Revision ID: b8c4e2f1a903
Revises: 38475edff666
Create Date: 2026-05-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b8c4e2f1a903"
down_revision: Union[str, Sequence[str], None] = "38475edff666"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "configuracion_empresa",
        sa.Column("recargo_transferencia_habilitado", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "configuracion_empresa",
        sa.Column("recargo_banco_habilitado", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("configuracion_empresa", "recargo_banco_habilitado")
    op.drop_column("configuracion_empresa", "recargo_transferencia_habilitado")
