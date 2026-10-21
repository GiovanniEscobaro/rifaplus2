"""Aceptación de términos y declaraciones de responsabilidad.

RifaPlus administra rifas; no las organiza ni las opera. Cada aceptación queda
guardada con su versión, fecha e IP para poder demostrar qué aceptó cada organizador.
"""

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, creado, pk


class Aceptacion(Base):
    """Constancia de que un usuario aceptó un documento legal: cuál, qué versión, cuándo y desde qué IP."""

    __tablename__ = "aceptaciones"
    __table_args__ = (
        CheckConstraint("documento IN ('terminos', 'tratamiento_datos', 'declaracion_rifa')", name="documento"),
    )

    id: Mapped[pk]
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), index=True)
    organizador_id: Mapped[int | None] = mapped_column(ForeignKey("organizadores.id", ondelete="RESTRICT"), index=True)
    rifa_id: Mapped[int | None] = mapped_column(ForeignKey("rifas.id", ondelete="RESTRICT"), index=True)
    documento: Mapped[str] = mapped_column(String(30))
    version: Mapped[str] = mapped_column(String(20))
    texto_aceptado: Mapped[str | None] = mapped_column(String(600))
    ip: Mapped[str | None] = mapped_column(String(45))
    fecha: Mapped[creado]
