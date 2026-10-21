"""Datos iniciales: loterías, medios de pago y planes. Se pueden cargar varias veces sin duplicar."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modulos.pagos.modelos import MedioPago, Plan
from app.modulos.rifas.modelos import Loteria

LOTERIAS = [
    "Lotería de Bogotá",
    "Lotería de Boyacá",
    "Lotería de Cundinamarca",
    "Lotería de Manizales",
    "Lotería de Medellín",
    "Lotería de Risaralda",
    "Lotería de Santander",
    "Lotería del Cauca",
    "Lotería del Huila",
    "Lotería del Meta",
    "Lotería del Quindío",
    "Lotería del Tolima",
    "Lotería del Valle",
    "Lotería de la Cruz Roja",
]

# codigo, nombre, activo, orden, para compradores, para pagar a RifaPlus
MEDIOS_PAGO = [
    ("bre_b", "Llave Bre-B", True, 0, True, True),
    ("nequi", "Nequi", True, 1, True, True),
    ("daviplata", "Daviplata", True, 2, True, True),
    ("efectivo", "Efectivo", True, 3, True, False),
    ("transferencia", "Transferencia bancaria", True, 4, True, False),
    ("tarjeta_credito", "Tarjeta de crédito", False, 5, True, False),
    ("tarjeta_debito", "Tarjeta débito", False, 6, True, False),
]

# nombre, boletas mínimas, boletas máximas, valor por rifa, números por boleta (mínimo, máximo)
# Un precio por cada tipo de rifa: (boletas que vende, cifras por boleta, valor). Los números del sorteo salen solos:
# boletas × cifras = 10, 100, 1.000 o 10.000 números (del 0 al 9, del 00 al 99, del 000 al 999 o del 0000 al 9999).
TIPOS_DE_RIFA = [
    (5, 2, 0),
    (10, 1, 0),
    (25, 4, 6_000),
    (50, 2, 19_900),
    (100, 1, 19_900),
    (250, 4, 59_900),
    (500, 2, 59_900),
    (1_000, 1, 89_900),
    (1_250, 8, 149_900),
    (2_000, 5, 149_900),
    (2_500, 4, 149_900),
    (5_000, 2, 299_900),
    (10_000, 1, 299_900),
]


def nombre_tipo(boletas: int, cifras: int) -> str:
    """Nombre de un tipo de rifa: '25 boletas de 4 cifras'."""
    return f"{boletas:,} boletas de {cifras} cifra{'s' if cifras > 1 else ''}".replace(",", ".")


DURACIONES = [("6 meses", 6), ("1 año", 12)]


def precio_inicial(valor_6_meses: int, meses: int) -> int:
    """Precio inicial por duración: el de 6 meses tal cual; cada 6 meses más suma la mitad (1 año = 1,5 veces)."""
    if valor_6_meses == 0 or meses == 6:
        return valor_6_meses
    factor = 1 + (meses - 6) / 12
    return max(int(round(valor_6_meses * factor / 1000) * 1000) - 100, 0)


def crear_precios_faltantes(db) -> int:
    """Crea las duraciones iniciales si no hay ninguna y el precio que falte de cada tipo de rifa por cada duración."""
    from app.modulos.pagos.modelos import Duracion, PrecioRifa

    if not db.scalar(select(Duracion.id).limit(1)):
        db.add_all(Duracion(nombre=n, meses=m) for n, m in DURACIONES)
        db.flush()
    existentes = {(p.plan_id, p.duracion_id) for p in db.scalars(select(PrecioRifa))}
    nuevos = []
    for plan in db.scalars(select(Plan).where(Plan.boletas_min == Plan.boletas_max)):
        for duracion in db.scalars(select(Duracion)):
            if (plan.id, duracion.id) not in existentes:
                nuevos.append(
                    PrecioRifa(
                        plan_id=plan.id, duracion_id=duracion.id, valor=precio_inicial(int(plan.valor), duracion.meses)
                    )
                )
    db.add_all(nuevos)
    db.flush()
    return len(nuevos)


def crear_tipos_faltantes(db) -> int:
    """Crea los tipos de rifa que falten, con su precio inicial. No toca los que ya están. Devuelve cuántos creó."""
    existentes = {
        (b, c)
        for b, c in db.execute(
            select(Plan.boletas_min, Plan.numeros_min).where(
                Plan.boletas_min == Plan.boletas_max, Plan.numeros_min == Plan.numeros_max
            )
        ).all()
    }
    nuevos = [
        Plan(nombre=nombre_tipo(b, c), boletas_min=b, boletas_max=b, valor=v, numeros_min=c, numeros_max=c)
        for b, c, v in TIPOS_DE_RIFA
        if (b, c) not in existentes
    ]
    db.add_all(nuevos)
    db.flush()
    crear_precios_faltantes(db)
    return len(nuevos)


def cargar(db: Session) -> None:
    """Inserta loterías, medios de pago y planes que falten. Se puede ejecutar varias veces sin duplicar."""
    existentes = set(db.scalars(select(Loteria.nombre)))
    db.add_all(Loteria(nombre=n) for n in LOTERIAS if n not in existentes)
    existentes = set(db.scalars(select(MedioPago.codigo)))
    db.add_all(
        MedioPago(
            codigo=c,
            nombre=n,
            activo=a,
            orden=o,
            requiere_comprobante=c != "efectivo",
            para_compradores=pc,
            para_rifaplus=pr,
        )
        for c, n, a, o, pc, pr in MEDIOS_PAGO
        if c not in existentes
    )
    crear_tipos_faltantes(db)
    db.commit()
