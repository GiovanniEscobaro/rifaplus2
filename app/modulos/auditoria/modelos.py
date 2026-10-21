"""Registro de cambios importantes."""

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, creado, pk


class Auditoria(Base):
    """Registro de cambios importantes: quién, qué tabla y registro, qué acción, antes y después."""

    __tablename__ = "auditoria"

    id: Mapped[pk]
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), index=True)
    organizador_id: Mapped[int | None] = mapped_column(ForeignKey("organizadores.id", ondelete="SET NULL"), index=True)
    tabla: Mapped[str] = mapped_column(String(50))
    registro_id: Mapped[int] = mapped_column(BigInteger)
    accion: Mapped[str] = mapped_column(String(20))
    valor_anterior: Mapped[dict | None] = mapped_column(JSONB)
    valor_nuevo: Mapped[dict | None] = mapped_column(JSONB)
    ip: Mapped[str | None] = mapped_column(String(45))
    fecha: Mapped[creado]
