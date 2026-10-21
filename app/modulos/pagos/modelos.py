"""Dinero: medios de pago, cuentas de cobro, planes, pagos de boletas, cobros de rifas y entregas de vendedores."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, creado, pk

ESTADOS_REVISION = "estado IN ('pendiente','aprobado','rechazado')"


class MedioPago(Base):
    """Forma de pago (Nequi, Daviplata, efectivo…). Se activan o desactivan sin tocar el código."""

    __tablename__ = "medios_pago"

    id: Mapped[pk]
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    nombre: Mapped[str] = mapped_column(String(50))
    requiere_comprobante: Mapped[bool] = mapped_column(Boolean, default=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=False)
    para_compradores: Mapped[bool] = mapped_column(Boolean, default=True)  # pagos de boletas al organizador
    para_rifaplus: Mapped[bool] = mapped_column(Boolean, default=False)  # pago del plan a RifaPlus
    orden: Mapped[int] = mapped_column(SmallInteger, default=1)


class CuentaCobro(Base):
    """Cuenta donde se recibe dinero. organizador_id vacío = cuenta de RifaPlus."""

    __tablename__ = "cuentas_cobro"

    id: Mapped[pk]
    organizador_id: Mapped[int | None] = mapped_column(ForeignKey("organizadores.id", ondelete="RESTRICT"), index=True)
    medio_pago_id: Mapped[int] = mapped_column(ForeignKey("medios_pago.id", ondelete="RESTRICT"))
    numero_cuenta: Mapped[str] = mapped_column(String(30))
    titular: Mapped[str] = mapped_column(String(150))
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    fecha_creacion: Mapped[creado]

    medio_pago: Mapped[MedioPago] = relationship()


class Plan(Base):
    """Tipo de rifa: boletas que vende (boletas_min = boletas_max) y cifras por boleta (numeros_min = numeros_max)."""

    __tablename__ = "planes"
    __table_args__ = (
        CheckConstraint("boletas_min >= 1 AND boletas_max >= boletas_min", name="rango"),
        CheckConstraint("valor >= 0", name="valor"),
        CheckConstraint("numeros_min >= 1 AND numeros_max >= numeros_min", name="numeros"),
        # Un tipo de rifa (boletas × cifras por boleta) no se puede repetir
        Index(
            "uq_tipo_de_rifa",
            "boletas_min",
            "numeros_min",
            unique=True,
            postgresql_where=text("boletas_min = boletas_max AND numeros_min = numeros_max"),
        ),
    )

    id: Mapped[pk]
    nombre: Mapped[str] = mapped_column(String(50))
    boletas_min: Mapped[int] = mapped_column(Integer)
    boletas_max: Mapped[int] = mapped_column(Integer)
    valor: Mapped[int] = mapped_column(Numeric(12, 0))
    numeros_min: Mapped[int] = mapped_column(SmallInteger, default=1)  # números por boleta permitidos
    numeros_max: Mapped[int] = mapped_column(SmallInteger, default=1)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class Pago(Base):
    """Pago de un comprador por su boleta (va al organizador)."""

    __tablename__ = "pagos"
    __table_args__ = (
        CheckConstraint("monto > 0", name="monto"),
        CheckConstraint(ESTADOS_REVISION, name="estado"),
        Index(
            "uq_pago_referencia",
            "medio_pago_id",
            "referencia",
            unique=True,
            postgresql_where=text("referencia IS NOT NULL AND estado <> 'rechazado'"),
        ),
    )

    id: Mapped[pk]
    boleta_id: Mapped[int] = mapped_column(ForeignKey("boletas.id", ondelete="RESTRICT"), index=True)
    medio_pago_id: Mapped[int] = mapped_column(ForeignKey("medios_pago.id", ondelete="RESTRICT"))
    cuenta_destino_id: Mapped[int | None] = mapped_column(ForeignKey("cuentas_cobro.id", ondelete="RESTRICT"))
    monto: Mapped[int] = mapped_column(Numeric(12, 0))
    referencia: Mapped[str | None] = mapped_column(String(100))
    comprobante_url: Mapped[str | None] = mapped_column(String(300))
    estado: Mapped[str] = mapped_column(String(12), default="pendiente")
    registrado_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"))
    verificado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"))
    fecha_pago: Mapped[creado]
    fecha_verificacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    medio_pago: Mapped[MedioPago] = relationship()
    registrado_por: Mapped["Usuario"] = relationship(foreign_keys=[registrado_por_id])  # noqa: F821


class CobroRifa(Base):
    """Pago del organizador a RifaPlus por publicar una rifa."""

    __tablename__ = "cobros_rifa"
    __table_args__ = (CheckConstraint(ESTADOS_REVISION, name="estado"),)

    id: Mapped[pk]
    rifa_id: Mapped[int] = mapped_column(ForeignKey("rifas.id", ondelete="RESTRICT"), unique=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("planes.id", ondelete="RESTRICT"))
    valor: Mapped[int] = mapped_column(Numeric(12, 0))
    medio_pago_id: Mapped[int | None] = mapped_column(ForeignKey("medios_pago.id", ondelete="RESTRICT"))
    cuenta_destino_id: Mapped[int | None] = mapped_column(ForeignKey("cuentas_cobro.id", ondelete="RESTRICT"))
    referencia: Mapped[str | None] = mapped_column(String(100))
    comprobante_url: Mapped[str | None] = mapped_column(String(300))
    estado: Mapped[str] = mapped_column(String(12), default="pendiente")
    revisado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"))
    motivo_rechazo: Mapped[str | None] = mapped_column(String(300))
    fecha_pago: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_revision: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    rifa: Mapped["Rifa"] = relationship()  # noqa: F821
    medio_pago: Mapped[MedioPago | None] = relationship()


class EntregaVendedor(Base):
    """Dinero que un vendedor le entrega al organizador (rendición de cuentas)."""

    __tablename__ = "entregas_vendedor"
    __table_args__ = (CheckConstraint("monto > 0", name="monto"),)

    id: Mapped[pk]
    vendedor_id: Mapped[int] = mapped_column(ForeignKey("vendedores.id", ondelete="RESTRICT"), index=True)
    rifa_id: Mapped[int] = mapped_column(ForeignKey("rifas.id", ondelete="RESTRICT"), index=True)
    medio_pago_id: Mapped[int] = mapped_column(ForeignKey("medios_pago.id", ondelete="RESTRICT"))
    monto: Mapped[int] = mapped_column(Numeric(12, 0))
    comprobante_url: Mapped[str | None] = mapped_column(String(300))
    recibido_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"))
    fecha: Mapped[creado]
    observacion: Mapped[str | None] = mapped_column(String(300))

    medio_pago: Mapped[MedioPago] = relationship()
    rifa: Mapped["Rifa"] = relationship()  # noqa: F821


class PagoComision(Base):
    """Pago de comisión que el organizador le hace a un vendedor. Con estos pagos su saldo llega a cero."""

    __tablename__ = "pagos_comision"
    __table_args__ = (CheckConstraint("monto > 0", name="monto"),)

    id: Mapped[pk]
    vendedor_id: Mapped[int] = mapped_column(ForeignKey("vendedores.id", ondelete="RESTRICT"), index=True)
    monto: Mapped[int] = mapped_column(Numeric(12, 0))
    medio_pago_id: Mapped[int] = mapped_column(ForeignKey("medios_pago.id", ondelete="RESTRICT"))
    referencia: Mapped[str | None] = mapped_column(String(100))
    observacion: Mapped[str | None] = mapped_column(String(300))
    registrado_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"))
    fecha: Mapped[creado]

    medio_pago: Mapped[MedioPago] = relationship()


class Duracion(Base):
    """Cuánto tiempo cubre un pago: por ejemplo 6 meses o 1 año. El superadministrador las crea y las activa."""

    __tablename__ = "duraciones"
    __table_args__ = (CheckConstraint("meses BETWEEN 1 AND 36", name="meses"),)

    id: Mapped[pk]
    nombre: Mapped[str] = mapped_column(String(40))
    meses: Mapped[int] = mapped_column(SmallInteger, unique=True)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)


class PrecioRifa(Base):
    """Precio de un tipo de rifa por una duración: «1.000 boletas de 1 cifra, por 6 meses, $89.900»."""

    __tablename__ = "precios_rifa"
    __table_args__ = (
        UniqueConstraint("plan_id", "duracion_id", name="uq_precio_tipo_duracion"),
        CheckConstraint("valor >= 0", name="valor"),
    )

    id: Mapped[pk]
    plan_id: Mapped[int] = mapped_column(ForeignKey("planes.id", ondelete="CASCADE"), index=True)
    duracion_id: Mapped[int] = mapped_column(ForeignKey("duraciones.id", ondelete="CASCADE"))
    valor: Mapped[int] = mapped_column(Numeric(12, 0))

    duracion: Mapped[Duracion] = relationship()


class RenovacionRifa(Base):
    """Pago para extender la vigencia de una rifa publicada. Mientras no se apruebe, la rifa vencida sigue bloqueada."""

    __tablename__ = "renovaciones_rifa"
    __table_args__ = (CheckConstraint(ESTADOS_REVISION, name="estado"), CheckConstraint("meses > 0", name="meses"))

    id: Mapped[pk]
    rifa_id: Mapped[int] = mapped_column(ForeignKey("rifas.id", ondelete="CASCADE"), index=True)
    meses: Mapped[int] = mapped_column(SmallInteger)
    valor: Mapped[int] = mapped_column(Numeric(12, 0))
    medio_pago_id: Mapped[int | None] = mapped_column(ForeignKey("medios_pago.id", ondelete="RESTRICT"))
    referencia: Mapped[str | None] = mapped_column(String(100))
    comprobante_url: Mapped[str | None] = mapped_column(String(300))
    estado: Mapped[str] = mapped_column(String(12), default="pendiente")
    motivo_rechazo: Mapped[str | None] = mapped_column(String(300))
    revisado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    fecha_pago: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_revision: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_creacion: Mapped[creado]

    rifa: Mapped["Rifa"] = relationship()  # noqa: F821
    medio_pago: Mapped[MedioPago | None] = relationship()
