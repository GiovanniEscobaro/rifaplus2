"""Rifas: loterías, rifas, premios, boletas, números y resultados."""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, creado, pk

ESTADOS_RIFA = ("borrador", "en_venta", "cerrada", "sorteada", "anulada")
ESTADOS_BOLETA = ("disponible", "reservada", "vendida", "anulada")


class Loteria(Base):
    """Lotería oficial con la que juegan las rifas."""

    __tablename__ = "loterias"

    id: Mapped[pk]
    nombre: Mapped[str] = mapped_column(String(100), unique=True)
    dias_sorteo: Mapped[str | None] = mapped_column(String(50))
    activa: Mapped[bool] = mapped_column(Boolean, default=True)


class Rifa(Base):
    """Rifa de un organizador: opción de boletas, plan, precio, reglas y estado (borrador → en venta → sorteada)."""

    __tablename__ = "rifas"
    __table_args__ = (
        CheckConstraint("cifras BETWEEN 1 AND 4", name="cifras"),
        CheckConstraint("series_por_boleta >= 1", name="series"),
        # La rifa siempre usa TODOS los números posibles, para que siempre haya un ganador
        CheckConstraint("total_numeros = power(10, cifras)", name="rango_completo"),
        CheckConstraint("mod(total_numeros, series_por_boleta) = 0", name="division_exacta"),
        CheckConstraint("total_boletas = total_numeros / series_por_boleta", name="total_boletas"),
        CheckConstraint("valor_boleta > 0", name="valor"),
        CheckConstraint("estado IN ('borrador','en_venta','cerrada','sorteada','anulada')", name="estado"),
        CheckConstraint("regla_seco_atrasado IN ('desierto','acumula')", name="regla_seco"),
        CheckConstraint("regla_mayor_sin_pagar IN ('paga_saldo','desierto')", name="regla_mayor"),
    )

    id: Mapped[pk]
    organizador_id: Mapped[int] = mapped_column(ForeignKey("organizadores.id", ondelete="RESTRICT"), index=True)
    loteria_id: Mapped[int] = mapped_column(ForeignKey("loterias.id", ondelete="RESTRICT"))
    plan_id: Mapped[int] = mapped_column(ForeignKey("planes.id", ondelete="RESTRICT"))
    nombre: Mapped[str] = mapped_column(String(150))
    descripcion: Mapped[str | None] = mapped_column(Text)
    numero_autorizacion: Mapped[str | None] = mapped_column(String(50))
    entidad_autoriza: Mapped[str | None] = mapped_column(String(150))
    fecha_autorizacion: Mapped[date | None] = mapped_column(Date)
    fecha_sorteo: Mapped[date] = mapped_column(Date)
    cifras: Mapped[int] = mapped_column(SmallInteger)
    total_numeros: Mapped[int] = mapped_column(Integer)
    series_por_boleta: Mapped[int] = mapped_column(SmallInteger)
    total_boletas: Mapped[int] = mapped_column(Integer)
    valor_boleta: Mapped[int] = mapped_column(Numeric(12, 0))
    estado: Mapped[str] = mapped_column(String(20), default="borrador")
    # Reglas que el organizador escoge al crear la rifa
    regla_seco_atrasado: Mapped[str] = mapped_column(String(10), default="desierto")  # desierto | acumula
    regla_mayor_sin_pagar: Mapped[str] = mapped_column(String(12), default="paga_saldo")  # paga_saldo | desierto
    # Vigencia: la rifa publicada funciona hasta esta fecha; después hay que renovar o queda bloqueada
    duracion_meses: Mapped[int] = mapped_column(SmallInteger, default=6)
    vigente_hasta: Mapped[date | None] = mapped_column(Date)
    ultimo_aviso_vencimiento: Mapped[date | None] = mapped_column(Date)
    fecha_creacion: Mapped[creado]

    cuotas: Mapped[list["Cuota"]] = relationship(order_by="Cuota.numero", cascade="all, delete-orphan")
    loteria: Mapped[Loteria] = relationship()
    plan: Mapped["Plan"] = relationship()  # noqa: F821
    organizador: Mapped["Organizador"] = relationship()  # noqa: F821
    premios: Mapped[list["Premio"]] = relationship(back_populates="rifa", order_by="Premio.orden")


class Premio(Base):
    """Premio de la rifa: el mayor o un premio seco, cada uno con su lotería y fecha."""

    __tablename__ = "premios"
    __table_args__ = (CheckConstraint("tipo IN ('mayor','seco')", name="tipo"),)

    id: Mapped[pk]
    rifa_id: Mapped[int] = mapped_column(ForeignKey("rifas.id", ondelete="CASCADE"), index=True)
    tipo: Mapped[str] = mapped_column(String(10))
    descripcion: Mapped[str] = mapped_column(String(300))
    valor_estimado: Mapped[int | None] = mapped_column(Numeric(14, 0))
    loteria_id: Mapped[int | None] = mapped_column(ForeignKey("loterias.id", ondelete="RESTRICT"))
    fecha_juego: Mapped[date | None] = mapped_column(Date)
    orden: Mapped[int] = mapped_column(SmallInteger, default=1)
    foto_url: Mapped[str | None] = mapped_column(String(300))  # foto del premio que sube el organizador (opcional)

    rifa: Mapped[Rifa] = relationship(back_populates="premios")
    loteria: Mapped[Loteria | None] = relationship()
    resultado: Mapped["Resultado | None"] = relationship(back_populates="premio", uselist=False)

    @property
    def fecha(self) -> date:
        """Fecha en que juega el premio (si no tiene, la del sorteo de la rifa)."""
        return self.fecha_juego or self.rifa.fecha_sorteo

    @property
    def nombre_loteria(self) -> str:
        """Nombre de la lotería del premio (si no tiene, la de la rifa)."""
        return (self.loteria or self.rifa.loteria).nombre


class Cuota(Base):
    """Plan de pagos de la boleta, definido por el organizador: cuánto y hasta cuándo."""

    __tablename__ = "cuotas_rifa"
    __table_args__ = (
        UniqueConstraint("rifa_id", "numero", name="uq_cuota_numero"),
        CheckConstraint("valor > 0", name="valor"),
    )

    id: Mapped[pk]
    rifa_id: Mapped[int] = mapped_column(ForeignKey("rifas.id", ondelete="CASCADE"), index=True)
    numero: Mapped[int] = mapped_column(SmallInteger)
    valor: Mapped[int] = mapped_column(Numeric(12, 0))
    fecha_limite: Mapped[date] = mapped_column(Date)


class Boleta(Base):
    """Boleta de una rifa: consecutivo, código de verificación, comprador, vendedor y estado."""

    __tablename__ = "boletas"
    __table_args__ = (
        UniqueConstraint("rifa_id", "consecutivo", name="uq_boleta_consecutivo"),
        UniqueConstraint("id", "rifa_id", name="uq_boleta_id_rifa"),  # destino de la FK compuesta de numeros_boleta
        CheckConstraint("formato IN ('virtual','impresa')", name="formato"),
        CheckConstraint("estado IN ('disponible','reservada','vendida','anulada')", name="estado"),
        CheckConstraint("estado <> 'reservada' OR reservada_hasta IS NOT NULL", name="reserva"),
    )

    id: Mapped[pk]
    rifa_id: Mapped[int] = mapped_column(ForeignKey("rifas.id", ondelete="RESTRICT"), index=True)
    consecutivo: Mapped[int] = mapped_column(Integer)
    codigo_verificacion: Mapped[str] = mapped_column(String(20), unique=True)
    cliente_id: Mapped[int | None] = mapped_column(ForeignKey("clientes.id", ondelete="RESTRICT"), index=True)
    vendedor_id: Mapped[int | None] = mapped_column(ForeignKey("vendedores.id", ondelete="RESTRICT"), index=True)
    formato: Mapped[str] = mapped_column(String(10), default="virtual")
    estado: Mapped[str] = mapped_column(String(15), default="disponible")
    reservada_hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    medio_difusion: Mapped[str | None] = mapped_column(String(20))
    fecha_venta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    rifa: Mapped[Rifa] = relationship()

    @property
    def etiqueta(self) -> str:
        """Cómo se nombra la boleta: con un solo número, es su número (07); con varios, su consecutivo (1, 2…)."""
        if self.rifa.series_por_boleta == 1:
            return str(self.consecutivo).zfill(self.rifa.cifras)
        return str(self.consecutivo)

    numeros: Mapped[list["NumeroBoleta"]] = relationship(back_populates="boleta", order_by="NumeroBoleta.numero")
    cliente: Mapped[Optional["Cliente"]] = relationship()  # noqa: F821
    vendedor: Mapped[Optional["Vendedor"]] = relationship()  # noqa: F821


class NumeroBoleta(Base):
    """Número que juega una boleta. Único por rifa: la base de datos impide repetirlo."""

    __tablename__ = "numeros_boleta"
    __table_args__ = (
        UniqueConstraint("rifa_id", "numero", name="uq_numero_por_rifa"),  # un número no se repite en la rifa
        ForeignKeyConstraint(
            ["boleta_id", "rifa_id"],
            ["boletas.id", "boletas.rifa_id"],
            name="fk_numero_boleta_misma_rifa",
            ondelete="CASCADE",
        ),
    )

    id: Mapped[pk]
    rifa_id: Mapped[int] = mapped_column(ForeignKey("rifas.id", ondelete="RESTRICT"))
    boleta_id: Mapped[int] = mapped_column(BigInteger, index=True)
    numero: Mapped[str] = mapped_column(String(4))

    boleta: Mapped[Boleta] = relationship(
        back_populates="numeros", foreign_keys=[boleta_id], primaryjoin="NumeroBoleta.boleta_id == Boleta.id"
    )


class Resultado(Base):
    """Resultado de la lotería para un premio: número que cayó, boleta que lo tenía y decisión."""

    __tablename__ = "resultados"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('pendiente','con_ganador','debe_saldo','desierto','acumulado','sin_ganador')", name="estado"
        ),
    )

    id: Mapped[pk]
    premio_id: Mapped[int] = mapped_column(ForeignKey("premios.id", ondelete="RESTRICT"), unique=True)
    numero_loteria: Mapped[str] = mapped_column(String(10))
    numero_jugado: Mapped[str] = mapped_column(String(4))
    numero_boleta_id: Mapped[int | None] = mapped_column(ForeignKey("numeros_boleta.id", ondelete="RESTRICT"))
    estado: Mapped[str] = mapped_column(String(15), default="pendiente")
    registrado_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"))
    fecha_registro: Mapped[creado]
    premio_entregado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evidencia_entrega_url: Mapped[str | None] = mapped_column(String(300))
    observacion: Mapped[str | None] = mapped_column(String(300))

    premio: Mapped[Premio] = relationship(back_populates="resultado")
    numero_boleta: Mapped["NumeroBoleta | None"] = relationship()
