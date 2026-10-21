"""Excepciones de la aplicación."""


class ErrorNegocio(ValueError):
    """Regla de negocio incumplida. El mensaje está listo para mostrárselo al usuario."""


class Redirigir(Exception):
    """Envía al usuario a otra página (por ejemplo, al ingreso o al cambio de clave)."""

    def __init__(self, url: str):
        self.url = url
