"""Venta de boletas: comprador, abonos acreditados por el organizador, saldos y aviso por WhatsApp."""

from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import quote

from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import obtener_config
from app.core.excepciones import ErrorNegocio
from app.core.plantillas import fecha_larga, pesos
from app.modulos.acceso.modelos import Usuario
from app.modulos.auditoria import servicio as auditoria
from app.modulos.pagos.modelos import EntregaVendedor, MedioPago, Pago, PagoComision
from app.modulos.personas.modelos import Cliente, Vendedor
from app.modulos.rifas import vigencia
from app.modulos.rifas.cuotas import estado_plan
from app.modulos.rifas.modelos import Boleta, Rifa
from app.modulos.ventas.esquemas import Comprador, DatosPago, VendedorCrear


def _ahora() -> datetime:
    """Fecha y hora actual en UTC."""
    return datetime.now(timezone.utc)


@dataclass
class Saldo:
    """Lo que vale una boleta y lo que lleva pagado; de ahí salen lo pendiente y el estado."""

    valor: int
    pagado: int

    @property
    def pendiente(self) -> int:
        """Lo que falta por pagar (nunca negativo)."""
        return max(self.valor - self.pagado, 0)

    @property
    def estado(self) -> str:
        """'debe' sin pagos, 'abonada' con pagos parciales, 'pagada' completa."""
        if self.pagado <= 0:
            return "debe"
        return "pagada" if self.pagado >= self.valor else "abonada"


@dataclass
class ResumenVentas:
    """Cifras de venta de una rifa: vendidas, pagadas, con saldo, recaudado y por cobrar."""

    vendidas: int
    pagadas: int
    con_saldo: int
    recaudado: int
    por_cobrar: int


# ---------- Consultas ----------
def medios_para_compradores(db: Session) -> list[MedioPago]:
    """Medios de pago activos para los pagos de compradores."""
    return list(
        db.scalars(
            select(MedioPago)
            .where(MedioPago.activo.is_(True), MedioPago.para_compradores.is_(True))
            .order_by(MedioPago.orden)
        )
    )


def pagado_por_boleta(db: Session, boleta_ids: list[int]) -> dict[int, int]:
    """Total pagado (pagos aprobados) de cada boleta de la lista: {boleta_id: total}."""
    if not boleta_ids:
        return {}
    filas = db.execute(
        select(Pago.boleta_id, func.sum(Pago.monto))
        .where(Pago.boleta_id.in_(boleta_ids), Pago.estado == "aprobado")
        .group_by(Pago.boleta_id)
    ).all()
    return {boleta_id: int(total) for boleta_id, total in filas}


def saldo(db: Session, boleta: Boleta) -> Saldo:
    """Saldo de una boleta: valor y lo pagado."""
    return Saldo(int(boleta.rifa.valor_boleta), pagado_por_boleta(db, [boleta.id]).get(boleta.id, 0))


def pagos_de(db: Session, boleta: Boleta) -> list[Pago]:
    """Pagos de una boleta, del más reciente al más antiguo."""
    return list(db.scalars(select(Pago).where(Pago.boleta_id == boleta.id).order_by(Pago.fecha_pago.desc())))


def resumen(db: Session, rifa: Rifa) -> ResumenVentas:
    """Cifras de venta de la rifa calculadas en la base de datos con una sola consulta."""
    pagado = (
        select(Pago.boleta_id, func.sum(Pago.monto).label("total"))
        .where(Pago.estado == "aprobado")
        .group_by(Pago.boleta_id)
        .subquery()
    )
    total = func.coalesce(pagado.c.total, 0)
    valor = int(rifa.valor_boleta)
    fila = db.execute(
        select(
            func.count(),
            func.count().filter(total >= valor),
            func.coalesce(func.sum(total), 0),
            func.coalesce(func.sum(case((total < valor, valor - total), else_=0)), 0),
        )
        .select_from(Boleta)
        .outerjoin(pagado, pagado.c.boleta_id == Boleta.id)
        .where(Boleta.rifa_id == rifa.id, Boleta.estado == "vendida")
    ).one()
    vendidas, pagadas, recaudado, por_cobrar = fila
    return ResumenVentas(vendidas, pagadas, vendidas - pagadas, int(recaudado), int(por_cobrar))


def boleta_de_rifa(db: Session, rifa: Rifa, boleta_id: int, bloquear: bool = False) -> Boleta | None:
    """Boleta de esa rifa. Con bloquear=True la reserva (SELECT … FOR UPDATE) para que nadie la venda a la vez."""
    consulta = select(Boleta).where(Boleta.id == boleta_id, Boleta.rifa_id == rifa.id)
    if bloquear:
        consulta = consulta.with_for_update()
    return db.scalar(consulta)


def cliente_por_documento(db: Session, organizador_id: int, numero_documento: str) -> Cliente | None:
    """Comprador del organizador con ese documento, o None."""
    numero = "".join(c for c in numero_documento if c.isalnum()).upper()
    return db.scalar(
        select(Cliente).where(Cliente.organizador_id == organizador_id, Cliente.numero_documento == numero)
    )


# ---------- Compradores ----------
@dataclass
class CompraDe:
    """Una boleta de un comprador con su saldo, para la búsqueda de compradores."""

    boleta: Boleta
    saldo: Saldo


def buscar_compradores(db: Session, organizador_id: int, texto: str) -> list[tuple[Cliente, list[CompraDe]]]:
    """Busca por cédula (completa o el comienzo) o por nombre, y trae las boletas de cada comprador."""
    texto = " ".join(texto.split())
    if len(texto) < 2:
        return []
    documento = "".join(c for c in texto if c.isalnum()).upper()
    condicion = Cliente.nombre.ilike(f"%{texto}%")
    if documento and any(c.isdigit() for c in documento):
        condicion = Cliente.numero_documento.startswith(documento) | condicion
    clientes = list(
        db.scalars(
            select(Cliente)
            .where(Cliente.organizador_id == organizador_id, condicion)
            .order_by(Cliente.nombre)
            .limit(50)
        )
    )
    if not clientes:
        return []
    boletas = list(
        db.scalars(
            select(Boleta).where(Boleta.cliente_id.in_([c.id for c in clientes])).order_by(Boleta.fecha_venta.desc())
        )
    )
    pagado = pagado_por_boleta(db, [b.id for b in boletas])
    por_cliente: dict[int, list[CompraDe]] = {c.id: [] for c in clientes}
    for b in boletas:
        por_cliente[b.cliente_id].append(CompraDe(b, Saldo(int(b.rifa.valor_boleta), pagado.get(b.id, 0))))
    return [(c, por_cliente[c.id]) for c in clientes]


# ---------- Liquidación de vendedores ----------
@dataclass
class LineaLiquidacion:
    """Lo que un vendedor lleva en una rifa: boletas vendidas, dinero recaudado y comisión ganada."""

    rifa: Rifa
    vendidas: int
    recaudado: int
    comision: int


@dataclass
class Liquidacion:
    """Cuenta de un vendedor: comisión ganada en todas sus rifas, lo que ya se le pagó y lo que falta."""

    vendedor: Vendedor
    lineas: list[LineaLiquidacion]
    pagado: int

    @property
    def comision(self) -> int:
        """Comisión ganada en total."""
        return sum(linea.comision for linea in self.lineas)

    @property
    def recaudado(self) -> int:
        """Dinero recaudado en total por las boletas que vendió."""
        return sum(linea.recaudado for linea in self.lineas)

    @property
    def saldo(self) -> int:
        """Lo que falta por pagarle. Cuando llega a cero, el vendedor está a paz y salvo."""
        return max(self.comision - self.pagado, 0)


def _comision(valor: int, porcentaje) -> int:
    """Comisión en pesos enteros, redondeada al peso más cercano."""
    return int(round(valor * float(porcentaje or 0) / 100))


def liquidacion(db: Session, vendedor: Vendedor) -> Liquidacion:
    """Calcula por rifa lo recaudado en las boletas del vendedor (pagos aprobados) y su comisión.

    La comisión se calcula con el porcentaje actual del vendedor.
    """
    filas = db.execute(
        select(Rifa, func.count(func.distinct(Boleta.id)), func.coalesce(func.sum(Pago.monto), 0))
        .join(Boleta, Boleta.rifa_id == Rifa.id)
        .outerjoin(Pago, (Pago.boleta_id == Boleta.id) & (Pago.estado == "aprobado"))
        .where(Boleta.vendedor_id == vendedor.id, Boleta.estado == "vendida")
        .group_by(Rifa.id)
        .order_by(Rifa.fecha_creacion.desc())
    ).all()
    lineas = [LineaLiquidacion(r, int(n), int(t), _comision(int(t), vendedor.comision_porcentaje)) for r, n, t in filas]
    pagado = db.scalar(
        select(func.coalesce(func.sum(PagoComision.monto), 0)).where(PagoComision.vendedor_id == vendedor.id)
    )
    return Liquidacion(vendedor, lineas, int(pagado or 0))


def pagos_comision_de(db: Session, vendedor: Vendedor) -> list[PagoComision]:
    """Pagos de comisión hechos al vendedor, del más reciente al más antiguo."""
    return list(
        db.scalars(
            select(PagoComision).where(PagoComision.vendedor_id == vendedor.id).order_by(PagoComision.fecha.desc())
        )
    )


def vendedor_del_organizador(db: Session, organizador_id: int, vendedor_id: int) -> Vendedor | None:
    """El vendedor solo si es de este organizador."""
    vendedor = db.get(Vendedor, vendedor_id)
    return vendedor if vendedor and vendedor.organizador_id == organizador_id else None


def pagar_comision(
    db: Session, usuario: Usuario, vendedor: Vendedor, pago: DatosPago, observacion: str | None, ip: str | None
) -> PagoComision:
    """Registra un pago de comisión al vendedor. No deja pagar más de lo que se le debe."""
    medio = db.get(MedioPago, pago.medio_pago_id)
    if medio is None or not medio.activo:
        raise ErrorNegocio("Escoja cómo le pagó al vendedor.")
    saldo_actual = liquidacion(db, vendedor).saldo
    if saldo_actual <= 0:
        raise ErrorNegocio("Este vendedor no tiene comisión pendiente por pagar.")
    if pago.monto > saldo_actual:
        raise ErrorNegocio(f"El pago de {pesos(pago.monto)} supera lo que se le debe ({pesos(saldo_actual)}).")
    nuevo = PagoComision(
        vendedor_id=vendedor.id,
        monto=pago.monto,
        medio_pago_id=medio.id,
        referencia=pago.referencia,
        observacion=(observacion or "").strip()[:300] or None,
        registrado_por_id=usuario.id,
    )
    db.add(nuevo)
    db.flush()
    auditoria.registrar(
        db,
        usuario,
        "pagos_comision",
        nuevo.id,
        "registrar",
        ip=ip,
        nuevo={"vendedor": vendedor.nombre, "monto": pago.monto},
    )
    db.commit()
    return nuevo


def actualizar_vendedor(
    db: Session,
    usuario: Usuario,
    vendedor: Vendedor,
    comision: float,
    activo: bool,
    ip: str | None,
    llave_bre_b: str | None = None,
) -> None:
    """Cambia la comisión, la llave Bre-B o activa / desactiva al vendedor."""
    if not 0 <= comision <= 100:
        raise ErrorNegocio("La comisión debe estar entre 0 % y 100 %.")
    anterior = {"comision": float(vendedor.comision_porcentaje or 0), "activo": vendedor.activo}
    vendedor.comision_porcentaje = comision
    vendedor.activo = activo
    if llave_bre_b is not None:
        llave = " ".join(llave_bre_b.split())
        if len(llave) < 3:
            raise ErrorNegocio("Escriba la llave Bre-B del vendedor para poder pagarle su comisión.")
        vendedor.llave_bre_b = llave[:60]
    auditoria.registrar(
        db,
        usuario,
        "vendedores",
        vendedor.id,
        "editar",
        ip=ip,
        anterior=anterior,
        nuevo={"comision": comision, "activo": activo},
    )
    db.commit()


# ---------- Efectivo que cobran los vendedores y entregan al organizador ----------
@dataclass
class EfectivoRifa:
    """Por rifa: efectivo que cobró el vendedor, lo que ya entregó y lo que le falta entregar."""

    rifa: Rifa
    cobrado: int
    entregado: int

    @property
    def por_entregar(self) -> int:
        """Efectivo que el vendedor todavía tiene en su poder."""
        return max(self.cobrado - self.entregado, 0)


def efectivo_del_vendedor(db: Session, vendedor: Vendedor) -> list[EfectivoRifa]:
    """Pagos en efectivo de las boletas del vendedor (los cobra él) frente a lo que ya le entregó al organizador.

    Los pagos por llave Bre-B, Nequi, Daviplata o transferencia llegan directo a la cuenta del organizador, por eso
    solo el efectivo queda en manos del vendedor.
    """
    efectivo = db.scalar(select(MedioPago.id).where(MedioPago.codigo == "efectivo"))
    cobrado = dict(
        db.execute(
            select(Boleta.rifa_id, func.coalesce(func.sum(Pago.monto), 0))
            .join(Pago, Pago.boleta_id == Boleta.id)
            .where(Boleta.vendedor_id == vendedor.id, Pago.estado == "aprobado", Pago.medio_pago_id == efectivo)
            .group_by(Boleta.rifa_id)
        ).all()
    )
    entregado = dict(
        db.execute(
            select(EntregaVendedor.rifa_id, func.sum(EntregaVendedor.monto))
            .where(EntregaVendedor.vendedor_id == vendedor.id)
            .group_by(EntregaVendedor.rifa_id)
        ).all()
    )
    rifas = {r.id: r for r in db.scalars(select(Rifa).where(Rifa.id.in_(set(cobrado) | set(entregado))))}
    return [
        EfectivoRifa(rifas[i], int(cobrado.get(i, 0)), int(entregado.get(i, 0)))
        for i in sorted(rifas, key=lambda i: rifas[i].fecha_creacion, reverse=True)
    ]


def entregas_de(db: Session, vendedor: Vendedor) -> list[EntregaVendedor]:
    """Entregas de dinero del vendedor, de la más reciente a la más antigua."""
    return list(
        db.scalars(
            select(EntregaVendedor)
            .where(EntregaVendedor.vendedor_id == vendedor.id)
            .order_by(EntregaVendedor.fecha.desc())
        )
    )


def registrar_entrega(
    db: Session,
    usuario: Usuario,
    vendedor: Vendedor,
    rifa_id: int,
    monto: int,
    medio_pago_id: int,
    observacion: str | None,
    ip: str | None,
) -> EntregaVendedor:
    """El organizador registra el dinero que le entregó el vendedor. No puede pasar de lo que el vendedor tiene."""
    linea = next((x for x in efectivo_del_vendedor(db, vendedor) if x.rifa.id == rifa_id), None)
    if linea is None or linea.rifa.organizador_id != usuario.organizador_id:
        raise ErrorNegocio("Escoja una rifa en la que el vendedor haya cobrado en efectivo.")
    if monto <= 0:
        raise ErrorNegocio("Escriba el valor que le entregó.")
    if monto > linea.por_entregar:
        raise ErrorNegocio(
            f"La entrega de {pesos(monto)} supera lo que el vendedor tiene por entregar en esa rifa "
            f"({pesos(linea.por_entregar)})."
        )
    medio = db.get(MedioPago, medio_pago_id)
    if medio is None or not medio.activo:
        raise ErrorNegocio("Escoja cómo le entregó el dinero.")
    entrega = EntregaVendedor(
        vendedor_id=vendedor.id,
        rifa_id=rifa_id,
        medio_pago_id=medio.id,
        monto=monto,
        recibido_por_id=usuario.id,
        observacion=(observacion or "").strip()[:300] or None,
    )
    db.add(entrega)
    db.flush()
    auditoria.registrar(
        db,
        usuario,
        "entregas_vendedor",
        entrega.id,
        "registrar",
        ip=ip,
        nuevo={"vendedor": vendedor.nombre, "rifa_id": rifa_id, "monto": monto},
    )
    db.commit()
    return entrega


# ---------- Vendedores ----------
def vendedores(db: Session, organizador_id: int, solo_activos: bool = True) -> list[Vendedor]:
    """Vendedores del organizador en orden alfabético."""
    consulta = select(Vendedor).where(Vendedor.organizador_id == organizador_id)
    if solo_activos:
        consulta = consulta.where(Vendedor.activo.is_(True))
    return list(db.scalars(consulta.order_by(Vendedor.nombre)))


def crear_vendedor(db: Session, usuario: Usuario, datos: VendedorCrear) -> Vendedor:
    """Crea el vendedor si su documento no está repetido."""
    if db.scalar(
        select(Vendedor.id).where(
            Vendedor.organizador_id == usuario.organizador_id, Vendedor.numero_documento == datos.numero_documento
        )
    ):
        raise ErrorNegocio("Ya tiene un vendedor con ese número de documento.")
    vendedor = Vendedor(organizador_id=usuario.organizador_id, **datos.model_dump())
    db.add(vendedor)
    db.flush()
    auditoria.registrar(db, usuario, "vendedores", vendedor.id, "crear", nuevo={"nombre": vendedor.nombre})
    db.commit()
    return vendedor


def ventas_por_vendedor(db: Session, organizador_id: int) -> dict[int, tuple[int, int]]:
    """vendedor_id -> (boletas vendidas, dinero cobrado)."""
    filas = db.execute(
        select(Boleta.vendedor_id, func.count(func.distinct(Boleta.id)), func.coalesce(func.sum(Pago.monto), 0))
        .join(Rifa, Rifa.id == Boleta.rifa_id)
        .outerjoin(Pago, (Pago.boleta_id == Boleta.id) & (Pago.estado == "aprobado"))
        .where(Rifa.organizador_id == organizador_id, Boleta.vendedor_id.is_not(None))
        .group_by(Boleta.vendedor_id)
    ).all()
    return {v: (int(n), int(total)) for v, n, total in filas}


# ---------- Ventas y pagos ----------
def _medio_valido(db: Session, medio_pago_id: int) -> MedioPago:
    """El medio de pago debe existir, estar activo y servir para compradores."""
    medio = db.get(MedioPago, medio_pago_id)
    if medio is None or not medio.activo or not medio.para_compradores:
        raise ErrorNegocio("Escoja cómo le pagaron: efectivo, Nequi, Daviplata o transferencia.")
    return medio


def _agregar_pago(
    db: Session, usuario: Usuario, boleta: Boleta, pago: DatosPago, comprobante: str | None, pendiente: int
) -> Pago:
    """Agrega un pago aprobado sin pasarse de lo que falta por pagar."""
    _medio_valido(db, pago.medio_pago_id)
    if pago.monto > pendiente:
        raise ErrorNegocio(f"El pago de {pesos(pago.monto)} supera lo que falta por pagar ({pesos(pendiente)}).")
    # El organizador acredita sus propios pagos: quedan aprobados de inmediato
    nuevo = Pago(
        boleta_id=boleta.id,
        medio_pago_id=pago.medio_pago_id,
        monto=pago.monto,
        referencia=pago.referencia,
        comprobante_url=comprobante,
        estado="aprobado",
        registrado_por_id=usuario.id,
        verificado_por_id=usuario.id,
        fecha_verificacion=_ahora(),
    )
    db.add(nuevo)
    return nuevo


def vender(
    db: Session,
    usuario: Usuario,
    rifa: Rifa,
    boleta_id: int,
    comprador: Comprador,
    vendedor_id: int | None,
    medio_difusion: str | None,
    pago: DatosPago | None,
    comprobante: str | None,
    ip: str | None,
) -> Boleta:
    """Asigna la boleta al comprador (lo crea o actualiza), la marca vendida y registra el pago inicial."""
    if rifa.estado != "en_venta":
        raise ErrorNegocio("Solo se pueden vender boletas de una rifa publicada.")
    vigencia.exigir_vigente(rifa)
    boleta = boleta_de_rifa(db, rifa, boleta_id, bloquear=True)  # evita que dos personas vendan la misma boleta
    if boleta is None or boleta.estado != "disponible":
        raise ErrorNegocio("Esta boleta ya no está disponible.")
    if vendedor_id is not None:
        vendedor = db.get(Vendedor, vendedor_id)
        if vendedor is None or vendedor.organizador_id != usuario.organizador_id:
            raise ErrorNegocio("Escoja un vendedor de su lista.")

    cliente = cliente_por_documento(db, usuario.organizador_id, comprador.numero_documento)
    if cliente is None:
        cliente = Cliente(organizador_id=usuario.organizador_id, **comprador.model_dump())
        db.add(cliente)
    else:  # comprador conocido: se actualizan sus datos de contacto
        for campo, valor in comprador.model_dump().items():
            setattr(cliente, campo, valor)
    db.flush()

    boleta.cliente_id = cliente.id
    boleta.vendedor_id = vendedor_id
    boleta.medio_difusion = medio_difusion or None
    boleta.estado = "vendida"
    boleta.fecha_venta = _ahora()
    if pago is not None:
        _agregar_pago(db, usuario, boleta, pago, comprobante, int(rifa.valor_boleta))
    auditoria.registrar(
        db,
        usuario,
        "boletas",
        boleta.id,
        "vender",
        ip=ip,
        nuevo={"cliente": cliente.nombre, "pago_inicial": pago.monto if pago else 0},
    )
    _confirmar(db)
    return boleta


def registrar_pago(
    db: Session, usuario: Usuario, rifa: Rifa, boleta_id: int, pago: DatosPago, comprobante: str | None, ip: str | None
) -> Pago:
    """Agrega un pago a una boleta vendida."""
    vigencia.exigir_vigente(rifa)
    boleta = boleta_de_rifa(db, rifa, boleta_id, bloquear=True)
    if boleta is None or boleta.estado != "vendida":
        raise ErrorNegocio("Solo se registran pagos de boletas vendidas.")
    nuevo = _agregar_pago(db, usuario, boleta, pago, comprobante, saldo(db, boleta).pendiente)
    _confirmar(db, solo_enviar=True)
    auditoria.registrar(
        db, usuario, "pagos", nuevo.id, "registrar", ip=ip, nuevo={"boleta": boleta.etiqueta, "monto": pago.monto}
    )
    _confirmar(db)
    return nuevo


def liberar(db: Session, usuario: Usuario, rifa: Rifa, boleta_id: int, ip: str | None) -> None:
    """Deshace una venta sin pagos (por ejemplo, el comprador se arrepintió antes de pagar)."""
    vigencia.exigir_vigente(rifa)
    boleta = boleta_de_rifa(db, rifa, boleta_id, bloquear=True)
    if boleta is None or boleta.estado != "vendida":
        raise ErrorNegocio("Esta boleta no está vendida.")
    if saldo(db, boleta).pagado > 0:
        raise ErrorNegocio("No se puede liberar una boleta que ya tiene pagos registrados.")
    anterior = {"cliente_id": boleta.cliente_id}
    boleta.cliente_id = None
    boleta.vendedor_id = None
    boleta.estado = "disponible"
    boleta.fecha_venta = None
    auditoria.registrar(db, usuario, "boletas", boleta.id, "liberar", ip=ip, anterior=anterior)
    db.commit()


def _confirmar(db: Session, solo_enviar: bool = False) -> None:
    """Guarda los cambios y traduce los choques de la base de datos a mensajes claros."""
    try:
        db.flush() if solo_enviar else db.commit()
    except IntegrityError as e:
        db.rollback()
        if "uq_pago_referencia" in str(e.orig):
            raise ErrorNegocio("Esa referencia de pago ya está registrada en otra boleta.") from e
        if "uq_cliente_documento" in str(e.orig):
            raise ErrorNegocio("Ya existe un comprador con ese documento.") from e
        raise


# ---------- Correo ----------
def enlace_correo(boleta: Boleta, estado: Saldo) -> str | None:
    """Enlace mailto: abre el correo del organizador con destinatario, asunto, mensaje y enlace a la boleta."""
    if boleta.cliente is None or not boleta.cliente.email:
        return None
    rifa = boleta.rifa
    numeros = ", ".join(n.numero for n in boleta.numeros)
    situacion = (
        "Su boleta está pagada."
        if estado.estado == "pagada"
        else (f"Ha pagado {pesos(estado.pagado)} y le faltan {pesos(estado.pendiente)}.")
    )
    asunto = f"Su boleta {boleta.etiqueta} de la rifa {rifa.nombre}"
    cuerpo = (
        f"Hola, {boleta.cliente.nombre.split()[0]}:\n\n"
        f"Gracias por participar en la rifa {rifa.nombre}.\n"
        f"Boleta {boleta.etiqueta} · {'Cifra' if len(boleta.numeros) == 1 else 'Cifras'}: {numeros}\n"
        f"Juega con la {rifa.loteria.nombre} el {fecha_larga(rifa.fecha_sorteo)}.\n"
        f"{situacion}\n\n"
        f"Vea su boleta aquí: {obtener_config().app_url}/boleta/{boleta.codigo_verificacion}\n\n"
        f"{rifa.organizador.nombre}"
    )
    return f"mailto:{boleta.cliente.email}?subject={quote(asunto)}&body={quote(cuerpo)}"


# ---------- WhatsApp ----------
def enlace_whatsapp(boleta: Boleta, estado: Saldo) -> str | None:
    """Abre WhatsApp con el mensaje listo para el comprador; el organizador solo toca enviar."""
    if boleta.cliente is None or not boleta.cliente.acepta_whatsapp:
        return None
    rifa = boleta.rifa
    numeros = ", ".join(n.numero for n in boleta.numeros)
    etiqueta_numeros = "Cifra" if len(boleta.numeros) == 1 else "Cifras"
    if estado.estado == "pagada":
        situacion = "Su boleta está *pagada*."
    else:
        situacion = f"Ha pagado {pesos(estado.pagado)} y le faltan *{pesos(estado.pendiente)}*."
        proxima = estado_plan(rifa, estado.pagado).proxima
        if proxima:
            falta_cuota = proxima.acumulado - estado.pagado
            situacion += f"\nPróximo pago: {pesos(falta_cuota)} a más tardar el {fecha_larga(proxima.fecha_limite)}."
    texto = (
        f"Hola, {boleta.cliente.nombre.split()[0]}. Le escribe {rifa.organizador.nombre}.\n"
        f"Rifa: *{rifa.nombre}*\n"
        f"Boleta {boleta.etiqueta} · {etiqueta_numeros}: *{numeros}*\n"
        f"Juega con la {rifa.loteria.nombre} el {fecha_larga(rifa.fecha_sorteo)}.\n"
        f"{situacion}\n"
        f"Vea su boleta aquí: {obtener_config().app_url}/boleta/{boleta.codigo_verificacion}"
    )
    telefono = boleta.cliente.whatsapp.lstrip("+")
    return f"https://wa.me/{telefono}?text={quote(texto)}"
