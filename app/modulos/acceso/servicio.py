"""Casos de uso del módulo de acceso: registro, ingreso y cambio de clave."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.core.config import obtener_config
from app.core.excepciones import ErrorNegocio
from app.core.seguridad import (
    cifrar_clave,
    generar_clave_temporal,
    generar_token,
    hash_token,
    validar_clave_nueva,
    verificar_clave,
)
from app.modulos.acceso import sesiones
from app.modulos.acceso.esquemas import RegistroOrganizador
from app.modulos.acceso.modelos import HistorialAcceso, Organizador, TokenSeguridad, Usuario
from app.modulos.legal import servicio as legal


def _ahora() -> datetime:
    """Fecha y hora actual en UTC."""
    return datetime.now(timezone.utc)


@dataclass
class ResultadoRegistro:
    """Lo que devuelve el registro: el organizador creado y su clave temporal."""

    organizador: Organizador
    clave_temporal: str


@dataclass
class ResultadoIngreso:
    """Lo que devuelve un ingreso exitoso: el usuario y el token para la cookie."""

    usuario: Usuario
    token: str


def registrar_organizador(db: Session, datos: RegistroOrganizador, ip: str | None = None) -> ResultadoRegistro:
    """Crea organizador, usuario admin con clave temporal y aceptaciones legales; envía la clave."""
    if db.scalar(select(exists().where(Usuario.email == datos.email))) or db.scalar(
        select(exists().where(Organizador.email == datos.email))
    ):
        raise ErrorNegocio("Ya existe una cuenta con ese correo. Ingrese con él o recupere su clave.")
    if datos.numero_documento and db.scalar(
        select(exists().where(Organizador.numero_documento == datos.numero_documento))
    ):
        raise ErrorNegocio("Ya existe una cuenta con ese número de documento.")

    clave = generar_clave_temporal()
    organizador = Organizador(
        tipo_persona=datos.tipo_persona,
        nombre=datos.nombre,
        email=datos.email,
        celular=datos.celular,
        whatsapp=datos.whatsapp,
        direccion=datos.direccion,
        ciudad=datos.ciudad,
        tipo_documento=datos.tipo_documento,
        numero_documento=datos.numero_documento,
        estado="pendiente",
        acepta_tratamiento_datos=_ahora(),
    )
    db.add(organizador)
    db.flush()
    usuario = Usuario(
        organizador_id=organizador.id,
        nombre=datos.nombre,
        email=datos.email,
        password_hash=cifrar_clave(clave),
        rol="admin",
        debe_cambiar_clave=True,
    )
    db.add(usuario)
    db.flush()
    for documento, version in (
        ("terminos", legal.VERSION_TERMINOS),
        ("tratamiento_datos", legal.VERSION_TRATAMIENTO_DATOS),
    ):
        legal.registrar(
            db, usuario_id=usuario.id, organizador_id=organizador.id, documento=documento, version=version, ip=ip
        )
    db.commit()
    return ResultadoRegistro(organizador, clave)


def ingresar(db: Session, email: str, clave: str, ip: str | None, navegador: str | None) -> ResultadoIngreso:
    """Verifica correo y clave, aplica bloqueo por intentos fallidos y abre la sesión."""
    cfg = obtener_config()
    email = email.lower().strip()
    ahora = _ahora()
    usuario = db.scalar(select(Usuario).where(Usuario.email == email))

    def fallo(mensaje: str, evento: str) -> ErrorNegocio:
        """Registra el intento fallido en el historial y devuelve el error para mostrar."""
        db.add(
            HistorialAcceso(
                usuario_id=usuario.id if usuario else None,
                email_intentado=email[:150],
                evento=evento,
                exitoso=False,
                ip=ip,
            )
        )
        db.commit()
        return ErrorNegocio(mensaje)

    if usuario and usuario.bloqueado_hasta and usuario.bloqueado_hasta > ahora:
        minutos = int((usuario.bloqueado_hasta - ahora).total_seconds() // 60) + 1
        raise fallo(
            f"La cuenta está bloqueada por intentos fallidos. Intente de nuevo en {minutos} minutos.", "bloqueado"
        )
    if usuario is None or not usuario.activo or not verificar_clave(clave, usuario.password_hash):
        if usuario:
            usuario.intentos_fallidos += 1
            if usuario.intentos_fallidos >= cfg.max_intentos_fallidos:
                usuario.bloqueado_hasta = ahora + timedelta(minutes=cfg.minutos_bloqueo)
                usuario.intentos_fallidos = 0
        raise fallo("Correo o clave incorrectos.", "clave_incorrecta")

    if usuario.organizador and usuario.organizador.estado == "suspendido":
        raise fallo("Su cuenta está suspendida. Comuníquese con RifaPlus.", "suspendido")

    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    usuario.ultimo_acceso = ahora
    token = sesiones.crear_sesion(db, usuario, ip, navegador)
    db.add(HistorialAcceso(usuario_id=usuario.id, email_intentado=email, evento="ingreso", exitoso=True, ip=ip))
    db.commit()
    return ResultadoIngreso(usuario, token)


def cambiar_clave(
    db: Session,
    usuario: Usuario,
    clave_actual: str,
    clave_nueva: str,
    confirmacion: str,
    token_actual: str | None,
    ip: str | None,
) -> bool:
    """Cambia la clave. Devuelve True si era el primer ingreso (clave temporal)."""
    if not verificar_clave(clave_actual, usuario.password_hash):
        raise ErrorNegocio("La clave actual no es correcta.")
    if clave_actual == clave_nueva:
        raise ErrorNegocio("La clave nueva debe ser distinta a la actual.")
    error = validar_clave_nueva(clave_nueva, confirmacion)
    if error:
        raise ErrorNegocio(error)

    primer_ingreso = usuario.debe_cambiar_clave
    usuario.password_hash = cifrar_clave(clave_nueva)
    usuario.debe_cambiar_clave = False
    usuario.clave_cambiada_en = _ahora()
    if primer_ingreso and usuario.organizador and usuario.organizador.estado == "pendiente":
        usuario.organizador.estado = "activo"
    sesiones.cerrar_otras_sesiones(db, usuario.id, token_actual)
    db.add(
        HistorialAcceso(
            usuario_id=usuario.id, email_intentado=usuario.email, evento="cambio_clave", exitoso=True, ip=ip
        )
    )
    db.commit()
    return primer_ingreso


# ---------- Recuperar la clave ----------
MINUTOS_ENLACE = 60


def pedir_recuperacion(db: Session, email: str) -> tuple[Usuario, str] | None:
    """Crea un enlace de un solo uso para cambiar la clave. Devuelve (usuario, token) o None si el correo no existe.

    La ruta muestra el mismo mensaje exista o no el correo, para no revelar quién tiene cuenta.
    """
    usuario = db.scalar(select(Usuario).where(Usuario.email == email.lower().strip(), Usuario.activo.is_(True)))
    if usuario is None:
        return None
    token = generar_token()
    db.add(
        TokenSeguridad(
            usuario_id=usuario.id,
            tipo="recuperar_clave",
            token_hash=hash_token(token),
            expira_en=_ahora() + timedelta(minutes=MINUTOS_ENLACE),
        )
    )
    db.commit()
    return usuario, token


def token_valido(db: Session, token: str) -> TokenSeguridad | None:
    """El token de recuperación si existe, no se ha usado y no ha vencido."""
    return db.scalar(
        select(TokenSeguridad).where(
            TokenSeguridad.token_hash == hash_token(token),
            TokenSeguridad.tipo == "recuperar_clave",
            TokenSeguridad.usado_en.is_(None),
            TokenSeguridad.expira_en > _ahora(),
        )
    )


def restablecer_con_token(db: Session, token: str, clave_nueva: str, confirmacion: str, ip: str | None) -> None:
    """Cambia la clave con el enlace del correo: lo marca usado, desbloquea la cuenta y cierra las sesiones."""
    registro = token_valido(db, token)
    if registro is None:
        raise ErrorNegocio("El enlace ya se usó o venció. Pida uno nuevo.")
    error = validar_clave_nueva(clave_nueva, confirmacion)
    if error:
        raise ErrorNegocio(error)
    usuario = db.get(Usuario, registro.usuario_id)
    usuario.password_hash = cifrar_clave(clave_nueva)
    usuario.debe_cambiar_clave = False
    usuario.clave_cambiada_en = _ahora()
    usuario.intentos_fallidos, usuario.bloqueado_hasta = 0, None
    usuario.email_verificado = True  # abrió el enlace que le llegó al correo
    if usuario.organizador and usuario.organizador.estado == "pendiente":
        usuario.organizador.estado = "activo"
    registro.usado_en = _ahora()
    sesiones.cerrar_otras_sesiones(db, usuario.id, None)
    db.add(
        HistorialAcceso(
            usuario_id=usuario.id, email_intentado=usuario.email, evento="recuperar_clave", exitoso=True, ip=ip
        )
    )
    db.commit()


def restablecer_por_admin(db: Session, usuario: Usuario) -> str:
    """El superadministrador le pone una clave temporal nueva a un usuario; debe cambiarla al ingresar."""
    clave = generar_clave_temporal()
    usuario.password_hash = cifrar_clave(clave)
    usuario.debe_cambiar_clave = True
    usuario.intentos_fallidos, usuario.bloqueado_hasta = 0, None
    sesiones.cerrar_otras_sesiones(db, usuario.id, None)
    return clave
