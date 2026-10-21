"""Envío de correos (clave temporal, recuperar clave, avisos al superadministrador).

Usa SMTP con TLS, por ejemplo Gmail con una "contraseña de aplicación". Sin datos de correo en el .env,
el mensaje solo se escribe en el registro del servidor, para que en desarrollo todo funcione sin enviar nada.
Los envíos se hacen en segundo plano (BackgroundTasks) para que la página no espere al servidor de correo.
"""

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import obtener_config

log = logging.getLogger("rifaplus.correo")

PIE = (
    "\n\n—\nRifaPlus · Administración de rifas\n"
    "Este es un mensaje automático; si necesita ayuda, use el chat de su panel."
)


def enviar(destino: str, asunto: str, texto: str) -> bool:
    """Envía un correo de texto. Devuelve True si se envió; nunca lanza error (solo lo registra)."""
    return enviar_con_detalle(destino, asunto, texto)[0]


def enviar_con_detalle(destino: str, asunto: str, texto: str) -> tuple[bool, str]:
    """Igual que enviar(), pero devuelve también qué pasó, en palabras, para el botón «Probar correo»."""
    cfg = obtener_config()
    if not destino:
        return False, "No hay correo de destino."
    if not cfg.correo_activo:
        log.warning("Correo NO enviado (sin SMTP configurado) a %s · %s\n%s", destino, asunto, texto)
        return False, "El correo no está configurado: faltan SMTP_USUARIO y SMTP_CLAVE en el archivo .env."
    mensaje = EmailMessage()
    mensaje["From"] = formataddr(("RifaPlus", cfg.correo_remitente or cfg.smtp_usuario))
    mensaje["To"] = destino
    mensaje["Subject"] = asunto
    mensaje.set_content(texto + PIE)
    try:
        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_puerto, timeout=20) as servidor:
            servidor.starttls(context=ssl.create_default_context())
            servidor.login(cfg.smtp_usuario, cfg.smtp_clave)
            servidor.send_message(mensaje)
        log.info("Correo enviado a %s · %s", destino, asunto)
        return True, f"Correo enviado a {destino}."
    except smtplib.SMTPAuthenticationError as e:
        log.error("Gmail rechazó el usuario o la clave: %s", e)
        return False, (
            "Gmail rechazó el usuario o la clave. Use una «contraseña de aplicación» de 16 letras "
            "(no su clave normal de Gmail) y revise que SMTP_USUARIO sea el correo completo."
        )
    except (smtplib.SMTPException, OSError) as e:
        log.error("No se pudo enviar el correo a %s · %s: %s", destino, asunto, e)
        return False, f"No se pudo enviar el correo: {e}"


def avisar_admin(asunto: str, texto: str) -> bool:
    """Aviso para el superadministrador (pagos por revisar, consultas de soporte)."""
    return enviar(obtener_config().correo_avisos_admin, f"[RifaPlus] {asunto}", texto)
