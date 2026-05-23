"""Unificar heads: ingresos brutos + impreso consumo mesa

Revision ID: d1e2f3a4b5c6
Revises: c7d8e9f0a1b2, a1b2c3d4e5f6
Create Date: 2026-05-23

"""
from typing import Sequence, Union

from alembic import op

revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = ("c7d8e9f0a1b2", "a1b2c3d4e5f6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
