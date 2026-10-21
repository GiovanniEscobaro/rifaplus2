"""Plan de cuotas de la boleta: lo define el organizador y con él se sabe quién está al día."""

from dataclasses import dataclass
from datetime import date, timedelta

from app.core.excepciones import ErrorNegocio
from app.core.plantillas import fecha_larga, pesos
from app.modulos.rifas.modelos import Rifa

MAX_CUOTAS = 12


@dataclass
class EstadoCuota:
    """Una cuota del plan con lo que se debe llevar pagado al terminarla, si está pagada y si venció."""

    numero: int
    valor: int
    fecha_limite: date
    acumulado: int  # lo que debe llevar pagado al terminar esta cuota
    pagada: bool
    vencida: bool


@dataclass
class EstadoPlan:
    """Plan de cuotas de una boleta en una fecha: sus cuotas y lo que ya debería estar pagado."""

    cuotas: list[EstadoCuota]
    debido_hoy: int

    @property
    def proxima(self) -> EstadoCuota | None:
        """Primera cuota que todavía no está cubierta, o None si la boleta está pagada."""
        return next((c for c in self.cuotas if not c.pagada), None)

    @property
    def atrasada(self) -> bool:
        """True si alguna cuota ya venció y no está cubierta."""
        return any(c.vencida and not c.pagada for c in self.cuotas)


def validar_plan(
    cuotas: list[tuple[int, date]], valor_boleta: int, fecha_sorteo: date, hoy: date | None = None
) -> None:
    """Revisa que las cuotas sumen el valor de la boleta, vayan en orden y venzan a tiempo."""
    hoy = hoy or date.today()
    if not cuotas:
        raise ErrorNegocio("Defina al menos una cuota.")
    if len(cuotas) > MAX_CUOTAS:
        raise ErrorNegocio(f"Máximo {MAX_CUOTAS} cuotas.")
    total = sum(v for v, _ in cuotas)
    if total != valor_boleta:
        raise ErrorNegocio(
            f"Las cuotas suman {pesos(total)} y la boleta vale {pesos(valor_boleta)}: deben ser iguales."
        )
    anterior = None
    for i, (valor, fecha) in enumerate(cuotas, start=1):
        if valor <= 0:
            raise ErrorNegocio(f"La cuota {i} debe ser mayor que cero.")
        if fecha < hoy:
            raise ErrorNegocio(f"La fecha de la cuota {i} ya pasó.")
        if anterior and fecha <= anterior:
            raise ErrorNegocio(f"La cuota {i} debe vencer después de la cuota {i - 1}.")
        anterior = fecha
    if anterior > fecha_sorteo:
        raise ErrorNegocio(f"La última cuota debe vencer a más tardar el día del sorteo ({fecha_larga(fecha_sorteo)}).")


def _plan(rifa: Rifa) -> list[tuple[int, date]]:
    """Cuotas de la rifa como (valor, fecha). Sin cuotas guardadas, una sola cuota hasta el sorteo."""
    if rifa.cuotas:
        return [(int(c.valor), c.fecha_limite) for c in rifa.cuotas]
    return [(int(rifa.valor_boleta), rifa.fecha_sorteo)]  # rifas sin plan: pago único hasta el sorteo


def debido_hasta(rifa: Rifa, fecha: date) -> int:
    """Lo que una boleta debe llevar pagado al terminar ese día."""
    return sum(valor for valor, limite in _plan(rifa) if limite <= fecha)


def estado_plan(rifa: Rifa, pagado: int, hoy: date | None = None) -> EstadoPlan:
    """Estado de cada cuota de una boleta según lo que lleva pagado."""
    hoy = hoy or date.today()
    acumulado, cuotas = 0, []
    for i, (valor, limite) in enumerate(_plan(rifa), start=1):
        acumulado += valor
        cuotas.append(EstadoCuota(i, valor, limite, acumulado, pagado >= acumulado, limite < hoy))
    return EstadoPlan(cuotas, debido_hasta(rifa, hoy - timedelta(days=1)))
