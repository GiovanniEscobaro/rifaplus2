"""Llave Bre-B como medio de pago (para pagar el plan a RifaPlus y para los compradores).

Revisión: e5f6a7b8c9d0
Anterior: d4e5f6a7b8c9
Fecha: 2026-10-13
"""
from alembic import op

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "INSERT INTO medios_pago (codigo, nombre, requiere_comprobante, activo, orden, para_compradores, para_rifaplus) "
        "SELECT 'bre_b', 'Llave Bre-B', true, true, 0, true, true "
        "WHERE NOT EXISTS (SELECT 1 FROM medios_pago WHERE codigo = 'bre_b')"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM medios_pago m WHERE m.codigo = 'bre_b' "
        "AND NOT EXISTS (SELECT 1 FROM pagos p WHERE p.medio_pago_id = m.id) "
        "AND NOT EXISTS (SELECT 1 FROM cobros_rifa c WHERE c.medio_pago_id = m.id) "
        "AND NOT EXISTS (SELECT 1 FROM cuentas_cobro k WHERE k.medio_pago_id = m.id) "
        "AND NOT EXISTS (SELECT 1 FROM pagos_comision k WHERE k.medio_pago_id = m.id)"
    )
