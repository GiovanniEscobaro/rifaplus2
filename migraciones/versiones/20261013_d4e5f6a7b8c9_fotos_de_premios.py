"""Foto opcional de cada premio, que sube el organizador y se muestra en la boleta.

Revisión: d4e5f6a7b8c9
Anterior: c3d4e5f6a7b8
Fecha: 2026-10-13
"""
import sqlalchemy as sa
from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("premios", sa.Column("foto_url", sa.String(length=300), nullable=True))


def downgrade() -> None:
    op.drop_column("premios", "foto_url")
