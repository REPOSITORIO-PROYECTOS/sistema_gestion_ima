"""Unificar ramas de historial divergentes

Revision ID: 728db48bb35f
Revises: 6a3e5219b777, cbb92c1d1c39
Create Date: 2025-09-08 14:17:53.679776

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '728db48bb35f'
down_revision: Union[str, Sequence[str], None] = ('6a3e5219b777', 'cbb92c1d1c39')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
