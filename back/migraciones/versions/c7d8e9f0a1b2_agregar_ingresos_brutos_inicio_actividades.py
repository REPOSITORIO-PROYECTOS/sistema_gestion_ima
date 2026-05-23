"""Agregar ingresos_brutos e inicio_actividades a configuracion_empresa

Revision ID: c7d8e9f0a1b2
Revises: b8c4e2f1a903
Create Date: 2026-05-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, Sequence[str], None] = "b8c4e2f1a903"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "configuracion_empresa",
        sa.Column("ingresos_brutos", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "configuracion_empresa",
        sa.Column("inicio_actividades", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("configuracion_empresa", "inicio_actividades")
    op.drop_column("configuracion_empresa", "ingresos_brutos")
