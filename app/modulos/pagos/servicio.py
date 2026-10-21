"""Planes de cobro por rifa."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.excepciones import ErrorNegocio
from app.modulos.pagos.modelos import CobroRifa, CuentaCobro, MedioPago, Plan


def planes_activos(db: Session) -> list[Plan]:
    """Planes activos ordenados de menor a mayor, para la página de precios."""
    return list(db.scalars(select(Plan).where(Plan.activo.is_(True)).order_by(Plan.boletas_min)))


def plan_para(db: Session, total_boletas: int) -> Plan:
    """Plan activo cuyo rango contiene la cantidad de boletas de la rifa."""
    plan = db.scalar(
        select(Plan).where(Plan.activo.is_(True), Plan.boletas_min <= total_boletas, Plan.boletas_max >= total_boletas)
    )
    if plan is None:
        maximo = db.scalar(select(Plan.boletas_max).where(Plan.activo.is_(True)).order_by(Plan.boletas_max.desc()))
        raise ErrorNegocio(f"Por ahora RifaPlus permite rifas de hasta {maximo or 0} boletas.")
    return plan


# ---------- Pago del plan a RifaPlus ----------
def estado_cobro(cobro: CobroRifa | None) -> str:
    """Situación del pago del plan de una rifa.

    'gratis' (plan de $0), 'sin_enviar' (aún no pide publicar), 'en_revision' (envió el pago y espera al
    superadministrador), 'aprobado' o 'rechazado'.
    """
    if cobro is None or int(cobro.valor) == 0:
        return "gratis"
    if cobro.estado == "aprobado":
        return "aprobado"
    if cobro.estado == "rechazado":
        return "rechazado"
    return "en_revision" if cobro.fecha_pago else "sin_enviar"


def cuentas_rifaplus(db: Session) -> list[CuentaCobro]:
    """Cuentas activas de RifaPlus (sin organizador) donde los organizadores pagan sus planes."""
    return list(
        db.scalars(
            select(CuentaCobro)
            .where(CuentaCobro.organizador_id.is_(None), CuentaCobro.activa.is_(True))
            .order_by(CuentaCobro.id)
        )
    )


def medios_para_rifaplus(db: Session) -> list[MedioPago]:
    """Medios con los que se le puede pagar a RifaPlus: solo los de las cuentas activas que registró el superadmin.

    Si todavía no hay cuentas, devuelve los medios habilitados para RifaPlus (llave Bre-B, Nequi, Daviplata).
    """
    medios = list(
        db.scalars(
            select(MedioPago)
            .where(MedioPago.activo.is_(True), MedioPago.para_rifaplus.is_(True))
            .order_by(MedioPago.orden)
        )
    )
    con_cuenta = {c.medio_pago_id for c in cuentas_rifaplus(db)}
    return [m for m in medios if m.id in con_cuenta] if con_cuenta else medios


def enviar_pago_rifa(
    db: Session, cobro: CobroRifa, medio_pago_id: int, referencia: str | None, comprobante: str | None
) -> None:
    """El organizador informa el pago de su plan. Queda en revisión hasta que el superadministrador lo apruebe."""
    if estado_cobro(cobro) not in ("sin_enviar", "rechazado"):
        raise ErrorNegocio("El pago de esta rifa ya fue enviado.")
    medio = db.get(MedioPago, medio_pago_id)
    if medio is None or medio not in medios_para_rifaplus(db):
        raise ErrorNegocio("Escoja por dónde pagó.")
    referencia = (referencia or "").strip() or None
    if not referencia and not comprobante:
        raise ErrorNegocio("Escriba la referencia de la transacción o adjunte la foto del comprobante.")
    cuenta = next((c for c in cuentas_rifaplus(db) if c.medio_pago_id == medio.id), None)
    cobro.medio_pago_id, cobro.cuenta_destino_id = medio.id, cuenta.id if cuenta else None
    cobro.referencia, cobro.comprobante_url = referencia, comprobante or cobro.comprobante_url
    cobro.estado, cobro.motivo_rechazo = "pendiente", None
    cobro.fecha_pago, cobro.fecha_revision = datetime.now(timezone.utc), None
