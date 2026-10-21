"""Cuentas y acceso: organizadores, usuarios, sesiones, tokens de seguridad e historial de ingresos."""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, creado, pk


class Organizador(Base):
    """Persona o empresa que se registra en RifaPlus para administrar sus rifas (tabla organizadores)."""

    __tablename__ = "organizadores"
    __table_args__ = (
        CheckConstraint("tipo_persona IN ('natural','juridica')", name="tipo_persona"),
        CheckConstraint("estado IN ('pendiente','activo','suspendido')", name="estado"),
        CheckConstraint("whatsapp_estado IN ('conectado','desconectado')", name="wa_estado"),
    )

    id: Mapped[pk]
    tipo_persona: Mapped[str] = mapped_column(String(10))
    nombre: Mapped[str] = mapped_column(String(150))
    tipo_documento: Mapped[str | None] = mapped_column(String(5))
    numero_documento: Mapped[str | None] = mapped_column(String(20), unique=True)
    celular: Mapped[str] = mapped_column(String(20))
    whatsapp: Mapped[str] = mapped_column(String(20))
    email: Mapped[str] = mapped_column(String(150), unique=True)
    direccion: Mapped[str | None] = mapped_column(String(200))
    ciudad: Mapped[str | None] = mapped_column(String(100))
    estado: Mapped[str] = mapped_column(String(15), default="pendiente")
    whatsapp_estado: Mapped[str] = mapped_column(String(15), default="desconectado")
    whatsapp_ultima_conexion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    limite_mensajes_hora: Mapped[int] = mapped_column(SmallInteger, default=30)
    acepta_tratamiento_datos: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Verificación de identidad: el superadministrador revisa a mano el nombre y el documento.
    # Sin verificar, el organizador puede publicar UNA rifa; desde la segunda debe estar verificado.
    verificado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verificado_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL", use_alter=True, name="fk_org_verificado_por")
    )
    fecha_creacion: Mapped[creado]

    usuarios: Mapped[list["Usuario"]] = relationship(
        back_populates="organizador", foreign_keys="Usuario.organizador_id"
    )

    @property
    def verificado(self) -> bool:
        """True si el superadministrador ya verificó su nombre y documento."""
        return self.verificado_en is not None


class Usuario(Base):
    """Cuenta con la que se ingresa. Un organizador tiene su usuario admin; el superadmin no tiene organizador."""

    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint("rol IN ('superadmin','admin','vendedor','colaborador')", name="rol"),
        CheckConstraint("(rol = 'superadmin') = (organizador_id IS NULL)", name="superadmin_sin_org"),
    )

    id: Mapped[pk]
    organizador_id: Mapped[int | None] = mapped_column(ForeignKey("organizadores.id", ondelete="RESTRICT"))
    nombre: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(150), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[str] = mapped_column(String(20), default="admin")
    debe_cambiar_clave: Mapped[bool] = mapped_column(Boolean, default=True)
    clave_cambiada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_verificado: Mapped[bool] = mapped_column(Boolean, default=False)
    intentos_fallidos: Mapped[int] = mapped_column(SmallInteger, default=0)
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    ultimo_acceso: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_creacion: Mapped[creado]

    organizador: Mapped[Organizador | None] = relationship(back_populates="usuarios", foreign_keys=[organizador_id])


class Sesion(Base):
    """Sesión abierta en un navegador. La cookie guarda un token y aquí solo su hash, con vencimiento."""

    __tablename__ = "sesiones"

    id: Mapped[pk]
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    ip: Mapped[str | None] = mapped_column(String(45))
    navegador: Mapped[str | None] = mapped_column(String(300))
    creada_en: Mapped[creado]
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cerrada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    usuario: Mapped[Usuario] = relationship()


class TokenSeguridad(Base):
    """Enlace de un solo uso para recuperar la clave o verificar el correo (hash, vencimiento, uso)."""

    __tablename__ = "tokens_seguridad"
    __table_args__ = (CheckConstraint("tipo IN ('verificar_email','recuperar_clave')", name="tipo"),)

    id: Mapped[pk]
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    tipo: Mapped[str] = mapped_column(String(20))
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    creado_en: Mapped[creado]
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    usado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class HistorialAcceso(Base):
    """Registro de cada intento de ingreso, exitoso o fallido, con IP y fecha."""

    __tablename__ = "historial_accesos"

    id: Mapped[pk]
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), index=True)
    email_intentado: Mapped[str] = mapped_column(String(150))
    evento: Mapped[str] = mapped_column(String(30))
    exitoso: Mapped[bool] = mapped_column(Boolean)
    ip: Mapped[str | None] = mapped_column(String(45))
    fecha: Mapped[creado]
