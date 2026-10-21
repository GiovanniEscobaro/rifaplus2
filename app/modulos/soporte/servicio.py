"""Chat de soporte: guarda mensajes, responde lo común con el asistente y deja lo demás para RifaPlus."""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.excepciones import ErrorNegocio
from app.modulos.acceso.modelos import Usuario
from app.modulos.soporte import preguntas
from app.modulos.soporte.modelos import ConversacionSoporte, MensajeSoporte

MAX_TEXTO = 2000
SALUDO = (
    "¡Hola! Soy el asistente de RifaPlus. Toque una de las preguntas frecuentes o escríbame su duda. "
    "Si no sé la respuesta, se la paso al equipo de RifaPlus y le responderán aquí mismo."
)
PASO_A_RIFAPLUS = (
    "No tengo una respuesta exacta para eso. Ya le pasé su mensaje al equipo de RifaPlus: "
    "le responderán aquí mismo, normalmente el mismo día."
)


def _ahora() -> datetime:
    """Fecha y hora actual en UTC."""
    return datetime.now(timezone.utc)


def conversacion_de(db: Session, organizador_id: int, crear: bool = True) -> ConversacionSoporte | None:
    """La conversación del organizador; la crea con el saludo del asistente si no existe."""
    conv = db.scalar(select(ConversacionSoporte).where(ConversacionSoporte.organizador_id == organizador_id))
    if conv is None and crear:
        conv = ConversacionSoporte(organizador_id=organizador_id, estado="atendida")
        conv.mensajes.append(MensajeSoporte(autor="asistente", texto=SALUDO))
        db.add(conv)
        db.commit()
    return conv


def _respuesta(db: Session, pregunta: preguntas.Pregunta) -> str:
    """Texto de la respuesta. La de precios se arma con los planes vigentes, porque el superadmin los puede cambiar."""
    if pregunta.clave != "precios":
        return pregunta.respuesta
    from app.core.plantillas import miles, pesos
    from app.modulos.pagos.servicio import planes_activos

    partes = [
        f"{miles(p.boletas_max)} boletas de {p.numeros_min} cifra{'s' if p.numeros_min > 1 else ''}, "
        f"{'gratis' if int(p.valor) == 0 else pesos(p.valor)}"
        for p in planes_activos(db)
        if p.boletas_min == p.boletas_max
    ]
    return (
        "Se paga una sola vez por cada rifa, según cuántas boletas vende y cuántas cifras trae cada una: "
        + "; ".join(partes)
        + " (precio del período más corto; al crear la rifa verá los precios de las demás duraciones). "
        "Si la rifa sigue después de ese tiempo, se renueva."
    )


def _agregar(conv: ConversacionSoporte, autor: str, texto: str, usuario: Usuario | None = None) -> None:
    """Agrega un mensaje y actualiza la fecha de la conversación."""
    conv.mensajes.append(MensajeSoporte(autor=autor, texto=texto, usuario_id=usuario.id if usuario else None))
    conv.actualizada_en = _ahora()


def escribir(
    db: Session, usuario: Usuario, texto: str = "", clave_pregunta: str = "", hablar_con_persona: bool = False
) -> ConversacionSoporte:
    """Procesa lo que envía el organizador.

    - Si tocó una pregunta frecuente, responde el asistente.
    - Si escribió y el asistente reconoce la duda, responde el asistente.
    - Si no, o si pidió hablar con una persona, la conversación queda pendiente para el superadministrador.
    """
    conv = conversacion_de(db, usuario.organizador_id)
    conv.sin_leer_organizador = False
    pregunta = preguntas.por_clave(clave_pregunta) if clave_pregunta else None
    if pregunta:
        _agregar(conv, "organizador", pregunta.titulo, usuario)
        _agregar(conv, "asistente", _respuesta(db, pregunta))
    elif hablar_con_persona:
        _agregar(conv, "organizador", "Quiero hablar con una persona de RifaPlus.", usuario)
        _agregar(
            conv,
            "asistente",
            "Listo, ya le avisé al equipo de RifaPlus. Escriba aquí su consulta con el "
            "detalle que quiera y le responderán en este chat.",
        )
        conv.estado = "pendiente"
    else:
        texto = " ".join((texto or "").split())[:MAX_TEXTO]
        if not texto:
            raise ErrorNegocio("Escriba su mensaje.")
        _agregar(conv, "organizador", texto, usuario)
        encontrada = preguntas.buscar(texto) if conv.estado != "pendiente" else None
        if encontrada:
            _agregar(conv, "asistente", _respuesta(db, encontrada) + "\n\n¿No era eso? Toque «Hablar con una persona».")
        else:
            if conv.estado != "pendiente":
                _agregar(conv, "asistente", PASO_A_RIFAPLUS)
            conv.estado = "pendiente"
    db.commit()
    return conv


def responder(db: Session, admin: Usuario, conv: ConversacionSoporte, texto: str) -> None:
    """El superadministrador responde; el organizador lo verá en su chat como mensaje de RifaPlus."""
    texto = (texto or "").strip()[:MAX_TEXTO]
    if not texto:
        raise ErrorNegocio("Escriba la respuesta.")
    _agregar(conv, "rifaplus", texto, admin)
    conv.estado = "atendida"
    conv.sin_leer_organizador = True
    db.commit()


def marcar_atendida(db: Session, conv: ConversacionSoporte) -> None:
    """Cierra la consulta sin escribir (por ejemplo, si el organizador ya resolvió solo)."""
    conv.estado = "atendida"
    db.commit()


def conversaciones(db: Session) -> list[ConversacionSoporte]:
    """Todas las conversaciones: primero las pendientes, luego las más recientes."""
    return list(
        db.scalars(
            select(ConversacionSoporte).order_by(
                (ConversacionSoporte.estado == "pendiente").desc(), ConversacionSoporte.actualizada_en.desc()
            )
        )
    )


def pendientes(db: Session) -> int:
    """Cuántas conversaciones esperan respuesta de RifaPlus (para el aviso en el menú)."""
    return (
        db.scalar(
            select(func.count()).select_from(ConversacionSoporte).where(ConversacionSoporte.estado == "pendiente")
        )
        or 0
    )


def a_json(conv: ConversacionSoporte | None) -> dict:
    """La conversación lista para el chat del panel."""
    mensajes = conv.mensajes if conv else []
    return {
        "estado": conv.estado if conv else "atendida",
        "sin_leer": bool(conv and conv.sin_leer_organizador),
        "mensajes": [{"id": m.id, "autor": m.autor, "texto": m.texto, "fecha": m.fecha.isoformat()} for m in mensajes],
        "preguntas": [{"clave": p.clave, "titulo": p.titulo} for p in preguntas.PREGUNTAS],
    }
