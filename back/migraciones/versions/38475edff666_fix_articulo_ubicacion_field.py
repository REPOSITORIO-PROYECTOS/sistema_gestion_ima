"""Fix articulo ubicacion field and codigos_barras relationship

Revision ID: 38475edff666
Revises: 6a3e5219b777
Create Date: 2026-02-10 12:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '38475edff666'
down_revision = '6a3e5219b777'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Modificar la columna ubicacion de articulos para que tenga default value
    # y sea opcional (nullable)
    op.alter_column('articulos', 'ubicacion',
               existing_type=sa.String(length=255),
               existing_nullable=False,
               nullable=True,
               existing_server_default=None,
               server_default='Sin definir'
               )


def downgrade() -> None:
    # Revertir el cambio
    op.alter_column('articulos', 'ubicacion',
               existing_type=sa.String(length=255),
               existing_nullable=True,
               nullable=False,
               existing_server_default='Sin definir',
               server_default=None
               )
