"""Casos de uso de las rifas: crear, consultar, buscar boletas y publicar."""

from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.excepciones import ErrorNegocio
from app.modulos.acceso.modelos import Usuario
from app.modulos.auditoria import servicio as auditoria
from app.modulos.legal import servicio as legal
from app.modulos.pagos.modelos import CobroRifa, Pago
from app.modulos.personas.modelos import Cliente
from app.modulos.rifas import vigencia
from app.modulos.rifas.cuotas import debido_hasta, validar_plan
from app.modulos.rifas.esquemas import RifaCrear
from app.modulos.rifas.generador import Opcion, buscar_opcion, generar_boletas, opciones_disponibles
from app.modulos.rifas.modelos import Boleta, Cuota, Loteria, NumeroBoleta, Premio, Rifa

BOLETAS_POR_PAGINA = 100


@dataclass
class DetalleRifa:
    """Todo lo que muestra la página de una rifa: boletas de la página, cobro, cifras y filtros."""

    rifa: Rifa
    boletas: list[Boleta]
    cobro: CobroRifa | None
    por_estado: dict[str, int]
    pagina: int
    paginas: int
    encontradas: int
    buscar: str
    pagado: dict = field(default_factory=dict)
    ventas: object = None
    filtro_estado: str = ""

    @property
    def pago_aprobado(self) -> bool:
        """True si el plan de la rifa ya está pagado y aprobado (o es gratis)."""
        return self.cobro is not None and self.cobro.estado == "aprobado"

    @property
    def estado_cobro(self) -> str:
        """gratis, sin_enviar, en_revision, aprobado o rechazado (ver pagos.servicio.estado_cobro)."""
        from app.modulos.pagos.servicio import estado_cobro

        return estado_cobro(self.cobro)

    @property
    def puede_publicarse(self) -> bool:
        """True si la rifa está en borrador y su plan está aprobado."""
        return self.rifa.estado == "borrador" and self.pago_aprobado


def loterias_activas(db: Session) -> list[Loteria]:
    """Loterías activas en orden alfabético."""
    return list(db.scalars(select(Loteria).where(Loteria.activa.is_(True)).order_by(Loteria.nombre)))


def opciones(db: Session) -> list[Opcion]:
    """Opciones de boletas que se pueden escoger hoy, según los planes."""
    return opciones_disponibles(db)


def crear_rifa(db: Session, usuario: Usuario, datos: RifaCrear, ip: str | None = None) -> Rifa:
    """Crea la rifa, su premio, todas las boletas, su cobro y la declaración, en una sola transacción."""
    opcion = buscar_opcion(db, datos.cifras, datos.numeros_por_boleta)
    duracion, valor_cobro = vigencia.precio(db, opcion.plan_id, datos.duracion_id)
    if db.get(Loteria, datos.loteria_id) is None:
        raise ErrorNegocio("Escoja una lotería de la lista.")
    if any(db.get(Loteria, p.loteria_id) is None for p in datos.premios_secos):
        raise ErrorNegocio("Escoja la lotería de cada premio seco.")
    plan = [(c.valor, c.fecha_limite) for c in datos.cuotas] or [(datos.valor_boleta, datos.fecha_sorteo)]
    validar_plan(plan, datos.valor_boleta, datos.fecha_sorteo)

    rifa = Rifa(
        organizador_id=usuario.organizador_id,
        loteria_id=datos.loteria_id,
        plan_id=opcion.plan_id,
        nombre=datos.nombre,
        descripcion=datos.descripcion,
        fecha_sorteo=datos.fecha_sorteo,
        cifras=opcion.cifras,
        total_numeros=opcion.total_numeros,
        series_por_boleta=opcion.numeros_por_boleta,
        total_boletas=opcion.boletas,
        valor_boleta=datos.valor_boleta,
        duracion_meses=duracion.meses,
        regla_seco_atrasado=datos.regla_seco_atrasado,
        regla_mayor_sin_pagar=datos.regla_mayor_sin_pagar,
        estado="borrador",
    )
    db.add(rifa)
    db.add(
        Premio(
            rifa=rifa,
            tipo="mayor",
            descripcion=datos.premio_mayor,
            valor_estimado=datos.valor_premio,
            orden=1,
            foto_url=datos.foto_mayor_url,
        )
    )
    for i, seco in enumerate(sorted(datos.premios_secos, key=lambda p: p.fecha_juego), start=2):
        db.add(
            Premio(
                rifa=rifa,
                tipo="seco",
                descripcion=seco.descripcion,
                loteria_id=seco.loteria_id,
                fecha_juego=seco.fecha_juego,
                valor_estimado=seco.valor_estimado,
                foto_url=seco.foto_url,
                orden=i,
            )
        )
    for i, (valor, fecha) in enumerate(plan, start=1):
        rifa.cuotas.append(Cuota(numero=i, valor=valor, fecha_limite=fecha))
    db.flush()
    generar_boletas(db, rifa)
    db.add(
        CobroRifa(
            rifa_id=rifa.id,
            plan_id=opcion.plan_id,
            valor=valor_cobro,
            estado="aprobado" if valor_cobro == 0 else "pendiente",
        )
    )
    legal.registrar(
        db,
        usuario_id=usuario.id,
        organizador_id=usuario.organizador_id,
        rifa_id=rifa.id,
        documento="declaracion_rifa",
        version=legal.VERSION_DECLARACION,
        ip=ip,
        texto=legal.TEXTO_DECLARACION_RIFA,
    )
    auditoria.registrar(
        db,
        usuario,
        "rifas",
        rifa.id,
        "crear",
        ip=ip,
        nuevo={
            "nombre": rifa.nombre,
            "boletas": rifa.total_boletas,
            "numeros_por_boleta": rifa.series_por_boleta,
            "plan": opcion.plan_nombre,
        },
    )
    db.commit()
    return rifa


# ---------- Edición ----------
def datos_para_formulario(rifa: Rifa) -> dict:
    """Llena el formulario de rifa con los datos guardados (para editarla en borrador)."""
    from app.core.plantillas import miles

    mayor = next((p for p in rifa.premios if p.tipo == "mayor"), None)
    datos = {
        "nombre": rifa.nombre,
        "descripcion": rifa.descripcion or "",
        "loteria_id": str(rifa.loteria_id),
        "fecha_sorteo": rifa.fecha_sorteo.isoformat(),
        "opcion": f"{rifa.cifras}-{rifa.series_por_boleta}",
        "valor_boleta": miles(rifa.valor_boleta),
        "premio_mayor": mayor.descripcion if mayor else "",
        "valor_premio": miles(mayor.valor_estimado) if mayor and mayor.valor_estimado else "",
        "regla_seco_atrasado": rifa.regla_seco_atrasado,
        "regla_mayor_sin_pagar": rifa.regla_mayor_sin_pagar,
        "foto_mayor_actual": mayor.foto_url if mayor and mayor.foto_url else "",
        "duracion_meses": str(rifa.duracion_meses),
    }
    for c in rifa.cuotas:
        datos[f"cuota_valor_{c.numero}"] = miles(c.valor)
        datos[f"cuota_fecha_{c.numero}"] = c.fecha_limite.isoformat()
    for i, p in enumerate(sorted((p for p in rifa.premios if p.tipo == "seco"), key=lambda p: p.orden), start=1):
        datos |= {
            f"seco_descripcion_{i}": p.descripcion,
            f"seco_loteria_id_{i}": str(p.loteria_id or ""),
            f"seco_fecha_juego_{i}": p.fecha_juego.isoformat() if p.fecha_juego else "",
            f"seco_valor_estimado_{i}": miles(p.valor_estimado) if p.valor_estimado else "",
            f"seco_foto_actual_{i}": p.foto_url or "",
        }
    return datos


def editar_borrador(db: Session, usuario: Usuario, rifa: Rifa, datos: RifaCrear, ip: str | None = None) -> None:
    """Cambia todo lo de una rifa en borrador. Si cambia la opción de boletas, las vuelve a generar."""
    if rifa.estado != "borrador":
        raise ErrorNegocio("Esta rifa ya está publicada; solo se pueden corregir algunos datos.")
    cobro_actual = db.scalar(select(CobroRifa).where(CobroRifa.rifa_id == rifa.id))
    if cobro_actual and cobro_actual.estado == "pendiente" and cobro_actual.fecha_pago:
        raise ErrorNegocio(
            "El pago de esta rifa está en revisión; podrá editarla cuando RifaPlus lo apruebe o rechace."
        )
    opcion = buscar_opcion(db, datos.cifras, datos.numeros_por_boleta)
    if db.get(Loteria, datos.loteria_id) is None or any(
        db.get(Loteria, p.loteria_id) is None for p in datos.premios_secos
    ):
        raise ErrorNegocio("Escoja una lotería de la lista.")
    plan = [(c.valor, c.fecha_limite) for c in datos.cuotas] or [(datos.valor_boleta, datos.fecha_sorteo)]
    validar_plan(plan, datos.valor_boleta, datos.fecha_sorteo)

    cobro = db.scalar(select(CobroRifa).where(CobroRifa.rifa_id == rifa.id))
    duracion, valor_cobro = vigencia.precio(db, opcion.plan_id, datos.duracion_id)
    cambia_plan = opcion.plan_id != rifa.plan_id or duracion.meses != rifa.duracion_meses
    if cambia_plan and cobro and cobro.estado == "aprobado" and int(cobro.valor) > 0:
        raise ErrorNegocio(
            "El plan de esta rifa ya fue pagado. Para pasar a una opción de otro plan, comuníquese con RifaPlus."
        )
    anterior = {
        "nombre": rifa.nombre,
        "opcion": f"{rifa.cifras}-{rifa.series_por_boleta}",
        "valor_boleta": int(rifa.valor_boleta),
        "fecha_sorteo": rifa.fecha_sorteo.isoformat(),
    }

    regenerar = (opcion.cifras, opcion.numeros_por_boleta) != (rifa.cifras, rifa.series_por_boleta)
    if regenerar:
        if db.scalar(
            select(func.count()).select_from(Boleta).where(Boleta.rifa_id == rifa.id, Boleta.estado != "disponible")
        ):
            raise ErrorNegocio("La rifa ya tiene boletas asignadas; no se puede cambiar la cantidad de boletas.")
        from sqlalchemy import delete

        db.execute(delete(NumeroBoleta).where(NumeroBoleta.rifa_id == rifa.id))
        db.execute(delete(Boleta).where(Boleta.rifa_id == rifa.id))

    rifa.nombre, rifa.descripcion = datos.nombre, datos.descripcion
    rifa.loteria_id, rifa.fecha_sorteo, rifa.valor_boleta = datos.loteria_id, datos.fecha_sorteo, datos.valor_boleta
    rifa.cifras, rifa.total_numeros, rifa.series_por_boleta = (
        opcion.cifras,
        opcion.total_numeros,
        opcion.numeros_por_boleta,
    )
    rifa.total_boletas, rifa.plan_id = opcion.boletas, opcion.plan_id
    rifa.regla_seco_atrasado, rifa.regla_mayor_sin_pagar = datos.regla_seco_atrasado, datos.regla_mayor_sin_pagar

    rifa.cuotas.clear()
    db.flush()
    for i, (valor, fecha) in enumerate(plan, start=1):
        rifa.cuotas.append(Cuota(numero=i, valor=valor, fecha_limite=fecha))
    mayor = next((p for p in rifa.premios if p.tipo == "mayor"), None)
    mayor.descripcion, mayor.valor_estimado = datos.premio_mayor, datos.valor_premio
    mayor.foto_url = datos.foto_mayor_url
    for seco in [p for p in rifa.premios if p.tipo == "seco"]:  # en borrador no hay resultados: se reemplazan
        rifa.premios.remove(seco)
        db.delete(seco)
    for i, seco in enumerate(sorted(datos.premios_secos, key=lambda p: p.fecha_juego), start=2):
        db.add(
            Premio(
                rifa=rifa,
                tipo="seco",
                descripcion=seco.descripcion,
                loteria_id=seco.loteria_id,
                fecha_juego=seco.fecha_juego,
                valor_estimado=seco.valor_estimado,
                foto_url=seco.foto_url,
                orden=i,
            )
        )

    rifa.duracion_meses = duracion.meses
    if cobro and cambia_plan:
        cobro.plan_id, cobro.valor = opcion.plan_id, valor_cobro
        cobro.estado = "aprobado" if valor_cobro == 0 else "pendiente"
        cobro.fecha_pago = cobro.referencia = cobro.comprobante_url = cobro.motivo_rechazo = None
    db.flush()
    if regenerar:
        generar_boletas(db, rifa)
    auditoria.registrar(
        db,
        usuario,
        "rifas",
        rifa.id,
        "editar",
        ip=ip,
        anterior=anterior,
        nuevo={
            "nombre": rifa.nombre,
            "opcion": f"{rifa.cifras}-{rifa.series_por_boleta}",
            "valor_boleta": int(rifa.valor_boleta),
            "fecha_sorteo": rifa.fecha_sorteo.isoformat(),
        },
    )
    db.commit()


def editar_en_venta(
    db: Session,
    usuario: Usuario,
    rifa: Rifa,
    nombre: str,
    descripcion: str | None,
    premios: dict[int, tuple[str, int | None]],
    nuevos_secos: list,
    ip: str | None = None,
    fotos: dict[int, str] | None = None,
) -> None:
    """En venta solo se corrige lo que no perjudica a quien ya compró: textos, valores y fotos, secos nuevos."""
    if rifa.estado != "en_venta":
        raise ErrorNegocio("Solo se corrigen rifas en venta.")
    vigencia.exigir_vigente(rifa)
    nombre = " ".join((nombre or "").split())
    if len(nombre) < 3:
        raise ErrorNegocio("El nombre de la rifa debe tener al menos 3 caracteres.")
    hoy = date.today()
    for seco in nuevos_secos:
        if db.get(Loteria, seco.loteria_id) is None:
            raise ErrorNegocio("Escoja la lotería de cada premio seco nuevo.")
        if not hoy < seco.fecha_juego <= rifa.fecha_sorteo:
            raise ErrorNegocio(
                "Los premios secos nuevos deben jugar después de hoy y antes del sorteo del premio mayor."
            )
    anterior = {"nombre": rifa.nombre, "premios": {p.id: p.descripcion for p in rifa.premios}}
    rifa.nombre, rifa.descripcion = nombre, (descripcion or "").strip() or None
    for premio in rifa.premios:
        if premio.id in premios and premio.resultado is None:
            texto, valor = premios[premio.id]
            if len(texto.strip()) < 3:
                raise ErrorNegocio("La descripción de cada premio debe tener al menos 3 caracteres.")
            premio.descripcion, premio.valor_estimado = texto.strip()[:300], valor
        if premio.id in (fotos or {}) and premio.resultado is None:
            premio.foto_url = fotos[premio.id]
    orden = max((p.orden for p in rifa.premios), default=1)
    for i, seco in enumerate(sorted(nuevos_secos, key=lambda p: p.fecha_juego), start=1):
        db.add(
            Premio(
                rifa=rifa,
                tipo="seco",
                descripcion=seco.descripcion,
                loteria_id=seco.loteria_id,
                fecha_juego=seco.fecha_juego,
                valor_estimado=seco.valor_estimado,
                foto_url=seco.foto_url,
                orden=orden + i,
            )
        )
    auditoria.registrar(
        db,
        usuario,
        "rifas",
        rifa.id,
        "editar_en_venta",
        ip=ip,
        anterior=anterior,
        nuevo={"nombre": rifa.nombre, "secos_nuevos": len(nuevos_secos)},
    )
    db.commit()


def rifa_del_organizador(db: Session, rifa_id: int, usuario: Usuario) -> Rifa | None:
    """La rifa solo si pertenece al organizador del usuario; si no, None."""
    rifa = db.get(Rifa, rifa_id)
    return rifa if rifa and rifa.organizador_id == usuario.organizador_id else None


def rifas_del_organizador(db: Session, organizador_id: int) -> tuple[list[Rifa], dict[int, int]]:
    """Rifas del organizador y cuántas boletas lleva vendidas cada una."""
    rifas = list(
        db.scalars(select(Rifa).where(Rifa.organizador_id == organizador_id).order_by(Rifa.fecha_creacion.desc()))
    )
    vendidas = dict(
        db.execute(
            select(Boleta.rifa_id, func.count())
            .join(Rifa, Rifa.id == Boleta.rifa_id)
            .where(Rifa.organizador_id == organizador_id, Boleta.estado == "vendida")
            .group_by(Boleta.rifa_id)
        ).all()
    )
    return rifas, vendidas


FILTROS = {
    "": "Todas",
    "disponibles": "Disponibles",
    "atrasadas": "Atrasadas",
    "con_saldo": "Deben",
    "pagadas": "Pagadas",
}


def detalle(db: Session, rifa: Rifa, pagina: int = 1, buscar: str = "", filtro_estado: str = "") -> DetalleRifa:
    """Resumen de la rifa y una página de boletas; buscar acepta número, N.° de boleta o nombre del comprador."""
    from app.modulos.ventas.servicio import pagado_por_boleta, resumen  # evita importación circular

    buscar = buscar.strip()
    filtro = [Boleta.rifa_id == rifa.id]
    if buscar.isdigit():
        con_numero = select(NumeroBoleta.boleta_id).where(
            NumeroBoleta.rifa_id == rifa.id, NumeroBoleta.numero == buscar.zfill(rifa.cifras)
        )
        con_cedula = select(Cliente.id).where(Cliente.numero_documento == buscar)
        filtro.append(
            or_(Boleta.consecutivo == int(buscar), Boleta.id.in_(con_numero), Boleta.cliente_id.in_(con_cedula))
        )
    elif buscar:
        filtro.append(Boleta.cliente_id.in_(select(Cliente.id).where(Cliente.nombre.ilike(f"%{buscar}%"))))

    if filtro_estado == "disponibles":
        filtro.append(Boleta.estado == "disponible")
    elif filtro_estado == "atrasadas":  # con cuotas vencidas sin pagar
        pagado = (
            select(func.coalesce(func.sum(Pago.monto), 0))
            .where(Pago.boleta_id == Boleta.id, Pago.estado == "aprobado")
            .scalar_subquery()
        )
        filtro.append(Boleta.estado == "vendida")
        filtro.append(pagado < debido_hasta(rifa, date.today() - timedelta(days=1)))
    elif filtro_estado in ("con_saldo", "pagadas"):
        pagado = (
            select(func.coalesce(func.sum(Pago.monto), 0))
            .where(Pago.boleta_id == Boleta.id, Pago.estado == "aprobado")
            .scalar_subquery()
        )
        filtro.append(Boleta.estado == "vendida")
        filtro.append(pagado < rifa.valor_boleta if filtro_estado == "con_saldo" else pagado >= rifa.valor_boleta)

    encontradas = db.scalar(select(func.count()).select_from(Boleta).where(*filtro)) or 0
    paginas = max(1, -(-encontradas // BOLETAS_POR_PAGINA))
    pagina = min(max(1, pagina), paginas)
    boletas = list(
        db.scalars(
            select(Boleta)
            .where(*filtro)
            .order_by(Boleta.consecutivo)
            .offset((pagina - 1) * BOLETAS_POR_PAGINA)
            .limit(BOLETAS_POR_PAGINA)
            .options(selectinload(Boleta.numeros), selectinload(Boleta.cliente))
        )
    )
    cobro = db.scalar(select(CobroRifa).where(CobroRifa.rifa_id == rifa.id))
    por_estado = dict(
        db.execute(select(Boleta.estado, func.count()).where(Boleta.rifa_id == rifa.id).group_by(Boleta.estado)).all()
    )
    d = DetalleRifa(rifa, boletas, cobro, por_estado, pagina, paginas, encontradas, buscar)
    d.pagado = pagado_por_boleta(db, [b.id for b in boletas])
    d.ventas = resumen(db, rifa)
    d.filtro_estado = filtro_estado if filtro_estado in FILTROS else ""
    return d


@dataclass
class CuentasRifa:
    """Las cuentas de una rifa para el organizador: lo que espera recaudar, lo que lleva y lo que le queda."""

    recaudo_esperado: int  # si vende todas las boletas
    recaudado: int  # pagos aprobados hasta hoy
    premios: int  # valor estimado del premio mayor y los secos
    rifaplus: int  # plan + renovaciones aprobadas
    comisiones: int  # comisiones de vendedores causadas hasta hoy

    @property
    def ganancia_esperada(self) -> int:
        """Si vende todo: recaudo − premios − RifaPlus (antes de comisiones)."""
        return self.recaudo_esperado - self.premios - self.rifaplus

    @property
    def ganancia_hoy(self) -> int:
        """Con lo recaudado hasta hoy: recaudado − premios − RifaPlus − comisiones."""
        return self.recaudado - self.premios - self.rifaplus - self.comisiones


def cuentas(db: Session, rifa: Rifa) -> CuentasRifa:
    """Calcula las cuentas de la rifa con sus datos actuales."""
    from app.modulos.pagos.modelos import RenovacionRifa
    from app.modulos.personas.modelos import Vendedor
    from app.modulos.ventas.servicio import resumen

    cobro = db.scalar(select(CobroRifa).where(CobroRifa.rifa_id == rifa.id))
    renovaciones = (
        db.scalar(
            select(func.coalesce(func.sum(RenovacionRifa.valor), 0)).where(
                RenovacionRifa.rifa_id == rifa.id, RenovacionRifa.estado == "aprobado"
            )
        )
        or 0
    )
    comisiones = 0
    for porcentaje, total in db.execute(
        select(Vendedor.comision_porcentaje, func.coalesce(func.sum(Pago.monto), 0))
        .join(Boleta, Boleta.vendedor_id == Vendedor.id)
        .join(Pago, Pago.boleta_id == Boleta.id)
        .where(Boleta.rifa_id == rifa.id, Pago.estado == "aprobado")
        .group_by(Vendedor.id)
    ).all():
        comisiones += int(round(int(total) * float(porcentaje or 0) / 100))
    return CuentasRifa(
        recaudo_esperado=int(rifa.valor_boleta) * rifa.total_boletas,
        recaudado=resumen(db, rifa).recaudado,
        premios=sum(int(p.valor_estimado or 0) for p in rifa.premios),
        rifaplus=int(cobro.valor if cobro else 0) + int(renovaciones),
        comisiones=comisiones,
    )


def falta_verificacion(db: Session, rifa: Rifa) -> bool:
    """True si el organizador no está verificado y ya tiene otra rifa publicada (la primera va sin verificar)."""
    organizador = rifa.organizador
    if organizador.verificado:
        return False
    publicadas = db.scalar(
        select(func.count())
        .select_from(Rifa)
        .where(Rifa.organizador_id == organizador.id, Rifa.estado != "borrador", Rifa.id != rifa.id)
    )
    return bool(publicadas)


MENSAJE_VERIFICACION = (
    "Para publicar más de una rifa, RifaPlus debe verificar su nombre y su número de documento. "
    "Ya le avisamos al equipo de RifaPlus; le avisaremos cuando esté verificado. "
    "Si tiene dudas, escríbanos por el chat de ayuda."
)


def exigir_verificacion(db: Session, rifa: Rifa) -> None:
    """Detiene la publicación (o el pago para publicar) si el organizador debe verificarse primero."""
    if falta_verificacion(db, rifa):
        raise ErrorNegocio(MENSAJE_VERIFICACION)


def publicar(db: Session, usuario: Usuario, rifa: Rifa, ip: str | None = None) -> None:
    """Solo se publica con el plan pagado. La autorización legal es responsabilidad del organizador."""
    if rifa.estado != "borrador":
        raise ErrorNegocio("Esta rifa ya fue publicada.")
    exigir_verificacion(db, rifa)
    cobro = db.scalar(select(CobroRifa).where(CobroRifa.rifa_id == rifa.id))
    if cobro is None or cobro.estado != "aprobado":
        raise ErrorNegocio("La rifa solo se puede publicar cuando el pago de su plan esté aprobado.")
    rifa.estado = "en_venta"
    vigencia.iniciar(rifa)
    auditoria.registrar(
        db, usuario, "rifas", rifa.id, "publicar", ip=ip, anterior={"estado": "borrador"}, nuevo={"estado": "en_venta"}
    )
    db.commit()


def motivo_para_no_eliminar(db: Session, rifa: Rifa) -> str | None:
    """Una rifa se puede eliminar solo si no tiene ventas, pagos ni plan pagado."""
    vendidas = db.scalar(
        select(func.count()).select_from(Boleta).where(Boleta.rifa_id == rifa.id, Boleta.estado == "vendida")
    )
    if vendidas:
        return "Esta rifa ya tiene boletas vendidas, así que no se puede eliminar."
    pagos = db.scalar(
        select(func.count())
        .select_from(Pago)
        .join(Boleta, Boleta.id == Pago.boleta_id)
        .where(Boleta.rifa_id == rifa.id)
    )
    if pagos:
        return "Esta rifa tiene pagos registrados, así que no se puede eliminar."
    cobro = db.scalar(select(CobroRifa).where(CobroRifa.rifa_id == rifa.id))
    if cobro and cobro.estado == "aprobado" and int(cobro.valor) > 0:
        return "El plan de esta rifa ya fue pagado, así que no se puede eliminar."
    return None


def eliminar(db: Session, usuario: Usuario, rifa: Rifa, ip: str | None = None) -> None:
    """Borra la rifa con sus boletas y números. La declaración del organizador se conserva como respaldo."""
    from sqlalchemy import delete, update

    from app.modulos.legal.modelos import Aceptacion

    motivo = motivo_para_no_eliminar(db, rifa)
    if motivo:
        raise ErrorNegocio(motivo)
    datos = {"nombre": rifa.nombre, "boletas": rifa.total_boletas, "estado": rifa.estado}
    db.execute(update(Aceptacion).where(Aceptacion.rifa_id == rifa.id).values(rifa_id=None))
    db.execute(delete(NumeroBoleta).where(NumeroBoleta.rifa_id == rifa.id))
    db.execute(delete(Boleta).where(Boleta.rifa_id == rifa.id))
    db.execute(delete(CobroRifa).where(CobroRifa.rifa_id == rifa.id))
    db.execute(delete(Premio).where(Premio.rifa_id == rifa.id))
    auditoria.registrar(db, usuario, "rifas", rifa.id, "eliminar", anterior=datos, ip=ip)
    db.delete(rifa)
    db.commit()


def boleta_por_codigo(db: Session, codigo: str) -> Boleta | None:
    """Boleta por su código de verificación (sin importar mayúsculas)."""
    return db.scalar(select(Boleta).where(Boleta.codigo_verificacion == codigo.strip().upper()))
