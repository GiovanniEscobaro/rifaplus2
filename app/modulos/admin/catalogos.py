"""Lo que el superadministrador puede cambiar sin tocar el código: planes y precios, loterías y el valor del cobro
de una rifa en particular (descuento o cortesía). Todo queda en la auditoría.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.excepciones import ErrorNegocio
from app.core.plantillas import pesos
from app.modulos.acceso.modelos import Usuario
from app.modulos.auditoria import servicio as auditoria
from app.modulos.pagos.modelos import CobroRifa, Duracion, Plan, PrecioRifa
from app.modulos.rifas.modelos import Loteria, Rifa


# ---------- Precios por tipo de rifa ----------
def tipos_de_rifa(db: Session) -> list[Plan]:
    """Los 13 tipos de rifa con su precio (un plan exacto por cada combinación de boletas y cifras por boleta)."""
    return list(
        db.scalars(
            select(Plan)
            .where(Plan.boletas_min == Plan.boletas_max, Plan.numeros_min == Plan.numeros_max)
            .order_by(Plan.boletas_min)
        )
    )


def guardar_precios(
    db: Session, admin: Usuario, precios: dict[tuple[int, int], int], activos: set[int], ip: str | None
) -> None:
    """Guarda la tabla completa: precio de cada tipo de rifa por cada duración, y qué tipos se ofrecen.

    El precio de la duración más corta también queda en el plan (es el que se muestra como «desde»).
    """
    tipos = tipos_de_rifa(db)
    duraciones = list(db.scalars(select(Duracion).order_by(Duracion.meses)))
    actuales = {(p.plan_id, p.duracion_id): p for p in db.scalars(select(PrecioRifa))}
    for (plan_id, duracion_id), valor in precios.items():
        if valor < 0:
            raise ErrorNegocio("Los precios no pueden ser negativos.")
        fila = actuales.get((plan_id, duracion_id))
        if fila is None:
            db.add(PrecioRifa(plan_id=plan_id, duracion_id=duracion_id, valor=valor))
        elif int(fila.valor) != valor:
            fila.valor = valor
    db.flush()
    for plan in tipos:
        plan.activo = plan.id in activos
        primero = next(
            (precios.get((plan.id, d.id)) for d in duraciones if d.activa and (plan.id, d.id) in precios), None
        )
        if primero is not None:
            plan.valor = primero
    auditoria.registrar(
        db, admin, "precios_rifa", 0, "guardar_tabla", ip=ip, nuevo={"precios": len(precios), "activos": len(activos)}
    )
    db.commit()


def crear_tipo(db: Session, admin: Usuario, boletas: int, cifras: int, ip: str | None) -> Plan:
    """Agrega un tipo de rifa nuevo. Boletas × cifras debe dar 10, 100, 1.000 o 10.000 números del sorteo."""
    from app.core.semillas import nombre_tipo

    if not 1 <= cifras <= 10:
        raise ErrorNegocio("Las cifras por boleta deben ir de 1 a 10.")
    if boletas * cifras not in (10, 100, 1000, 10000):
        raise ErrorNegocio(
            f"{boletas:,} boletas de {cifras} cifras dan {boletas * cifras:,} números, y el sorteo necesita "
            "exactamente 10, 100, 1.000 o 10.000 para que siempre haya ganador.".replace(",", ".")
        )
    if any(t.boletas_min == boletas and t.numeros_min == cifras for t in tipos_de_rifa(db)):
        raise ErrorNegocio("Ese tipo de rifa ya existe.")
    if any(t.boletas_min == boletas for t in tipos_de_rifa(db) if t.activo):
        raise ErrorNegocio(f"Ya hay un tipo de rifa activo de {boletas:,} boletas.".replace(",", "."))
    plan = Plan(
        nombre=nombre_tipo(boletas, cifras),
        boletas_min=boletas,
        boletas_max=boletas,
        numeros_min=cifras,
        numeros_max=cifras,
        valor=0,
        activo=False,
    )
    db.add(plan)
    db.flush()
    db.add_all(PrecioRifa(plan_id=plan.id, duracion_id=d.id, valor=0) for d in db.scalars(select(Duracion)))
    auditoria.registrar(db, admin, "planes", plan.id, "crear_tipo", ip=ip, nuevo={"nombre": plan.nombre})
    db.commit()
    return plan


# ---------- Duraciones (6 meses, 1 año…) ----------
def duraciones(db: Session) -> list[Duracion]:
    """Todas las duraciones, de la más corta a la más larga."""
    return list(db.scalars(select(Duracion).order_by(Duracion.meses)))


def guardar_duracion(
    db: Session, admin: Usuario, duracion: Duracion | None, nombre: str, meses: int, activa: bool, ip: str | None
) -> None:
    """Crea o cambia una duración. Una duración nueva arranca con precios en 0 para que usted los ponga."""
    nombre = " ".join(nombre.split())
    if len(nombre) < 3:
        raise ErrorNegocio("Escriba el nombre de la duración, por ejemplo «6 meses».")
    if not 1 <= meses <= 36:
        raise ErrorNegocio("La duración debe ser de 1 a 36 meses.")
    repetida = db.scalar(select(Duracion).where(Duracion.meses == meses))
    if repetida is not None and repetida is not duracion:
        raise ErrorNegocio(f"Ya existe una duración de {meses} meses.")
    nueva = duracion is None
    if nueva:
        duracion = Duracion(nombre=nombre, meses=meses)
        db.add(duracion)
    duracion.nombre, duracion.meses, duracion.activa = nombre, meses, activa
    db.flush()
    if nueva:
        db.add_all(PrecioRifa(plan_id=t.id, duracion_id=duracion.id, valor=0) for t in tipos_de_rifa(db))
    auditoria.registrar(
        db,
        admin,
        "duraciones",
        duracion.id,
        "crear" if nueva else "editar",
        ip=ip,
        nuevo={"nombre": nombre, "meses": meses, "activa": activa},
    )
    db.commit()


# ---------- Loterías ----------
def loterias(db: Session) -> list[Loteria]:
    """Todas las loterías, en orden alfabético."""
    return list(db.scalars(select(Loteria).order_by(Loteria.nombre)))


def guardar_loteria(
    db: Session, admin: Usuario, loteria: Loteria | None, nombre: str, dias: str, activa: bool, ip: str | None
) -> None:
    """Agrega una lotería o cambia su nombre, sus días de sorteo o si está activa."""
    nombre = " ".join(nombre.split())
    if len(nombre) < 5:
        raise ErrorNegocio("Escriba el nombre completo de la lotería.")
    repetida = db.scalar(select(Loteria).where(Loteria.nombre.ilike(nombre)))
    if repetida is not None and repetida is not loteria:
        raise ErrorNegocio("Ya existe una lotería con ese nombre.")
    nueva = loteria is None
    if nueva:
        loteria = Loteria(nombre=nombre)
        db.add(loteria)
    loteria.nombre, loteria.dias_sorteo, loteria.activa = nombre, (dias or "").strip()[:50] or None, activa
    db.flush()
    auditoria.registrar(
        db,
        admin,
        "loterias",
        loteria.id,
        "crear" if nueva else "editar",
        ip=ip,
        nuevo={"nombre": nombre, "activa": activa},
    )
    db.commit()


# ---------- Valor del cobro de una rifa ----------
def ajustar_cobro(db: Session, admin: Usuario, rifa: Rifa, valor: int, motivo: str, ip: str | None) -> None:
    """Cambia lo que paga una rifa (descuento o cortesía). Con $0 queda aprobada y el organizador puede publicar."""
    cobro = db.scalar(select(CobroRifa).where(CobroRifa.rifa_id == rifa.id))
    if cobro is None or cobro.estado == "aprobado":
        raise ErrorNegocio("El cobro de esta rifa ya está aprobado; no se puede cambiar su valor.")
    if valor < 0:
        raise ErrorNegocio("El valor no puede ser negativo.")
    motivo = " ".join((motivo or "").split())
    if len(motivo) < 3:
        raise ErrorNegocio("Escriba el motivo del cambio (por ejemplo: descuento de lanzamiento).")
    anterior = int(cobro.valor)
    cobro.valor = valor
    if valor == 0:
        cobro.estado, cobro.revisado_por_id, cobro.motivo_rechazo = "aprobado", admin.id, None
    auditoria.registrar(
        db,
        admin,
        "cobros_rifa",
        cobro.id,
        "ajustar_valor",
        ip=ip,
        anterior={"valor": anterior},
        nuevo={"valor": valor, "motivo": motivo, "texto": f"{pesos(anterior)} → {pesos(valor)}"},
    )
    db.commit()
