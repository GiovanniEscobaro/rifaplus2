"""Claves, tokens y hashing."""

import hashlib
import secrets
import string

import bcrypt

# Sin caracteres que se confunden al leer (0/O, 1/l/I)
_ALFABETO = "".join(c for c in string.ascii_letters + string.digits if c not in "0O1lI")
_ALFABETO_CODIGO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"

LONGITUD_MINIMA_CLAVE = 8


def cifrar_clave(clave: str) -> str:
    """Cifra una clave con bcrypt. En la base de datos solo se guarda este resultado, nunca la clave."""
    return bcrypt.hashpw(clave.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verificar_clave(clave: str, clave_cifrada: str) -> bool:
    """Compara una clave escrita con su versión cifrada. Devuelve False si no coinciden o el hash es inválido."""
    try:
        return bcrypt.checkpw(clave.encode("utf-8"), clave_cifrada.encode("utf-8"))
    except ValueError:
        return False


def generar_clave_temporal(longitud: int = 10) -> str:
    """Genera la clave temporal del registro, sin caracteres que se confunden al leer (0/O, 1/l/I)."""
    return "".join(secrets.choice(_ALFABETO) for _ in range(longitud))


def generar_token() -> str:
    """Token aleatorio para cookies de sesión y enlaces de un solo uso."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """En la base de datos solo se guarda el hash del token, nunca el token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generar_codigo_verificacion(longitud: int = 10) -> str:
    """Código impreso en la boleta (y en su QR) para verificar que es auténtica."""
    return "".join(secrets.choice(_ALFABETO_CODIGO) for _ in range(longitud))


def validar_clave_nueva(clave: str, confirmacion: str) -> str | None:
    """Devuelve un mensaje de error, o None si la clave es válida."""
    if clave != confirmacion:
        return "Las dos claves no coinciden. Escríbalas de nuevo."
    if len(clave) < LONGITUD_MINIMA_CLAVE:
        return f"La clave debe tener al menos {LONGITUD_MINIMA_CLAVE} caracteres."
    if not any(c.isdigit() for c in clave) or not any(c.isalpha() for c in clave):
        return "La clave debe tener letras y números."
    return None
