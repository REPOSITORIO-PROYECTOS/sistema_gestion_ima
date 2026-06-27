"""Permitir mismo código de barras en distintos artículos (multi-empresa)

Revision ID: h2i3j4k5l6m7
Revises: g1h2i3j4k5l6
Create Date: 2026-06-26

"""
from typing import Sequence, Union

from alembic import op

revision: str = "h2i3j4k5l6m7"
down_revision: Union[str, Sequence[str], None] = "g1h2i3j4k5l6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("PRIMARY", "articulo_codigos", type_="primary")
    op.create_primary_key(
        "pk_articulo_codigos",
        "articulo_codigos",
        ["codigo", "id_articulo"],
    )


def downgrade() -> None:
    op.drop_constraint("pk_articulo_codigos", "articulo_codigos", type_="primary")
    op.create_primary_key("PRIMARY", "articulo_codigos", ["codigo"])
