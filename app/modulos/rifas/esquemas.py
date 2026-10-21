"""Validación de datos de entrada para las rifas."""

from datetime import date

from pydantic import BaseModel, Field, field_validator, model_validator

REGLAS_SECO = {"desierto": "El premio queda desierto", "acumula": "Se acumula para el siguiente premio seco"}
REGLAS_MAYOR = {
    "paga_saldo": "Gana, pero debe pagar el saldo antes de recibir el premio",
    "desierto": "El premio queda desierto",
}


class CuotaDatos(BaseModel):
    """Una fila de la forma de pago: valor y fecha límite."""

    valor: int = Field(gt=0)
    fecha_limite: date


class PremioSecoDatos(BaseModel):
    """Una fila de premio seco: descripción, lotería y fecha."""

    descripcion: str = Field(min_length=3, max_length=300)
    loteria_id: int
    fecha_juego: date
    valor_estimado: int | None = None
    foto_url: str | None = None


class RifaCrear(BaseModel):
    """Todo lo que llega del formulario de nueva rifa, validado."""

    nombre: str = Field(min_length=3, max_length=150)
    descripcion: str | None = None
    loteria_id: int
    fecha_sorteo: date
    opcion: str = Field(pattern=r"^[1-4]-\d{1,3}$")  # "dígitos del sorteo-cifras por boleta", p. ej. "4-4"
    duracion_id: int = 0  # por cuánto tiempo paga la rifa (6 meses, 1 año…)
    valor_boleta: int = Field(gt=0)
    premio_mayor: str = Field(min_length=3, max_length=300)
    valor_premio: int | None = None
    foto_mayor_url: str | None = None
    cuotas: list[CuotaDatos] = Field(default_factory=list)
    premios_secos: list[PremioSecoDatos] = Field(default_factory=list, max_length=24)
    regla_seco_atrasado: str = "desierto"
    regla_mayor_sin_pagar: str = "paga_saldo"
    acepta_declaracion: bool = False

    @field_validator("fecha_sorteo")
    @classmethod
    def fecha_futura(cls, v: date) -> date:
        """La fecha del sorteo no puede ser hoy ni una fecha pasada."""
        if v <= date.today():
            raise ValueError("La fecha del sorteo debe ser posterior a hoy.")
        return v

    @field_validator("acepta_declaracion")
    @classmethod
    def debe_aceptar(cls, v: bool) -> bool:
        """La declaración de responsabilidad del organizador es obligatoria."""
        if not v:
            raise ValueError("Debe aceptar la declaración de responsabilidad del organizador.")
        return v

    @field_validator("regla_seco_atrasado")
    @classmethod
    def regla_seco(cls, v: str) -> str:
        """Solo se aceptan las reglas conocidas para premios secos."""
        if v not in REGLAS_SECO:
            raise ValueError("Escoja qué pasa si un premio seco cae en una boleta atrasada.")
        return v

    @field_validator("regla_mayor_sin_pagar")
    @classmethod
    def regla_mayor(cls, v: str) -> str:
        """Solo se aceptan las reglas conocidas para el premio mayor."""
        if v not in REGLAS_MAYOR:
            raise ValueError("Escoja qué pasa si el premio mayor cae en una boleta sin pagar completa.")
        return v

    @model_validator(mode="after")
    def premios_secos_en_fecha(self):
        """Cada premio seco juega después de hoy y a más tardar el día del premio mayor."""
        for i, p in enumerate(self.premios_secos, start=1):
            if p.fecha_juego <= date.today():
                raise ValueError(f"La fecha del premio seco {i} debe ser posterior a hoy.")
            if p.fecha_juego > self.fecha_sorteo:
                raise ValueError(f"El premio seco {i} debe jugar a más tardar el día del sorteo del premio mayor.")
        return self

    @property
    def cifras(self) -> int:
        """Cifras de la opción escogida (la parte antes del guion de '4-4')."""
        return int(self.opcion.split("-")[0])

    @property
    def numeros_por_boleta(self) -> int:
        """Números por boleta de la opción escogida (la parte después del guion)."""
        return int(self.opcion.split("-")[1])
