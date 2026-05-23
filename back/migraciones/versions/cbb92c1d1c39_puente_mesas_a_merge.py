"""Puente histórico: une la rama de mesas (f4797) con el merge 728db48bb35f

Revision ID: cbb92c1d1c39
Revises: f4797ffeaa91
Create Date: 2025-09-08

La revisión existía en despliegues anteriores pero faltaba el archivo en el repo.
El esquema ya fue aplicado en producción; esta migración es un no-op.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "cbb92c1d1c39"
down_revision: Union[str, Sequence[str], None] = "f4797ffeaa91"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
