"""Importa todos los modelos para que SQLAlchemy y Alembic los conozcan."""

from app.modulos.acceso.modelos import HistorialAcceso, Organizador, Sesion, TokenSeguridad, Usuario  # noqa: F401
from app.modulos.auditoria.modelos import Auditoria  # noqa: F401
from app.modulos.legal.modelos import Aceptacion  # noqa: F401
from app.modulos.mensajes.modelos import MensajeWhatsapp  # noqa: F401
from app.modulos.pagos.modelos import (  # noqa: F401
    CobroRifa,
    CuentaCobro,
    Duracion,
    EntregaVendedor,
    MedioPago,
    Pago,
    PagoComision,
    Plan,
    PrecioRifa,
    RenovacionRifa,
)
from app.modulos.personas.modelos import Cliente, Vendedor  # noqa: F401
from app.modulos.rifas.modelos import Boleta, Cuota, Loteria, NumeroBoleta, Premio, Resultado, Rifa  # noqa: F401
from app.modulos.soporte.modelos import ConversacionSoporte, MensajeSoporte  # noqa: F401
