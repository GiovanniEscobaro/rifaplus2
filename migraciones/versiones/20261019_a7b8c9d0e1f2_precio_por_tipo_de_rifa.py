"""Un precio por cada tipo de rifa (boletas que vende y cifras por boleta), en lugar de planes por rangos.

Para cada uno de los 13 tipos se crea un plan exacto con el precio que tenía según los planes activos.
Los planes viejos quedan inactivos (no se borran porque las rifas que ya existen los usan).

Revisión: a7b8c9d0e1f2
Anterior: f6a7b8c9d0e1
Fecha: 2026-10-19
"""
import sqlalchemy as sa
from alembic import op

revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None

TIPOS = [(5, 2), (10, 1), (25, 4), (50, 2), (100, 1), (250, 4), (500, 2), (1000, 1), (1250, 8), (2000, 5),
         (2500, 4), (5000, 2), (10000, 1)]


def upgrade() -> None:
    conexion = op.get_bind()
    viejos = conexion.execute(sa.text(
        "SELECT boletas_min, boletas_max, numeros_min, numeros_max, valor, activo FROM planes")).all()
    for boletas, cifras in TIPOS:
        # Precio actual: el del plan activo que cubría ese tipo de rifa; si no había, el de cualquier plan que lo cubriera
        candidatos = [v for bmin, bmax, nmin, nmax, v, activo in sorted(viejos, key=lambda x: not x[5])
                      if bmin <= boletas <= bmax and nmin <= cifras <= nmax]
        activo = any(bmin <= boletas <= bmax and nmin <= cifras <= nmax and a
                     for bmin, bmax, nmin, nmax, _, a in viejos)
        valor = candidatos[0] if candidatos else 0
        nombre = f"{boletas:,} boletas de {cifras} cifra{'s' if cifras > 1 else ''}".replace(",", ".")
        ya_existe = conexion.execute(sa.text(
            "SELECT 1 FROM planes WHERE boletas_min = :b AND boletas_max = :b AND numeros_min = :c "
            "AND numeros_max = :c"), {"b": boletas, "c": cifras}).first()
        if ya_existe:  # por ejemplo, si las semillas se cargaron antes de esta migración
            continue
        conexion.execute(sa.text(
            "INSERT INTO planes (nombre, boletas_min, boletas_max, numeros_min, numeros_max, valor, activo) "
            "VALUES (:n, :b, :b, :c, :c, :v, false)"), {"n": nombre, "b": boletas, "c": cifras, "v": valor})
        if activo:
            conexion.execute(sa.text("UPDATE planes SET activo = true WHERE nombre = :n AND boletas_min = :b"),
                             {"n": nombre, "b": boletas})
    # Los planes por rangos quedan inactivos
    conexion.execute(sa.text("UPDATE planes SET activo = false WHERE boletas_min <> boletas_max "
                             "OR numeros_min <> numeros_max OR nombre NOT LIKE '%boletas de%'"))


def downgrade() -> None:
    op.execute("DELETE FROM planes p WHERE p.nombre LIKE '%boletas de%' AND p.boletas_min = p.boletas_max "
               "AND NOT EXISTS (SELECT 1 FROM rifas r WHERE r.plan_id = p.id)")
    op.execute("UPDATE planes SET activo = true WHERE boletas_min <> boletas_max")
