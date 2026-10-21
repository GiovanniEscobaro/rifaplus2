"""Motor de plantillas Jinja2 y filtros de formato colombiano."""

from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.core.config import obtener_config

plantillas = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "web" / "plantillas"))


def pesos(valor) -> str:
    """12345 -> $12.345"""
    try:
        return "$" + f"{int(valor):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "$0"


def solo_digitos(valor) -> str:
    """'100.000' -> '100000' (los campos de dinero llegan con puntos de miles)."""
    return "".join(c for c in str(valor or "") if c.isdigit())


def miles(valor) -> str:
    """Formatea un número con puntos de miles sin el signo $: 12345 -> '12.345'."""
    try:
        return f"{int(valor):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "0"


MESES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]


def fecha_larga(valor) -> str:
    """Escribe una fecha en español: date(2026, 12, 13) -> '13 de diciembre de 2026'."""
    if not valor:
        return ""
    return f"{valor.day} de {MESES[valor.month - 1]} de {valor.year}"


def hora_colombia(valor, formato: str = "%d/%m %H:%M") -> str:
    """Fecha y hora guardadas en UTC, mostradas en hora de Colombia."""
    from zoneinfo import ZoneInfo

    return valor.astimezone(ZoneInfo("America/Bogota")).strftime(formato) if valor else ""


class _Hoy:
    """Fecha de hoy al momento de mostrar la página (no al arrancar el servidor)."""

    def __sub__(self, otra):
        from datetime import date

        return date.today() - otra

    def __rsub__(self, otra):
        from datetime import date

        return otra - date.today()


plantillas.env.filters.update(hora_colombia=hora_colombia, pesos=pesos, miles=miles, fecha_larga=fecha_larga)
plantillas.env.globals["config"] = obtener_config()

# Versión de los archivos estáticos: cambia cada vez que se modifica el CSS o el JS,
# así el navegador descarga la versión nueva en lugar de usar la que tenía guardada.
_ESTATICOS = Path(__file__).resolve().parent.parent / "web" / "estaticos"


def _version_estaticos() -> str:
    """Número que cambia cuando cambia algún CSS o JS; se agrega a sus enlaces para evitar la caché vieja."""
    archivos = [p for p in _ESTATICOS.rglob("*") if p.suffix in (".css", ".js")]
    return str(int(max((p.stat().st_mtime for p in archivos), default=0)))


plantillas.env.globals["v"] = _version_estaticos()


def errores_de_validacion(error) -> list[str]:
    """Convierte los errores de Pydantic en mensajes legibles para el formulario."""
    return [e["msg"].removeprefix("Value error, ") for e in error.errors()]


plantillas.env.globals["hoy"] = _Hoy()  # en las plantillas: (fecha - hoy).days
