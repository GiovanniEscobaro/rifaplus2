"""Sorteos: registrar el resultado de la lotería, encontrar al ganador y aplicar las reglas del organizador."""

from dataclasses import dataclass
from datetime import date, datetime, timezone
from urllib.parse import quote

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import obtener_config
from app.core.excepciones import ErrorNegocio
from app.core.plantillas import fecha_larga, pesos
from app.modulos.acceso.modelos import Usuario
from app.modulos.auditoria import servicio as auditoria
from app.modulos.pagos.modelos import Pago
from app.modulos.rifas import vigencia
from app.modulos.rifas.cuotas import debido_hasta
from app.modulos.rifas.generador import numero_jugado
from app.modulos.rifas.modelos import Boleta, NumeroBoleta, Premio, Resultado, Rifa

ZONA = "America/Bogota"

TEXTOS_ESTADO = {
    "con_ganador": "Tiene ganador",
    "debe_saldo": "Ganador con saldo pendiente: debe pagar antes de recibir el premio",
    "desierto": "Desierto",
    "acumulado": "Se acumula para el siguiente premio seco",
    "sin_ganador": "Sin ganador",
}


@dataclass
class Sorteo:
    """Un premio con su resultado, la boleta que tenía el número y los premios acumulados que incluye."""

    premio: Premio
    resultado: Resultado | None
    boleta: Boleta | None
    acumulados: list[Premio]

    @property
    def ganador(self):
        """Comprador que ganó el premio, o None si quedó desierto, acumulado o sin resultado."""
        return (
            self.boleta.cliente
            if self.boleta and self.resultado and self.resultado.estado in ("con_ganador", "debe_saldo")
            else None
        )


def pagado_hasta(db: Session, boleta_id: int, fecha: date) -> int:
    """Pagos aprobados hasta el final de ese día, en hora de Colombia."""
    total = db.scalar(
        select(func.coalesce(func.sum(Pago.monto), 0)).where(
            Pago.boleta_id == boleta_id,
            Pago.estado == "aprobado",
            func.date(func.timezone(ZONA, Pago.fecha_pago)) <= fecha,
        )
    )
    return int(total or 0)


def sorteos(db: Session, rifa: Rifa) -> list[Sorteo]:
    """Premios de la rifa en orden de fecha, con resultados y acumulados de premios secos."""
    premios = sorted(rifa.premios, key=lambda p: (p.fecha, p.tipo == "mayor", p.orden))
    lista, acumulados = [], []
    for premio in premios:
        resultado = premio.resultado
        boleta = resultado.numero_boleta.boleta if resultado and resultado.numero_boleta else None
        lista.append(Sorteo(premio, resultado, boleta, list(acumulados) if premio.tipo == "seco" else []))
        if premio.tipo == "seco" and resultado:
            acumulados = acumulados + [premio] if resultado.estado == "acumulado" else []
    return lista


def registrar(
    db: Session, usuario: Usuario, rifa: Rifa, premio_id: int, resultado_loteria: str, ip: str | None
) -> Resultado:
    """Guarda el resultado de un premio, busca la boleta y aplica las reglas del organizador."""
    if rifa.estado not in ("en_venta", "cerrada", "sorteada"):
        raise ErrorNegocio("Solo se registran resultados de rifas publicadas.")
    vigencia.exigir_vigente(rifa)
    premio = db.get(Premio, premio_id)
    if premio is None or premio.rifa_id != rifa.id:
        raise ErrorNegocio("Ese premio no es de esta rifa.")
    if premio.resultado is not None:
        raise ErrorNegocio("Este premio ya tiene resultado. Bórrelo primero si necesita corregirlo.")

    digitos = "".join(c for c in resultado_loteria if c.isdigit())
    jugado = numero_jugado(rifa, digitos)
    numero = db.scalar(select(NumeroBoleta).where(NumeroBoleta.rifa_id == rifa.id, NumeroBoleta.numero == jugado))
    boleta = numero.boleta if numero else None
    estado, observacion = _decidir(db, rifa, premio, boleta)

    resultado = Resultado(
        premio_id=premio.id,
        numero_loteria=digitos[:10],
        numero_jugado=jugado,
        numero_boleta_id=numero.id if numero else None,
        estado=estado,
        registrado_por_id=usuario.id,
        observacion=observacion,
    )
    db.add(resultado)
    if premio.tipo == "mayor":
        rifa.estado = "sorteada"
    db.flush()
    auditoria.registrar(
        db,
        usuario,
        "resultados",
        resultado.id,
        "registrar",
        ip=ip,
        nuevo={"premio": premio.descripcion, "loteria": digitos, "jugado": jugado, "estado": estado},
    )
    db.commit()
    return resultado


def _decidir(db: Session, rifa: Rifa, premio: Premio, boleta: Boleta | None) -> tuple[str, str]:
    """Aplica las reglas que el organizador escogió al crear la rifa."""
    if boleta is None or boleta.estado != "vendida":
        if premio.tipo == "seco" and rifa.regla_seco_atrasado == "acumula":
            return "acumulado", "El número no se vendió; el premio se acumula para el siguiente premio seco."
        return "desierto", "El número que cayó no se vendió."

    if premio.tipo == "mayor":
        pagado = pagado_hasta(db, boleta.id, premio.fecha)
        if pagado >= int(rifa.valor_boleta):
            return "con_ganador", "La boleta está pagada completa."
        saldo = int(rifa.valor_boleta) - pagado
        if rifa.regla_mayor_sin_pagar == "paga_saldo":
            return "debe_saldo", f"Gana, pero debe pagar {pesos(saldo)} antes de recibir el premio."
        return "desierto", f"La boleta no estaba pagada completa (debía {pesos(saldo)}); el premio queda desierto."

    # Premio seco: debe estar al día con las cuotas vencidas hasta la fecha del sorteo
    debido = debido_hasta(rifa, premio.fecha)
    pagado = pagado_hasta(db, boleta.id, premio.fecha)
    if pagado >= debido:
        return "con_ganador", "La boleta estaba al día con sus cuotas."
    faltaba = pesos(debido - pagado)
    if rifa.regla_seco_atrasado == "acumula":
        return "acumulado", f"La boleta estaba atrasada (le faltaban {faltaba}); el premio se acumula."
    return "desierto", f"La boleta estaba atrasada (le faltaban {faltaba}); el premio queda desierto."


def borrar(db: Session, usuario: Usuario, rifa: Rifa, premio_id: int, ip: str | None) -> None:
    """Corrige un resultado mal digitado. No se puede si el premio ya se entregó."""
    vigencia.exigir_vigente(rifa)
    premio = db.get(Premio, premio_id)
    if premio is None or premio.rifa_id != rifa.id or premio.resultado is None:
        raise ErrorNegocio("Ese premio no tiene resultado.")
    if premio.resultado.premio_entregado_en:
        raise ErrorNegocio("El premio ya fue entregado; su resultado no se puede borrar.")
    anterior = {"loteria": premio.resultado.numero_loteria, "estado": premio.resultado.estado}
    db.delete(premio.resultado)
    if premio.tipo == "mayor":
        rifa.estado = "en_venta"
    auditoria.registrar(db, usuario, "resultados", premio.id, "borrar", ip=ip, anterior=anterior)
    db.commit()


def marcar_entregado(db: Session, usuario: Usuario, rifa: Rifa, premio_id: int, ip: str | None) -> None:
    """Registra la fecha de entrega del premio. Solo para ganadores al día o pagados."""
    vigencia.exigir_vigente(rifa)
    premio = db.get(Premio, premio_id)
    if premio is None or premio.rifa_id != rifa.id or premio.resultado is None:
        raise ErrorNegocio("Ese premio no tiene resultado.")
    if premio.resultado.estado != "con_ganador":
        raise ErrorNegocio("Solo se entrega el premio a un ganador con su boleta al día o pagada.")
    premio.resultado.premio_entregado_en = datetime.now(timezone.utc)
    auditoria.registrar(db, usuario, "resultados", premio.resultado.id, "entregar", ip=ip)
    db.commit()


def whatsapp_ganador(sorteo: Sorteo) -> str | None:
    """Enlace de WhatsApp con el mensaje de felicitación listo para el ganador."""
    cliente = sorteo.ganador
    if cliente is None or not cliente.acepta_whatsapp:
        return None
    rifa, r = sorteo.premio.rifa, sorteo.resultado
    texto = (
        f"¡Felicitaciones, {cliente.nombre.split()[0]}! Le escribe {rifa.organizador.nombre}.\n"
        f"Su boleta {sorteo.boleta.etiqueta} de la rifa *{rifa.nombre}* ganó: *{sorteo.premio.descripcion}*.\n"
        f"Resultado de la {sorteo.premio.nombre_loteria} del {fecha_larga(sorteo.premio.fecha)}: {r.numero_loteria}"
        f" (juega el {r.numero_jugado}).\n"
    )
    if r.estado == "debe_saldo":
        texto += f"{r.observacion}\n"
    texto += f"Verifique su boleta en {obtener_config().app_url}/verificar/{sorteo.boleta.codigo_verificacion}"
    return f"https://wa.me/{cliente.whatsapp.lstrip('+')}?text={quote(texto)}"


def premios_de_boleta(db: Session, boleta: Boleta) -> list[Resultado]:
    """Resultados en los que esta boleta resultó ganadora (para la verificación pública)."""
    ids = select(NumeroBoleta.id).where(NumeroBoleta.boleta_id == boleta.id)
    return list(
        db.scalars(
            select(Resultado).where(
                Resultado.numero_boleta_id.in_(ids), Resultado.estado.in_(("con_ganador", "debe_saldo"))
            )
        )
    )
