"""Boleta individual de un comprador: los datos para imprimirla o enviarla, con su código QR."""

from dataclasses import dataclass

import segno
from markupsafe import Markup
from sqlalchemy.orm import Session

from app.core.config import obtener_config
from app.modulos.rifas.cuotas import EstadoPlan, estado_plan
from app.modulos.rifas.modelos import Boleta, Premio
from app.modulos.ventas.servicio import Saldo, enlace_correo, enlace_whatsapp, saldo


@dataclass
class BoletaIndividual:
    """Todo lo que se pinta en la boleta individual."""

    boleta: Boleta
    saldo: Saldo
    plan: EstadoPlan
    premios: list[Premio]
    url_publica: str
    qr_svg: Markup
    completa: bool  # True para el organizador (datos completos); False en el enlace público
    correo: str | None = None  # enlace "Enviar por correo" (solo en la versión del organizador)
    whatsapp: str | None = None  # enlace "Enviar por WhatsApp" (solo en la versión del organizador)

    @property
    def mayor(self) -> Premio | None:
        """El premio mayor de la rifa."""
        return next((p for p in self.premios if p.tipo == "mayor"), None)

    @property
    def secos(self) -> list[Premio]:
        """Los premios secos, en orden de fecha."""
        return [p for p in self.premios if p.tipo == "seco"]

    @property
    def nombre_comprador(self) -> str:
        """Nombre completo para el organizador; en el enlace público solo nombre e inicial del apellido."""
        nombre = self.boleta.cliente.nombre if self.boleta.cliente else ""
        if self.completa or not nombre:
            return nombre
        partes = nombre.split()
        return partes[0] + (f" {partes[1][0]}." if len(partes) > 1 else "")


def url_publica(boleta: Boleta) -> str:
    """Dirección pública de la boleta, la que se envía al comprador y va en el código QR."""
    return f"{obtener_config().app_url}/boleta/{boleta.codigo_verificacion}"


def armar(db: Session, boleta: Boleta, completa: bool) -> BoletaIndividual:
    """Reúne saldo, plan de cuotas, premios y el QR de la boleta."""
    estado = saldo(db, boleta)
    url = url_publica(boleta)
    qr = segno.make(url, error="m").svg_inline(dark="#10131a", border=1, omitsize=True)  # viewBox: escala con el CSS
    premios = sorted(boleta.rifa.premios, key=lambda p: (p.tipo != "mayor", p.fecha, p.orden))
    individual = BoletaIndividual(
        boleta, estado, estado_plan(boleta.rifa, estado.pagado), premios, url, Markup(qr), completa
    )
    if completa:
        individual.correo = enlace_correo(boleta, estado)
        individual.whatsapp = enlace_whatsapp(boleta, estado)
    return individual
