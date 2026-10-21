"""Sesiones de usuario guardadas en la base de datos (cookie con token aleatorio)."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import obtener_config
from app.core.seguridad import generar_token, hash_token
from app.modulos.acceso.modelos import Sesion, Usuario

NOMBRE_COOKIE = "rifaplus_sesion"


def ahora() -> datetime:
    """Fecha y hora actual en UTC."""
    return datetime.now(timezone.utc)


def crear_sesion(db: Session, usuario: Usuario, ip: str | None, navegador: str | None) -> str:
    """Crea una sesión nueva y devuelve el token que va en la cookie (en la base solo queda su hash)."""
    token = generar_token()
    db.add(
        Sesion(
            usuario_id=usuario.id,
            token_hash=hash_token(token),
            ip=ip,
            navegador=(navegador or "")[:300],
            expira_en=ahora() + timedelta(hours=obtener_config().sesion_horas),
        )
    )
    return token


def usuario_de_token(db: Session, token: str | None) -> Usuario | None:
    """Usuario dueño del token si la sesión está abierta, vigente y el organizador no está suspendido."""
    if not token:
        return None
    sesion = db.scalar(
        select(Sesion).where(
            Sesion.token_hash == hash_token(token), Sesion.cerrada_en.is_(None), Sesion.expira_en > ahora()
        )
    )
    if sesion is None or not sesion.usuario.activo:
        return None
    if sesion.usuario.organizador and sesion.usuario.organizador.estado == "suspendido":
        return None
    return sesion.usuario


def cerrar_sesion(db: Session, token: str | None) -> None:
    """Marca como cerrada la sesión de ese token."""
    if token:
        db.execute(update(Sesion).where(Sesion.token_hash == hash_token(token)).values(cerrada_en=ahora()))


def cerrar_otras_sesiones(db: Session, usuario_id: int, token_actual: str | None) -> None:
    """Al cambiar la clave se cierran las sesiones abiertas en otros dispositivos."""
    consulta = update(Sesion).where(Sesion.usuario_id == usuario_id, Sesion.cerrada_en.is_(None))
    if token_actual:
        consulta = consulta.where(Sesion.token_hash != hash_token(token_actual))
    db.execute(consulta.values(cerrada_en=ahora()))
