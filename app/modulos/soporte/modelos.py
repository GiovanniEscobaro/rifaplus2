"""Chat de soporte: una conversación por organizador, con mensajes del organizador, del asistente y de RifaPlus."""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, creado, pk


class ConversacionSoporte(Base):
    """Conversación de soporte de un organizador. 'pendiente' = espera respuesta de RifaPlus."""

    __tablename__ = "conversaciones_soporte"
    __table_args__ = (CheckConstraint("estado IN ('pendiente','atendida')", name="estado"),)

    id: Mapped[pk]
    organizador_id: Mapped[int] = mapped_column(ForeignKey("organizadores.id", ondelete="CASCADE"), unique=True)
    estado: Mapped[str] = mapped_column(String(10), default="atendida")
    sin_leer_organizador: Mapped[bool] = mapped_column(Boolean, default=False)  # respuesta nueva de RifaPlus
    actualizada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fecha_creacion: Mapped[creado]

    organizador: Mapped["Organizador"] = relationship()  # noqa: F821
    mensajes: Mapped[list["MensajeSoporte"]] = relationship(order_by="MensajeSoporte.id", cascade="all, delete-orphan")


class MensajeSoporte(Base):
    """Un mensaje del chat. autor: organizador, asistente (respuesta automática) o rifaplus (el superadministrador)."""

    __tablename__ = "mensajes_soporte"
    __table_args__ = (CheckConstraint("autor IN ('organizador','asistente','rifaplus')", name="autor"),)

    id: Mapped[pk]
    conversacion_id: Mapped[int] = mapped_column(
        ForeignKey("conversaciones_soporte.id", ondelete="CASCADE"), index=True
    )
    autor: Mapped[str] = mapped_column(String(12))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    texto: Mapped[str] = mapped_column(Text)
    fecha: Mapped[creado]
