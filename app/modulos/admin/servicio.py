"""Superadministrador: organizadores, sus rifas, cobros de planes y borrados con confirmación."""

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from app.core.excepciones import ErrorNegocio
from app.modulos.acceso.modelos import HistorialAcceso, Organizador, Sesion, TokenSeguridad, Usuario
from app.modulos.auditoria import servicio as auditoria
from app.modulos.legal.modelos import Aceptacion
from app.modulos.mensajes.modelos import MensajeWhatsapp
from app.modulos.pagos.modelos import CobroRifa, CuentaCobro, EntregaVendedor, MedioPago, Pago, Plan
from app.modulos.personas.modelos import Cliente, Vendedor
from app.modulos.rifas import vigencia
from app.modulos.rifas.modelos import Boleta, NumeroBoleta, Premio, Resultado, Rifa
from app.modulos.soporte.modelos import ConversacionSoporte


@dataclass
class FilaOrganizador:
    """Organizador con su número de rifas y su último ingreso, para las tablas."""

    organizador: Organizador
    rifas: int
    ultimo_acceso: datetime | None


@dataclass
class FilaRifa:
    """Rifa con boletas vendidas, dinero recaudado y su cobro, para la ficha del organizador."""

    rifa: Rifa
    vendidas: int
    recaudado: int
    cobro: CobroRifa | None


def resumen(db: Session) -> dict:
    """Cifras generales: organizadores, rifas, cobros por revisar e ingresos aprobados."""
    contar = lambda modelo, *filtros: db.scalar(select(func.count()).select_from(modelo).where(*filtros))  # noqa: E731
    return {
        "organizadores": contar(Organizador),
        "activos": contar(Organizador, Organizador.estado == "activo"),
        "suspendidos": contar(Organizador, Organizador.estado == "suspendido"),
        "por_verificar": contar(Organizador, Organizador.verificado_en.is_(None)),
        "rifas": contar(Rifa),
        "en_venta": contar(Rifa, Rifa.estado == "en_venta"),
        "cobros_pendientes": contar(
            CobroRifa, CobroRifa.estado == "pendiente", CobroRifa.valor > 0, CobroRifa.fecha_pago.is_not(None)
        ),
        "soporte_pendiente": db.scalar(
            select(func.count()).select_from(ConversacionSoporte).where(ConversacionSoporte.estado == "pendiente")
        ),
        "ingresos": int(
            db.scalar(select(func.coalesce(func.sum(CobroRifa.valor), 0)).where(CobroRifa.estado == "aprobado")) or 0
        ),
    }


def organizadores(db: Session, buscar: str = "", estado: str = "") -> list[FilaOrganizador]:
    """Organizadores filtrados por texto (nombre, correo, celular, documento) y estado."""
    rifas = select(Rifa.organizador_id, func.count().label("n")).group_by(Rifa.organizador_id).subquery()
    acceso = (
        select(Usuario.organizador_id, func.max(Usuario.ultimo_acceso).label("u"))
        .group_by(Usuario.organizador_id)
        .subquery()
    )
    consulta = (
        select(Organizador, func.coalesce(rifas.c.n, 0), acceso.c.u)
        .outerjoin(rifas, rifas.c.organizador_id == Organizador.id)
        .outerjoin(acceso, acceso.c.organizador_id == Organizador.id)
        .order_by(Organizador.fecha_creacion.desc())
    )
    if buscar.strip():
        patron = f"%{buscar.strip()}%"
        consulta = consulta.where(
            or_(
                Organizador.nombre.ilike(patron),
                Organizador.email.ilike(patron),
                Organizador.celular.ilike(patron),
                Organizador.whatsapp.ilike(patron),
                Organizador.numero_documento.ilike(patron),
            )
        )
    if estado == "por_verificar":
        consulta = consulta.where(Organizador.verificado_en.is_(None))
    elif estado == "verificado":
        consulta = consulta.where(Organizador.verificado_en.is_not(None))
    elif estado:
        consulta = consulta.where(Organizador.estado == estado)
    return [FilaOrganizador(o, n, u) for o, n, u in db.execute(consulta.limit(500)).all()]


def rifas_de(db: Session, organizador_id: int) -> list[FilaRifa]:
    """Rifas de un organizador con sus cifras de venta y su cobro."""
    vendidas = (
        select(Boleta.rifa_id, func.count().label("n"))
        .where(Boleta.estado == "vendida")
        .group_by(Boleta.rifa_id)
        .subquery()
    )
    recaudo = (
        select(Boleta.rifa_id, func.sum(Pago.monto).label("total"))
        .join(Pago, Pago.boleta_id == Boleta.id)
        .where(Pago.estado == "aprobado")
        .group_by(Boleta.rifa_id)
        .subquery()
    )
    filas = db.execute(
        select(Rifa, func.coalesce(vendidas.c.n, 0), func.coalesce(recaudo.c.total, 0), CobroRifa)
        .outerjoin(vendidas, vendidas.c.rifa_id == Rifa.id)
        .outerjoin(recaudo, recaudo.c.rifa_id == Rifa.id)
        .outerjoin(CobroRifa, CobroRifa.rifa_id == Rifa.id)
        .where(Rifa.organizador_id == organizador_id)
        .order_by(Rifa.fecha_creacion.desc())
    ).all()
    return [FilaRifa(r, int(v), int(t), c) for r, v, t, c in filas]


def cobros_pendientes(db: Session) -> list[CobroRifa]:
    """Pagos de planes que los organizadores ya enviaron y esperan revisión (del más antiguo al más nuevo)."""
    return list(
        db.scalars(
            select(CobroRifa)
            .where(CobroRifa.estado == "pendiente", CobroRifa.valor > 0, CobroRifa.fecha_pago.is_not(None))
            .order_by(CobroRifa.fecha_pago)
        )
    )


# ---------- Acciones ----------
def cambiar_estado(db: Session, admin: Usuario, organizador: Organizador, nuevo: str, ip: str | None) -> None:
    """Activa o suspende al organizador; al suspender, cierra sus sesiones abiertas."""
    if nuevo not in ("activo", "suspendido"):
        raise ErrorNegocio("Estado no válido.")
    anterior = organizador.estado
    organizador.estado = nuevo
    if nuevo == "suspendido":  # cierra sus sesiones abiertas
        ids = select(Usuario.id).where(Usuario.organizador_id == organizador.id)
        db.execute(
            update(Sesion)
            .where(Sesion.usuario_id.in_(ids), Sesion.cerrada_en.is_(None))
            .values(cerrada_en=datetime.now(timezone.utc))
        )
    auditoria.registrar(
        db, admin, "organizadores", organizador.id, nuevo, ip=ip, anterior={"estado": anterior}, nuevo={"estado": nuevo}
    )
    db.commit()


def cambiar_verificacion(
    db: Session, admin: Usuario, organizador: Organizador, verificar: bool, ip: str | None
) -> None:
    """Marca al organizador como verificado (revisó su nombre y documento) o le quita la verificación."""
    if verificar and not organizador.numero_documento:
        raise ErrorNegocio("Este organizador no tiene documento registrado; no se puede verificar.")
    organizador.verificado_en = datetime.now(timezone.utc) if verificar else None
    organizador.verificado_por_id = admin.id if verificar else None
    auditoria.registrar(
        db,
        admin,
        "organizadores",
        organizador.id,
        "verificar" if verificar else "quitar_verificacion",
        ip=ip,
        nuevo={"nombre": organizador.nombre, "documento": organizador.numero_documento},
    )
    db.commit()


def revisar_cobro(
    db: Session,
    admin: Usuario,
    cobro: CobroRifa,
    aprobar: bool,
    referencia: str | None,
    motivo: str | None,
    ip: str | None,
) -> None:
    """Aprueba o rechaza el pago de un plan. Al aprobar, la rifa queda publicada; rechazar exige el motivo."""
    if cobro.estado != "pendiente" or cobro.fecha_pago is None:
        raise ErrorNegocio("Este cobro ya fue revisado o el organizador aún no ha enviado el pago.")
    if not aprobar and not (motivo or "").strip():
        raise ErrorNegocio("Escriba el motivo del rechazo; el organizador lo verá.")
    cobro.estado = "aprobado" if aprobar else "rechazado"
    cobro.referencia = (referencia or "").strip() or cobro.referencia
    cobro.motivo_rechazo = None if aprobar else motivo.strip()[:300]
    cobro.revisado_por_id = admin.id
    cobro.fecha_revision = datetime.now(timezone.utc)
    rifa = db.get(Rifa, cobro.rifa_id)
    if aprobar and rifa.estado == "borrador":  # el organizador ya pidió publicar al enviar el pago
        rifa.estado = "en_venta"
        vigencia.iniciar(rifa)
    auditoria.registrar(
        db,
        admin,
        "cobros_rifa",
        cobro.id,
        cobro.estado,
        ip=ip,
        nuevo={
            "rifa_id": cobro.rifa_id,
            "valor": int(cobro.valor),
            "referencia": cobro.referencia,
            "rifa_publicada": aprobar,
        },
    )
    db.commit()


# ---------- Cuentas de RifaPlus ----------
def cuentas_rifaplus(db: Session) -> list[CuentaCobro]:
    """Todas las cuentas de RifaPlus (activas e inactivas)."""
    return list(db.scalars(select(CuentaCobro).where(CuentaCobro.organizador_id.is_(None)).order_by(CuentaCobro.id)))


def crear_cuenta(db: Session, admin: Usuario, medio_pago_id: int, numero: str, titular: str, ip: str | None) -> None:
    """Agrega una cuenta de RifaPlus (llave Bre-B, Nequi o Daviplata) para recibir los pagos de los planes."""
    medio = db.get(MedioPago, medio_pago_id)
    if medio is None or not medio.para_rifaplus:
        raise ErrorNegocio("Escoja llave Bre-B, Nequi o Daviplata.")
    numero, titular = " ".join(numero.split()), " ".join(titular.split())
    minimo = 3 if medio.codigo == "bre_b" else 7  # una llave puede ser corta, por ejemplo @GE
    if len(numero) < minimo or len(titular) < 2:
        raise ErrorNegocio("Escriba la llave o el número de la cuenta y el nombre del titular.")
    cuenta = CuentaCobro(organizador_id=None, medio_pago_id=medio.id, numero_cuenta=numero[:30], titular=titular[:150])
    db.add(cuenta)
    db.flush()
    auditoria.registrar(
        db, admin, "cuentas_cobro", cuenta.id, "crear", ip=ip, nuevo={"medio": medio.nombre, "numero": numero}
    )
    db.commit()


def cambiar_cuenta(db: Session, admin: Usuario, cuenta: CuentaCobro, activa: bool, ip: str | None) -> None:
    """Activa o desactiva una cuenta de RifaPlus (las inactivas no se muestran a los organizadores)."""
    cuenta.activa = activa
    auditoria.registrar(db, admin, "cuentas_cobro", cuenta.id, "activar" if activa else "desactivar", ip=ip)
    db.commit()


def _confirmar(texto: str, esperado: str) -> None:
    """Exige que el texto de confirmación coincida (sin importar mayúsculas) antes de borrar."""
    if texto.strip().lower() != esperado.strip().lower():
        raise ErrorNegocio(f"Para confirmar escriba exactamente: {esperado}")


def eliminar_rifa(db: Session, admin: Usuario, rifa: Rifa, confirmacion: str, ip: str | None) -> None:
    """Borra la rifa con TODO lo suyo: boletas, números, pagos, premios, resultados y su cobro."""
    _confirmar(confirmacion, rifa.nombre)
    boletas = select(Boleta.id).where(Boleta.rifa_id == rifa.id)
    datos = {"nombre": rifa.nombre, "organizador_id": rifa.organizador_id, "boletas": rifa.total_boletas}
    db.execute(update(Aceptacion).where(Aceptacion.rifa_id == rifa.id).values(rifa_id=None))
    db.execute(delete(MensajeWhatsapp).where(MensajeWhatsapp.boleta_id.in_(boletas)))
    db.execute(delete(Pago).where(Pago.boleta_id.in_(boletas)))
    db.execute(delete(EntregaVendedor).where(EntregaVendedor.rifa_id == rifa.id))
    db.execute(delete(Resultado).where(Resultado.premio_id.in_(select(Premio.id).where(Premio.rifa_id == rifa.id))))
    db.execute(delete(NumeroBoleta).where(NumeroBoleta.rifa_id == rifa.id))
    db.execute(delete(Boleta).where(Boleta.rifa_id == rifa.id))
    db.execute(delete(CobroRifa).where(CobroRifa.rifa_id == rifa.id))
    db.execute(delete(Premio).where(Premio.rifa_id == rifa.id))
    auditoria.registrar(db, admin, "rifas", rifa.id, "eliminar_admin", anterior=datos, ip=ip)
    db.delete(rifa)
    db.commit()


def eliminar_organizador(
    db: Session, admin: Usuario, organizador: Organizador, confirmacion: str, ip: str | None
) -> None:
    """Borra un organizador sin rifas, con sus usuarios, compradores y vendedores."""
    _confirmar(confirmacion, organizador.email)
    if db.scalar(select(func.count()).select_from(Rifa).where(Rifa.organizador_id == organizador.id)):
        raise ErrorNegocio("Primero elimine las rifas de este organizador.")
    usuarios = select(Usuario.id).where(Usuario.organizador_id == organizador.id)
    datos = {"nombre": organizador.nombre, "email": organizador.email}
    db.execute(
        delete(Aceptacion).where(or_(Aceptacion.organizador_id == organizador.id, Aceptacion.usuario_id.in_(usuarios)))
    )
    db.execute(delete(MensajeWhatsapp).where(MensajeWhatsapp.organizador_id == organizador.id))
    db.execute(update(HistorialAcceso).where(HistorialAcceso.usuario_id.in_(usuarios)).values(usuario_id=None))
    db.execute(delete(Sesion).where(Sesion.usuario_id.in_(usuarios)))
    db.execute(delete(TokenSeguridad).where(TokenSeguridad.usuario_id.in_(usuarios)))
    db.execute(update(Cliente).where(Cliente.organizador_id == organizador.id).values(referido_por_id=None))
    db.execute(delete(Cliente).where(Cliente.organizador_id == organizador.id))
    db.execute(delete(Vendedor).where(Vendedor.organizador_id == organizador.id))
    db.execute(delete(CuentaCobro).where(CuentaCobro.organizador_id == organizador.id))
    db.execute(delete(Usuario).where(Usuario.organizador_id == organizador.id))
    auditoria.registrar(db, admin, "organizadores", organizador.id, "eliminar_admin", anterior=datos, ip=ip)
    db.delete(organizador)
    db.commit()


def plan_de(db: Session, plan_id: int) -> Plan | None:
    """Plan por su id."""
    return db.get(Plan, plan_id)
