"""Unificar ramas divergentes de CUIT y creación inicial

Revision ID: d49af62587b5
Revises: 90d209d80239, cbb92c1d1c39
Create Date: 2025-07-19 15:18:44.187709

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd49af62587b5'
down_revision: Union[str, Sequence[str], None] = ('90d209d80239', 'cbb92c1d1c39')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
