"""Quita los tipos de rifa repetidos y prohíbe que se repitan.

Pasaba cuando se cargaban las semillas antes de la migración de precios: quedaban dos planes iguales por cada
tipo de rifa. Para cada tipo repetido se conserva UNO: el que ya usen las rifas; si ninguno, el que tenga precios
cambiados por el superadministrador (distintos del precio inicial); si tampoco, el más antiguo. Las rifas y cobros
que apuntaban al repetido pasan al que se conserva, y después se borra el repetido con sus precios.

Revisión: b8c9d0e1f2a3
Anterior: af33a30fbbfc
Fecha: 2026-10-20
"""
import sqlalchemy as sa
from alembic import op

revision = "b8c9d0e1f2a3"
down_revision = "af33a30fbbfc"
branch_labels = None
depends_on = None

PRECIO_INICIAL = {(5, 2): 0, (10, 1): 0, (25, 4): 6000, (50, 2): 19900, (100, 1): 19900, (250, 4): 59900,
                  (500, 2): 59900, (1000, 1): 89900, (1250, 8): 149900, (2000, 5): 149900, (2500, 4): 149900,
                  (5000, 2): 299900, (10000, 1): 299900}


def upgrade() -> None:
    c = op.get_bind()
    tipos = c.execute(sa.text(
        "SELECT boletas_min, numeros_min FROM planes WHERE boletas_min = boletas_max AND numeros_min = numeros_max "
        "GROUP BY boletas_min, numeros_min HAVING count(*) > 1")).all()
    for boletas, cifras in tipos:
        planes = c.execute(sa.text(
            "SELECT p.id, p.valor, (SELECT count(*) FROM rifas r WHERE r.plan_id = p.id) AS usos "
            "FROM planes p WHERE p.boletas_min = :b AND p.boletas_max = :b AND p.numeros_min = :c "
            "AND p.numeros_max = :c ORDER BY p.id"), {"b": boletas, "c": cifras}).all()
        inicial = PRECIO_INICIAL.get((boletas, cifras))
        conservar = (next((p for p in planes if p.usos), None)
                     or next((p for p in planes if inicial is not None and int(p.valor) != inicial), None)
                     or planes[0])
        for p in planes:
            if p.id == conservar.id:
                continue
            for tabla in ("rifas", "cobros_rifa"):
                c.execute(sa.text(f"UPDATE {tabla} SET plan_id = :n WHERE plan_id = :v"),  # noqa: S608
                          {"n": conservar.id, "v": p.id})
            c.execute(sa.text("DELETE FROM precios_rifa WHERE plan_id = :v"), {"v": p.id})
            c.execute(sa.text("DELETE FROM planes WHERE id = :v"), {"v": p.id})
    # Desde ahora la base de datos no deja crear dos tipos de rifa iguales
    op.create_index("uq_tipo_de_rifa", "planes", ["boletas_min", "numeros_min"], unique=True,
                    postgresql_where=sa.text("boletas_min = boletas_max AND numeros_min = numeros_max"))


def downgrade() -> None:
    op.drop_index("uq_tipo_de_rifa", table_name="planes")
