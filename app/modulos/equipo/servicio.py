"""Equipo del organizador: personas que le ayudan a manejar sus rifas con su propio usuario y clave.

Solo el organizador (rol «admin») agrega o desactiva colaboradores; nadie entra a su panel sin que él lo agregue.
Los colaboradores pueden crear y editar rifas, vender, registrar pagos y resultados. No pueden manejar el equipo
ni eliminar rifas. Todo lo que hacen queda en la auditoría con su nombre.
"""

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.excepciones import ErrorNegocio
from app.core.seguridad import cifrar_clave, generar_clave_temporal
from app.modulos.acceso.modelos import Sesion, Usuario
from app.modulos.auditoria import servicio as auditoria

MAX_COLABORADORES = 10


def es_dueno(usuario: Usuario) -> bool:
    """True si es el dueño de la cuenta del organizador (no un colaborador)."""
    return usuario.rol == "admin"


def exigir_dueno(usuario: Usuario) -> None:
    """Solo el organizador puede hacer esto; los colaboradores no."""
    if not es_dueno(usuario):
        raise ErrorNegocio("Esta opción es solo para el organizador dueño de la cuenta.")


def miembros(db: Session, organizador_id: int) -> list[Usuario]:
    """Todos los usuarios del organizador: él primero y luego sus colaboradores."""
    return list(
        db.scalars(
            select(Usuario)
            .where(Usuario.organizador_id == organizador_id)
            .order_by((Usuario.rol == "admin").desc(), Usuario.nombre)
        )
    )


def agregar(db: Session, dueno: Usuario, nombre: str, email: str, ip: str | None) -> tuple[Usuario, str]:
    """Crea el usuario del colaborador con una clave temporal (debe cambiarla al entrar). Devuelve (usuario, clave)."""
    exigir_dueno(dueno)
    nombre, email = " ".join((nombre or "").split()), (email or "").strip().lower()
    if len(nombre) < 3:
        raise ErrorNegocio("Escriba el nombre completo de la persona.")
    if "@" not in email or "." not in email.split("@")[-1]:
        raise ErrorNegocio("Escriba un correo válido.")
    if db.scalar(select(Usuario.id).where(func.lower(Usuario.email) == email)):
        raise ErrorNegocio("Ese correo ya tiene una cuenta en RifaPlus. Use otro correo.")
    activos = db.scalar(
        select(func.count())
        .select_from(Usuario)
        .where(Usuario.organizador_id == dueno.organizador_id, Usuario.rol == "colaborador", Usuario.activo.is_(True))
    )
    if activos >= MAX_COLABORADORES:
        raise ErrorNegocio(f"Puede tener hasta {MAX_COLABORADORES} colaboradores activos.")
    clave = generar_clave_temporal()
    colaborador = Usuario(
        nombre=nombre,
        email=email,
        password_hash=cifrar_clave(clave),
        rol="colaborador",
        organizador_id=dueno.organizador_id,
        debe_cambiar_clave=True,
    )
    db.add(colaborador)
    db.flush()
    auditoria.registrar(
        db, dueno, "usuarios", colaborador.id, "agregar_colaborador", ip=ip, nuevo={"nombre": nombre, "email": email}
    )
    db.commit()
    return colaborador, clave


def cambiar_estado(db: Session, dueno: Usuario, colaborador_id: int, activo: bool, ip: str | None) -> Usuario:
    """Activa o desactiva a un colaborador. Al desactivarlo se cierran sus sesiones al instante."""
    exigir_dueno(dueno)
    colaborador = db.get(Usuario, colaborador_id)
    if colaborador is None or colaborador.organizador_id != dueno.organizador_id or colaborador.rol != "colaborador":
        raise ErrorNegocio("Esa persona no es de su equipo.")
    colaborador.activo = activo
    if not activo:
        from datetime import datetime, timezone

        db.execute(
            update(Sesion)
            .where(Sesion.usuario_id == colaborador.id, Sesion.cerrada_en.is_(None))
            .values(cerrada_en=datetime.now(timezone.utc))
        )
    auditoria.registrar(db, dueno, "usuarios", colaborador.id, "activar" if activo else "desactivar", ip=ip)
    db.commit()
    return colaborador
