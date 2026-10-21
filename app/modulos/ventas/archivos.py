"""Guardado de comprobantes de pago. Se guardan fuera de la carpeta pública y solo los ve su organizador."""

import secrets
from pathlib import Path

from fastapi import UploadFile

from app.core.config import obtener_config
from app.core.excepciones import ErrorNegocio

TIPOS_PERMITIDOS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "application/pdf": ".pdf"}
FIRMAS = {b"\xff\xd8\xff": "image/jpeg", b"\x89PNG": "image/png", b"RIFF": "image/webp", b"%PDF": "application/pdf"}


def carpeta_base() -> Path:
    """Carpeta donde se guardan los comprobantes (fuera de la carpeta pública)."""
    return Path(obtener_config().carpeta_archivos).resolve()


TIPOS_IMAGEN = {k: v for k, v in TIPOS_PERMITIDOS.items() if k.startswith("image/")}


async def _guardar(
    archivo: UploadFile | None, carpeta: str, organizador_id: int, tipos: dict, mensaje: str
) -> str | None:
    """Guarda un archivo subido si es de un tipo permitido (se revisa el contenido, no la extensión)."""
    if archivo is None or not archivo.filename:
        return None
    limite = obtener_config().max_mb_comprobante * 1024 * 1024
    contenido = await archivo.read(limite + 1)
    if not contenido:
        return None
    if len(contenido) > limite:
        raise ErrorNegocio(f"El archivo pesa más de {obtener_config().max_mb_comprobante} MB.")
    tipo = next((t for firma, t in FIRMAS.items() if contenido.startswith(firma)), None)
    if tipo not in tipos:
        raise ErrorNegocio(mensaje)
    relativa = Path(carpeta) / str(organizador_id) / (secrets.token_hex(16) + tipos[tipo])
    destino = carpeta_base() / relativa
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(contenido)
    return relativa.as_posix()


async def guardar_comprobante(archivo: UploadFile | None, organizador_id: int) -> str | None:
    """Guarda un comprobante de pago (privado). Devuelve su ruta relativa, o None si no se envió."""
    return await _guardar(
        archivo,
        "comprobantes",
        organizador_id,
        TIPOS_PERMITIDOS,
        "El comprobante debe ser una foto (JPG, PNG o WEBP) o un PDF.",
    )


async def guardar_foto(archivo: UploadFile | None, organizador_id: int) -> str | None:
    """Guarda la foto de un premio (pública en la boleta). Devuelve su ruta relativa, o None si no se envió."""
    return await _guardar(
        archivo, "fotos", organizador_id, TIPOS_IMAGEN, "La foto del premio debe ser una imagen JPG, PNG o WEBP."
    )


def foto_propia(ruta: str | None, organizador_id: int) -> str | None:
    """Acepta una ruta de foto ya guardada solo si es de este organizador (evita usar archivos ajenos)."""
    return ruta if ruta and ruta.startswith(f"fotos/{organizador_id}/") and ".." not in ruta else None


def ruta_absoluta(relativa: str) -> Path | None:
    """Ruta real de un comprobante, verificando que no se salga de la carpeta de archivos."""
    ruta = (carpeta_base() / relativa).resolve()
    if carpeta_base() not in ruta.parents or not ruta.is_file():
        return None
    return ruta
