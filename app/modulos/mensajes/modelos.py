"""Cola de mensajes de WhatsApp."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, SmallInteger, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, creado, pk


class MensajeWhatsapp(Base):
    """Cola de mensajes de WhatsApp para compradores (preparada para el envío automático)."""

    __tablename__ = "mensajes_whatsapp"
    __table_args__ = (
        CheckConstraint("tipo IN ('boleta_pagada','saldo_pendiente','recordatorio_sorteo','ganador')", name="tipo"),
        CheckConstraint("canal IN ('automatico','manual')", name="canal"),
        CheckConstraint("estado IN ('pendiente','enviado','fallido','cancelado')", name="estado"),
        # Una boleta no recibe dos veces el aviso de pagada ni el de ganador
        Index(
            "uq_msg_unico_por_boleta",
            "boleta_id",
            "tipo",
            unique=True,
            postgresql_where=text("tipo IN ('boleta_pagada','ganador') AND estado <> 'cancelado'"),
        ),
        Index("ix_msg_pendientes", "estado", "programado_para"),
    )

    id: Mapped[pk]
    organizador_id: Mapped[int] = mapped_column(ForeignKey("organizadores.id", ondelete="RESTRICT"), index=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id", ondelete="RESTRICT"))
    boleta_id: Mapped[int | None] = mapped_column(ForeignKey("boletas.id", ondelete="RESTRICT"))
    tipo: Mapped[str] = mapped_column(String(25))
    canal: Mapped[str] = mapped_column(String(10), default="manual")
    telefono_destino: Mapped[str] = mapped_column(String(20))
    mensaje: Mapped[str] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(12), default="pendiente")
    intentos: Mapped[int] = mapped_column(SmallInteger, default=0)
    programado_para: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    enviado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
    fecha_creacion: Mapped[creado]
