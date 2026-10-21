"""Llave Bre-B del vendedor, para pagarle su comisión.

Revisión: f6a7b8c9d0e1
Anterior: 3443e040477d
Fecha: 2026-10-17
"""
import sqlalchemy as sa
from alembic import op

revision = "f6a7b8c9d0e1"
down_revision = "3443e040477d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Queda opcional en la base de datos para no romper a los vendedores que ya existen;
    # el formulario la exige al crear o editar un vendedor.
    op.add_column("vendedores", sa.Column("llave_bre_b", sa.String(length=60), nullable=True))


def downgrade() -> None:
    op.drop_column("vendedores", "llave_bre_b")
