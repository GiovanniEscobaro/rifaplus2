"""Personas de cada organizador: vendedores y clientes (compradores)."""

from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, creado, pk


class Vendedor(Base):
    """Persona que vende boletas para un organizador, con su comisión."""

    __tablename__ = "vendedores"
    __table_args__ = (UniqueConstraint("organizador_id", "numero_documento", name="uq_vendedor_documento"),)

    id: Mapped[pk]
    organizador_id: Mapped[int] = mapped_column(ForeignKey("organizadores.id", ondelete="RESTRICT"), index=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), unique=True)
    tipo_documento: Mapped[str] = mapped_column(String(5))
    numero_documento: Mapped[str] = mapped_column(String(20))
    nombre: Mapped[str] = mapped_column(String(150))
    celular: Mapped[str] = mapped_column(String(20))
    ciudad: Mapped[str | None] = mapped_column(String(100))
    comision_porcentaje: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    llave_bre_b: Mapped[str | None] = mapped_column(String(60))  # a dónde se le paga la comisión
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    fecha_creacion: Mapped[creado]


class Cliente(Base):
    """Comprador de boletas. Su documento es único por organizador; todos sus datos son obligatorios."""

    __tablename__ = "clientes"
    __table_args__ = (UniqueConstraint("organizador_id", "numero_documento", name="uq_cliente_documento"),)

    id: Mapped[pk]
    organizador_id: Mapped[int] = mapped_column(ForeignKey("organizadores.id", ondelete="RESTRICT"), index=True)
    tipo_documento: Mapped[str] = mapped_column(String(5))
    numero_documento: Mapped[str] = mapped_column(String(20))
    nombre: Mapped[str] = mapped_column(String(150))
    celular: Mapped[str] = mapped_column(String(20), index=True)
    whatsapp: Mapped[str] = mapped_column(String(20))
    email: Mapped[str] = mapped_column(String(150))
    direccion: Mapped[str] = mapped_column(String(200))
    ciudad: Mapped[str] = mapped_column(String(100))
    pais: Mapped[str] = mapped_column(String(100), default="Colombia")
    acepta_whatsapp: Mapped[bool] = mapped_column(Boolean, default=True)
    referido_por_id: Mapped[int | None] = mapped_column(ForeignKey("clientes.id", ondelete="SET NULL"))
    fecha_creacion: Mapped[creado]

    referido_por: Mapped[Optional["Cliente"]] = relationship(remote_side="Cliente.id")
