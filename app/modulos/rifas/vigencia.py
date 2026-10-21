"""Vigencia de las rifas: cada rifa publicada funciona por un período pagado (por ejemplo 6 meses o 1 año).

- Al publicarse, la rifa queda vigente desde hoy por los meses de la duración que escogió el organizador.
- Antes de vencer se le avisa; si vence sin renovar, la rifa queda BLOQUEADA para el organizador (no puede vender,
  registrar pagos, registrar resultados, imprimir ni editar). Los compradores siguen pudiendo verificar su boleta.
- Al aprobarse una renovación, la vigencia se extiende desde la fecha de vencimiento (o desde hoy, si ya venció).
"""

import calendar
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.excepciones import ErrorNegocio
from app.modulos.pagos.modelos import Duracion, PrecioRifa, RenovacionRifa
from app.modulos.rifas.modelos import Rifa

DIAS_AVISO = (15, 3)  # se avisa al organizador cuando faltan estos días


def sumar_meses(fecha: date, meses: int) -> date:
    """Suma meses a una fecha; si el día no existe en el mes destino, usa el último día (31 ene + 1 mes = 28 feb)."""
    total = fecha.month - 1 + meses
    anio, mes = fecha.year + total // 12, total % 12 + 1
    return date(anio, mes, min(fecha.day, calendar.monthrange(anio, mes)[1]))


# ---------- Duraciones y precios ----------
def duraciones_activas(db: Session) -> list[Duracion]:
    """Duraciones que puede escoger el organizador, de la más corta a la más larga."""
    return list(db.scalars(select(Duracion).where(Duracion.activa.is_(True)).order_by(Duracion.meses)))


def precios_por_tipo(db: Session) -> dict[int, dict[int, int]]:
    """{plan_id: {duracion_id: valor}} con todos los precios guardados."""
    salida: dict[int, dict[int, int]] = {}
    for p in db.scalars(select(PrecioRifa)):
        salida.setdefault(p.plan_id, {})[p.duracion_id] = int(p.valor)
    return salida


def precio(db: Session, plan_id: int, duracion_id: int) -> tuple[Duracion, int]:
    """La duración y el precio de un tipo de rifa por esa duración. Error si no está disponible."""
    if not duracion_id:  # si no se escogió, la duración activa más corta
        primera = next(iter(duraciones_activas(db)), None)
        duracion_id = primera.id if primera else 0
    duracion = db.get(Duracion, duracion_id)
    if duracion is None or not duracion.activa:
        raise ErrorNegocio("Escoja por cuánto tiempo quiere la rifa.")
    fila = db.scalar(select(PrecioRifa).where(PrecioRifa.plan_id == plan_id, PrecioRifa.duracion_id == duracion_id))
    if fila is None:
        raise ErrorNegocio(f"Ese tipo de rifa no tiene precio por {duracion.nombre}. Escoja otra duración.")
    return duracion, int(fila.valor)


# ---------- Estado de la vigencia ----------
def bloqueada(rifa: Rifa, hoy: date | None = None) -> bool:
    """True si la rifa está en venta y ya pasó su fecha de vigencia sin renovar."""
    hoy = hoy or date.today()
    return rifa.estado == "en_venta" and rifa.vigente_hasta is not None and rifa.vigente_hasta < hoy


def dias_restantes(rifa: Rifa, hoy: date | None = None) -> int | None:
    """Días que le quedan de vigencia (negativo si ya venció); None si no aplica."""
    if rifa.estado != "en_venta" or rifa.vigente_hasta is None:
        return None
    return (rifa.vigente_hasta - (hoy or date.today())).days


def exigir_vigente(rifa: Rifa) -> None:
    """Detiene cualquier acción del organizador sobre una rifa bloqueada por falta de renovación."""
    if bloqueada(rifa):
        raise ErrorNegocio(
            f"La rifa «{rifa.nombre}» está bloqueada: su vigencia venció el "
            f"{rifa.vigente_hasta.strftime('%d/%m/%Y')}. Renuévela para seguir usándola."
        )


def iniciar(rifa: Rifa, hoy: date | None = None) -> None:
    """Al publicar: la rifa queda vigente desde hoy por los meses que pagó."""
    rifa.vigente_hasta = sumar_meses(hoy or date.today(), rifa.duracion_meses or 6)


def extender(rifa: Rifa, meses: int, hoy: date | None = None) -> None:
    """Al aprobar una renovación: suma los meses desde el vencimiento, o desde hoy si ya estaba vencida."""
    hoy = hoy or date.today()
    base = max(rifa.vigente_hasta or hoy, hoy)
    rifa.vigente_hasta = sumar_meses(base, meses)
    rifa.ultimo_aviso_vencimiento = None


# ---------- Renovaciones ----------
def renovacion_pendiente(db: Session, rifa: Rifa) -> RenovacionRifa | None:
    """La renovación que el organizador envió y espera revisión, si la hay."""
    return db.scalar(
        select(RenovacionRifa).where(RenovacionRifa.rifa_id == rifa.id, RenovacionRifa.estado == "pendiente")
    )


def ultima_rechazada(db: Session, rifa: Rifa) -> RenovacionRifa | None:
    """La última renovación rechazada (para mostrar el motivo)."""
    return db.scalar(
        select(RenovacionRifa)
        .where(RenovacionRifa.rifa_id == rifa.id, RenovacionRifa.estado == "rechazado")
        .order_by(RenovacionRifa.id.desc())
    )


def solicitar_renovacion(
    db: Session,
    rifa: Rifa,
    duracion_id: int,
    medio_pago_id: int | None,
    referencia: str | None,
    comprobante: str | None,
) -> RenovacionRifa:
    """El organizador pide renovar. Si el precio es $0, se aprueba sola; si no, queda en revisión."""
    from app.modulos.pagos.servicio import medios_para_rifaplus

    if rifa.estado != "en_venta":
        raise ErrorNegocio("Solo se renuevan rifas publicadas.")
    if renovacion_pendiente(db, rifa):
        raise ErrorNegocio("Ya envió una renovación y está en revisión.")
    duracion, valor = precio(db, rifa.plan_id, duracion_id)
    ahora = datetime.now(timezone.utc)
    renovacion = RenovacionRifa(rifa_id=rifa.id, meses=duracion.meses, valor=valor)
    if valor == 0:
        renovacion.estado, renovacion.fecha_revision = "aprobado", ahora
        extender(rifa, duracion.meses)
    else:
        medio = next((m for m in medios_para_rifaplus(db) if m.id == medio_pago_id), None)
        if medio is None:
            raise ErrorNegocio("Escoja por dónde pagó.")
        referencia = (referencia or "").strip() or None
        if not referencia and not comprobante:
            raise ErrorNegocio("Escriba la referencia de la transacción o adjunte la foto del comprobante.")
        renovacion.medio_pago_id, renovacion.referencia, renovacion.comprobante_url = medio.id, referencia, comprobante
        renovacion.fecha_pago = ahora
    db.add(renovacion)
    db.flush()
    return renovacion


def revisar_renovacion(
    db: Session, renovacion: RenovacionRifa, admin_id: int, aprobar: bool, motivo: str | None
) -> None:
    """El superadministrador aprueba (extiende la vigencia y desbloquea) o rechaza con motivo."""
    if renovacion.estado != "pendiente":
        raise ErrorNegocio("Esta renovación ya fue revisada.")
    if not aprobar and not (motivo or "").strip():
        raise ErrorNegocio("Escriba el motivo del rechazo; el organizador lo verá.")
    renovacion.estado = "aprobado" if aprobar else "rechazado"
    renovacion.motivo_rechazo = None if aprobar else motivo.strip()[:300]
    renovacion.revisado_por_id, renovacion.fecha_revision = admin_id, datetime.now(timezone.utc)
    if aprobar:
        extender(renovacion.rifa, renovacion.meses)


def renovaciones_por_revisar(db: Session) -> list[RenovacionRifa]:
    """Renovaciones enviadas que esperan revisión del superadministrador."""
    return list(
        db.scalars(
            select(RenovacionRifa).where(RenovacionRifa.estado == "pendiente").order_by(RenovacionRifa.fecha_pago)
        )
    )


# ---------- Avisos de vencimiento (se ejecuta una vez al día: python -m app.cli avisar-vencimientos) ----------
def avisos_del_dia(db: Session, hoy: date | None = None) -> list[tuple[Rifa, int]]:
    """Rifas a las que hoy les toca aviso: faltan 15 o 3 días, vencen hoy o vencieron ayer. Una sola vez por día."""
    hoy = hoy or date.today()
    rifas = db.scalars(select(Rifa).where(Rifa.estado == "en_venta", Rifa.vigente_hasta.is_not(None)))
    salida = []
    for rifa in rifas:
        dias = (rifa.vigente_hasta - hoy).days
        if (dias in (*DIAS_AVISO, 0, -1)) and rifa.ultimo_aviso_vencimiento != hoy:
            salida.append((rifa, dias))
    return salida


def texto_aviso(rifa: Rifa, dias: int, url: str) -> tuple[str, str]:
    """Asunto y mensaje del correo de aviso al organizador."""
    fecha = rifa.vigente_hasta.strftime("%d/%m/%Y")
    enlace = f"{url}/panel/rifas/{rifa.id}/renovar"
    if dias < 0:
        return (
            f"Su rifa «{rifa.nombre}» quedó bloqueada",
            f"La vigencia de su rifa «{rifa.nombre}» venció el {fecha} y quedó bloqueada: no puede vender boletas "
            f"ni registrar pagos hasta renovarla.\n\nRenuévela aquí: {enlace}",
        )
    cuando = "hoy" if dias == 0 else f"en {dias} días"
    return (
        f"Su rifa «{rifa.nombre}» vence {cuando}",
        f"La vigencia de su rifa «{rifa.nombre}» vence {cuando} ({fecha}). Si la rifa sigue después de esa fecha, "
        f"renuévela para que no se bloquee.\n\nRenueve aquí: {enlace}",
    )
