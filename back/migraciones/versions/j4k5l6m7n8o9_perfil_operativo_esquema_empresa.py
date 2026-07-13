"""Agregar tipo_esquema_empresa y perfil_operativo a configuracion_empresa

Revision ID: j4k5l6m7n8o9
Revises: i3j4k5l6m7n8
Create Date: 2026-07-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "j4k5l6m7n8o9"
down_revision: Union[str, Sequence[str], None] = "i3j4k5l6m7n8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "configuracion_empresa",
        sa.Column(
            "tipo_esquema_empresa",
            sa.String(length=32),
            nullable=False,
            server_default="estandar",
        ),
    )
    op.add_column(
        "configuracion_empresa",
        sa.Column("perfil_operativo", sa.JSON(), nullable=True),
    )
    op.add_column(
        "configuracion_empresa",
        sa.Column("perfil_operativo_archivado", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("configuracion_empresa", "perfil_operativo_archivado")
    op.drop_column("configuracion_empresa", "perfil_operativo")
    op.drop_column("configuracion_empresa", "tipo_esquema_empresa")
