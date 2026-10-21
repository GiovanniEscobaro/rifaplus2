"""Planes por números por boleta, rifas de rango completo (1 a 4 cifras) y aceptaciones legales.

Revisión: 8c7dc909ca65
Anterior: ccec9efac41d
Fecha: 2026-10-09
"""
import sqlalchemy as sa
from alembic import op

revision = "8c7dc909ca65"
down_revision = "ccec9efac41d"
branch_labels = None
depends_on = None

# nombre, boletas mínimas, boletas máximas, valor, números por boleta (mínimo, máximo)
PLANES_NUEVOS = [
    ("Gratis", 1, 10, 0, 1, 2),
    ("Plan 25", 11, 25, 6000, 4, 4),
    ("Plan 100", 26, 100, 19900, 1, 2),
    ("Plan 500", 101, 500, 59900, 1, 4),
    ("Plan 1.000", 501, 1000, 89900, 1, 8),
    ("Plan 2.500", 1001, 2500, 149900, 4, 8),
    ("Plan 10.000", 2501, 10000, 299900, 1, 2),
]


def upgrade() -> None:
    # --- Aceptaciones de términos, tratamiento de datos y declaraciones por rifa ---
    op.create_table(
        "aceptaciones",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("organizador_id", sa.BigInteger(), nullable=True),
        sa.Column("rifa_id", sa.BigInteger(), nullable=True),
        sa.Column("documento", sa.String(length=30), nullable=False),
        sa.Column("version", sa.String(length=20), nullable=False),
        sa.Column("texto_aceptado", sa.String(length=600), nullable=True),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("fecha", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "documento IN ('terminos', 'tratamiento_datos', 'declaracion_rifa')", name=op.f("ck_aceptaciones_documento")
        ),
        sa.ForeignKeyConstraint(["organizador_id"], ["organizadores.id"],
                                name=op.f("fk_aceptaciones_organizador_id_organizadores"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["rifa_id"], ["rifas.id"], name=op.f("fk_aceptaciones_rifa_id_rifas"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], name=op.f("fk_aceptaciones_usuario_id_usuarios"),
                                ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_aceptaciones")),
    )
    op.create_index(op.f("ix_aceptaciones_organizador_id"), "aceptaciones", ["organizador_id"], unique=False)
    op.create_index(op.f("ix_aceptaciones_rifa_id"), "aceptaciones", ["rifa_id"], unique=False)
    op.create_index(op.f("ix_aceptaciones_usuario_id"), "aceptaciones", ["usuario_id"], unique=False)

    # --- Planes: números por boleta permitidos ---
    op.add_column("planes", sa.Column("numeros_min", sa.SmallInteger(), nullable=False, server_default="1"))
    op.add_column("planes", sa.Column("numeros_max", sa.SmallInteger(), nullable=False, server_default="1"))
    op.alter_column("planes", "numeros_min", server_default=None)
    op.alter_column("planes", "numeros_max", server_default=None)
    op.create_check_constraint("numeros", "planes", "numeros_min >= 1 AND numeros_max >= numeros_min")

    # Los planes anteriores quedan inactivos (las rifas que ya los usan los conservan) y entran los nuevos
    op.execute("UPDATE planes SET activo = false")
    planes = sa.table("planes", sa.column("nombre", sa.String), sa.column("boletas_min", sa.Integer),
                      sa.column("boletas_max", sa.Integer), sa.column("valor", sa.Numeric),
                      sa.column("numeros_min", sa.SmallInteger), sa.column("numeros_max", sa.SmallInteger),
                      sa.column("activo", sa.Boolean))
    op.bulk_insert(planes, [
        {"nombre": n, "boletas_min": bmin, "boletas_max": bmax, "valor": v, "numeros_min": nmin,
         "numeros_max": nmax, "activo": True}
        for n, bmin, bmax, v, nmin, nmax in PLANES_NUEVOS
    ])

    # --- Rifas: de 1 a 4 cifras y siempre con todos los números ---
    op.drop_constraint(op.f("ck_rifas_cifras"), "rifas", type_="check")
    op.drop_constraint(op.f("ck_rifas_rango"), "rifas", type_="check")
    op.execute("ALTER TABLE rifas ADD CONSTRAINT ck_rifas_cifras CHECK (cifras BETWEEN 1 AND 4)")
    # NOT VALID: se exige a las rifas nuevas sin rechazar rifas de prueba creadas con la regla anterior
    op.execute("ALTER TABLE rifas ADD CONSTRAINT ck_rifas_rango_completo CHECK (total_numeros = power(10, cifras)) NOT VALID")


def downgrade() -> None:
    op.drop_constraint(op.f("ck_rifas_rango_completo"), "rifas", type_="check")
    op.drop_constraint(op.f("ck_rifas_cifras"), "rifas", type_="check")
    op.execute("ALTER TABLE rifas ADD CONSTRAINT ck_rifas_cifras CHECK (cifras IN (2,3,4)) NOT VALID")
    op.execute("ALTER TABLE rifas ADD CONSTRAINT ck_rifas_rango CHECK (total_numeros >= 1 AND total_numeros <= power(10, cifras)) NOT VALID")
    # Quita los planes que agregó esta migración (si ninguna rifa los usa) y reactiva los anteriores
    for n, bmin, bmax, *_ in PLANES_NUEVOS:
        op.execute(sa.text(
            "DELETE FROM planes p WHERE p.nombre = :n AND p.boletas_min = :bmin AND p.boletas_max = :bmax "
            "AND NOT EXISTS (SELECT 1 FROM rifas r WHERE r.plan_id = p.id) "
            "AND NOT EXISTS (SELECT 1 FROM cobros_rifa c WHERE c.plan_id = p.id)"
        ).bindparams(n=n, bmin=bmin, bmax=bmax))
    op.execute("UPDATE planes SET activo = true")
    op.drop_constraint(op.f("ck_planes_numeros"), "planes", type_="check")
    op.drop_column("planes", "numeros_max")
    op.drop_column("planes", "numeros_min")
    op.drop_index(op.f("ix_aceptaciones_usuario_id"), table_name="aceptaciones")
    op.drop_index(op.f("ix_aceptaciones_rifa_id"), table_name="aceptaciones")
    op.drop_index(op.f("ix_aceptaciones_organizador_id"), table_name="aceptaciones")
    op.drop_table("aceptaciones")
