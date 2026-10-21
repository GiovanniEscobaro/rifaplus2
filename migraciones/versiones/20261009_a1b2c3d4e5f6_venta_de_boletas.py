"""Venta de boletas: WhatsApp y datos obligatorios del comprador, y medios de pago por uso.

Revisión: a1b2c3d4e5f6
Anterior: 8c7dc909ca65
Fecha: 2026-10-09
"""
import sqlalchemy as sa
from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "8c7dc909ca65"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Comprador: WhatsApp aparte del celular; correo, dirección y ciudad obligatorios ---
    op.add_column("clientes", sa.Column("whatsapp", sa.String(length=20), nullable=True))
    op.execute("UPDATE clientes SET whatsapp = celular WHERE whatsapp IS NULL")
    op.execute("UPDATE clientes SET email = '' WHERE email IS NULL")
    op.execute("UPDATE clientes SET direccion = '' WHERE direccion IS NULL")
    op.execute("UPDATE clientes SET ciudad = '' WHERE ciudad IS NULL")
    for columna in ("whatsapp", "email", "direccion", "ciudad"):
        op.alter_column("clientes", columna, nullable=False)

    # --- Medios de pago: cuáles usan los compradores y cuáles sirven para pagar a RifaPlus ---
    op.add_column("medios_pago", sa.Column("para_compradores", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("medios_pago", sa.Column("para_rifaplus", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column("medios_pago", "para_compradores", server_default=None)
    op.alter_column("medios_pago", "para_rifaplus", server_default=None)
    op.execute("UPDATE medios_pago SET para_rifaplus = true WHERE codigo IN ('nequi', 'daviplata')")
    op.execute("UPDATE medios_pago SET activo = true WHERE codigo = 'efectivo'")
    op.execute(
        "INSERT INTO medios_pago (codigo, nombre, requiere_comprobante, activo, orden, para_compradores, para_rifaplus) "
        "SELECT 'transferencia', 'Transferencia bancaria', true, true, 4, true, false "
        "WHERE NOT EXISTS (SELECT 1 FROM medios_pago WHERE codigo = 'transferencia')"
    )
    for codigo, orden in (("nequi", 1), ("daviplata", 2), ("efectivo", 3), ("transferencia", 4),
                          ("tarjeta_credito", 5), ("tarjeta_debito", 6)):
        op.execute(sa.text("UPDATE medios_pago SET orden = :o WHERE codigo = :c").bindparams(o=orden, c=codigo))


def downgrade() -> None:
    op.execute(
        "DELETE FROM medios_pago m WHERE m.codigo = 'transferencia' "
        "AND NOT EXISTS (SELECT 1 FROM pagos p WHERE p.medio_pago_id = m.id)"
    )
    op.execute("UPDATE medios_pago SET activo = false WHERE codigo = 'efectivo'")
    op.drop_column("medios_pago", "para_rifaplus")
    op.drop_column("medios_pago", "para_compradores")
    for columna in ("email", "direccion", "ciudad"):
        op.alter_column("clientes", columna, nullable=True)
    op.drop_column("clientes", "whatsapp")
