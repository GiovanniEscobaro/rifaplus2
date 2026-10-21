"""Plan de cuotas por rifa, reglas del organizador y estados de resultado para premios secos.

Revisión: b2c3d4e5f6a7
Anterior: a1b2c3d4e5f6
Fecha: 2026-10-10
"""
import sqlalchemy as sa
from alembic import op

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cuotas_rifa",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("rifa_id", sa.BigInteger(), nullable=False),
        sa.Column("numero", sa.SmallInteger(), nullable=False),
        sa.Column("valor", sa.Numeric(12, 0), nullable=False),
        sa.Column("fecha_limite", sa.Date(), nullable=False),
        sa.CheckConstraint("valor > 0", name=op.f("ck_cuotas_rifa_valor")),
        sa.ForeignKeyConstraint(["rifa_id"], ["rifas.id"], name=op.f("fk_cuotas_rifa_rifa_id_rifas"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cuotas_rifa")),
        sa.UniqueConstraint("rifa_id", "numero", name="uq_cuota_numero"),
    )
    op.create_index(op.f("ix_cuotas_rifa_rifa_id"), "cuotas_rifa", ["rifa_id"], unique=False)
    # Las rifas que ya existían quedan con una sola cuota: el valor completo hasta el día del sorteo
    op.execute("INSERT INTO cuotas_rifa (rifa_id, numero, valor, fecha_limite) "
               "SELECT id, 1, valor_boleta, fecha_sorteo FROM rifas")

    op.add_column("rifas", sa.Column("regla_seco_atrasado", sa.String(10), nullable=False, server_default="desierto"))
    op.add_column("rifas", sa.Column("regla_mayor_sin_pagar", sa.String(12), nullable=False,
                                     server_default="paga_saldo"))
    op.alter_column("rifas", "regla_seco_atrasado", server_default=None)
    op.alter_column("rifas", "regla_mayor_sin_pagar", server_default=None)
    op.create_check_constraint("regla_seco", "rifas", "regla_seco_atrasado IN ('desierto','acumula')")
    op.create_check_constraint("regla_mayor", "rifas", "regla_mayor_sin_pagar IN ('paga_saldo','desierto')")

    op.add_column("resultados", sa.Column("observacion", sa.String(300), nullable=True))
    op.drop_constraint(op.f("ck_resultados_estado"), "resultados", type_="check")
    op.create_check_constraint(
        "estado", "resultados",
        "estado IN ('pendiente','con_ganador','debe_saldo','desierto','acumulado','sin_ganador')")


def downgrade() -> None:
    op.drop_constraint(op.f("ck_resultados_estado"), "resultados", type_="check")
    op.execute("UPDATE resultados SET estado = 'sin_ganador' WHERE estado IN ('debe_saldo','desierto','acumulado')")
    op.create_check_constraint("estado", "resultados", "estado IN ('pendiente','con_ganador','sin_ganador')")
    op.drop_column("resultados", "observacion")
    op.drop_constraint(op.f("ck_rifas_regla_mayor"), "rifas", type_="check")
    op.drop_constraint(op.f("ck_rifas_regla_seco"), "rifas", type_="check")
    op.drop_column("rifas", "regla_mayor_sin_pagar")
    op.drop_column("rifas", "regla_seco_atrasado")
    op.drop_index(op.f("ix_cuotas_rifa_rifa_id"), table_name="cuotas_rifa")
    op.drop_table("cuotas_rifa")
