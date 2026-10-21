"""Correos al organizador sobre su cuenta: clave temporal y recuperación de clave."""

from app.core.config import obtener_config
from app.core.correo import enviar


def enviar_clave_temporal(nombre: str, email: str, whatsapp: str, clave: str) -> bool:
    """Envía al correo del organizador la clave temporal con la que ingresa la primera vez."""
    url = obtener_config().app_url
    texto = (
        f"Hola, {nombre.split()[0]}:\n\n"
        f"Su cuenta de RifaPlus quedó creada. Para ingresar use:\n\n"
        f"  Correo: {email}\n"
        f"  Clave temporal: {clave}\n\n"
        f"Ingrese en {url}/ingresar. La primera vez, RifaPlus le pedirá crear su clave definitiva.\n"
        f"Si usted no creó esta cuenta, ignore este mensaje."
    )
    return enviar(email, "Su clave temporal de RifaPlus", texto)


def enviar_enlace_recuperacion(nombre: str, email: str, token: str) -> bool:
    """Envía el enlace de un solo uso para crear una clave nueva (vence en una hora)."""
    url = obtener_config().app_url
    texto = (
        f"Hola, {nombre.split()[0]}:\n\n"
        f"Recibimos una solicitud para cambiar la clave de su cuenta de RifaPlus.\n"
        f"Para crear una clave nueva, abra este enlace (sirve una sola vez y vence en una hora):\n\n"
        f"  {url}/restablecer-clave/{token}\n\n"
        f"Si usted no lo pidió, ignore este mensaje: su clave actual sigue funcionando."
    )
    return enviar(email, "Cambie su clave de RifaPlus", texto)


def enviar_clave_restablecida(nombre: str, email: str, clave: str) -> bool:
    """Cuando el superadministrador restablece la clave, le envía al organizador la nueva clave temporal."""
    url = obtener_config().app_url
    texto = (
        f"Hola, {nombre.split()[0]}:\n\n"
        f"El equipo de RifaPlus restableció la clave de su cuenta.\n\n"
        f"  Clave temporal: {clave}\n\n"
        f"Ingrese en {url}/ingresar; RifaPlus le pedirá crear una clave nueva."
    )
    return enviar(email, "Su clave de RifaPlus fue restablecida", texto)


def enviar_invitacion_equipo(nombre: str, email: str, clave: str, organizador: str) -> bool:
    """Le avisa a un colaborador que el organizador lo agregó a su equipo, con su clave temporal."""
    url = obtener_config().app_url
    texto = (
        f"Hola, {nombre.split()[0]}:\n\n"
        f"{organizador} lo agregó a su equipo en RifaPlus para ayudarle a manejar sus rifas.\n\n"
        f"  Correo: {email}\n"
        f"  Clave temporal: {clave}\n\n"
        f"Ingrese en {url}/ingresar. La primera vez, RifaPlus le pedirá crear su clave definitiva.\n"
        f"Si no esperaba este mensaje, ignórelo."
    )
    return enviar(email, f"{organizador} lo agregó a su equipo en RifaPlus", texto)
