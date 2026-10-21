"""Pagos de comisión a vendedores, para liquidar su saldo hasta cero.

Revisión: c3d4e5f6a7b8
Anterior: b2c3d4e5f6a7
Fecha: 2026-10-12
"""
import sqlalchemy as sa
from alembic import op

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pagos_comision",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("vendedor_id", sa.BigInteger(), nullable=False),
        sa.Column("monto", sa.Numeric(12, 0), nullable=False),
        sa.Column("medio_pago_id", sa.BigInteger(), nullable=False),
        sa.Column("referencia", sa.String(length=100), nullable=True),
        sa.Column("observacion", sa.String(length=300), nullable=True),
        sa.Column("registrado_por_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("monto > 0", name=op.f("ck_pagos_comision_monto")),
        sa.ForeignKeyConstraint(["medio_pago_id"], ["medios_pago.id"],
                                name=op.f("fk_pagos_comision_medio_pago_id_medios_pago"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["registrado_por_id"], ["usuarios.id"],
                                name=op.f("fk_pagos_comision_registrado_por_id_usuarios"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["vendedor_id"], ["vendedores.id"],
                                name=op.f("fk_pagos_comision_vendedor_id_vendedores"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pagos_comision")),
    )
    op.create_index(op.f("ix_pagos_comision_vendedor_id"), "pagos_comision", ["vendedor_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_pagos_comision_vendedor_id"), table_name="pagos_comision")
    op.drop_table("pagos_comision")
