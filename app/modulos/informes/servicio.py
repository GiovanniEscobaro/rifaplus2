"""Informes de ventas: boletas vendidas filtradas por rifa, vendedor, ciudad, comprador y estado de pago."""

import csv
import io
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.modulos.personas.modelos import Cliente
from app.modulos.rifas.cuotas import debido_hasta
from app.modulos.rifas.modelos import Boleta, Rifa
from app.modulos.ventas.servicio import pagado_por_boleta

ESTADOS = {"": "Todas", "pagadas": "Pagadas", "deben": "Deben", "atrasadas": "Atrasadas"}
MAX_FILAS_PANTALLA = 300


@dataclass
class Filtros:
    """Filtros del informe; todos son opcionales."""

    rifa_id: int | None = None
    vendedor: str = ""  # "" todos, "organizador" = vendidas por el organizador, o el id del vendedor
    ciudad: str = ""
    comprador: str = ""  # cédula (o su comienzo) o parte del nombre
    estado: str = ""

    @property
    def activos(self) -> bool:
        """True si se escribió o escogió algún filtro."""
        return bool(self.rifa_id or self.vendedor or self.ciudad.strip() or self.comprador.strip() or self.estado)


@dataclass
class Fila:
    """Una boleta vendida en el informe, con lo pagado y lo que debe."""

    boleta: Boleta
    pagado: int
    debe: int
    atrasada: bool

    @property
    def estado(self) -> str:
        """Texto corto del estado de pago."""
        if self.debe == 0:
            return "Pagada"
        return "Atrasada" if self.atrasada else "Debe"


@dataclass
class Informe:
    """Resultado del informe: filas y totales."""

    filas: list[Fila] = field(default_factory=list)

    @property
    def total_recaudado(self) -> int:
        """Suma de lo pagado en las boletas del informe."""
        return sum(f.pagado for f in self.filas)

    @property
    def total_por_cobrar(self) -> int:
        """Suma de lo que deben las boletas del informe."""
        return sum(f.debe for f in self.filas)


def generar(db: Session, organizador_id: int, filtros: Filtros) -> Informe:
    """Arma el informe: filtra en la base de datos y calcula pagos, saldos y atrasos de cada boleta."""
    consulta = (
        select(Boleta)
        .join(Rifa, Rifa.id == Boleta.rifa_id)
        .join(Cliente, Cliente.id == Boleta.cliente_id)
        .where(Rifa.organizador_id == organizador_id, Boleta.estado == "vendida")
        .options(
            selectinload(Boleta.cliente),
            selectinload(Boleta.vendedor),
            selectinload(Boleta.rifa),
            selectinload(Boleta.numeros),
        )
        .order_by(Rifa.fecha_creacion.desc(), Boleta.consecutivo)
    )
    if filtros.rifa_id:
        consulta = consulta.where(Boleta.rifa_id == filtros.rifa_id)
    if filtros.vendedor == "organizador":
        consulta = consulta.where(Boleta.vendedor_id.is_(None))
    elif filtros.vendedor.isdigit():
        consulta = consulta.where(Boleta.vendedor_id == int(filtros.vendedor))
    if filtros.ciudad.strip():
        consulta = consulta.where(Cliente.ciudad.ilike(f"%{filtros.ciudad.strip()}%"))
    texto = " ".join(filtros.comprador.split())
    if texto:
        documento = "".join(c for c in texto if c.isalnum()).upper()
        condicion = Cliente.nombre.ilike(f"%{texto}%")
        if any(c.isdigit() for c in documento):
            condicion = or_(condicion, Cliente.numero_documento.startswith(documento))
        consulta = consulta.where(condicion)

    boletas = list(db.scalars(consulta))
    pagado = pagado_por_boleta(db, [b.id for b in boletas])
    ayer = date.today() - timedelta(days=1)
    debido_rifa: dict[int, int] = {}
    filas = []
    for b in boletas:
        if b.rifa_id not in debido_rifa:
            debido_rifa[b.rifa_id] = debido_hasta(b.rifa, ayer)
        p = pagado.get(b.id, 0)
        fila = Fila(b, p, max(int(b.rifa.valor_boleta) - p, 0), p < debido_rifa[b.rifa_id])
        if (
            (filtros.estado == "pagadas" and fila.debe)
            or (filtros.estado == "deben" and not fila.debe)
            or (filtros.estado == "atrasadas" and not fila.atrasada)
        ):
            continue
        filas.append(fila)
    return Informe(filas)


def a_csv(informe: Informe) -> str:
    """Convierte el informe en CSV para Excel (separado por punto y coma, con marca UTF-8)."""
    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=";")
    escritor.writerow(
        [
            "Rifa",
            "Boleta",
            "Números",
            "Comprador",
            "Tipo doc.",
            "Documento",
            "Celular",
            "WhatsApp",
            "Correo",
            "Dirección",
            "Ciudad",
            "Vendedor",
            "Valor boleta",
            "Pagado",
            "Debe",
            "Estado",
        ]
    )
    for f in informe.filas:
        b, c = f.boleta, f.boleta.cliente
        escritor.writerow(
            [
                b.rifa.nombre,
                b.etiqueta,
                " ".join(n.numero for n in b.numeros),
                c.nombre,
                c.tipo_documento,
                c.numero_documento,
                c.celular,
                c.whatsapp,
                c.email,
                c.direccion,
                c.ciudad,
                b.vendedor.nombre if b.vendedor else "Organizador",
                int(b.rifa.valor_boleta),
                f.pagado,
                f.debe,
                f.estado,
            ]
        )
    return "\ufeff" + salida.getvalue()
