"""Preguntas frecuentes del asistente del chat. Para agregar o cambiar respuestas, edite la lista PREGUNTAS.

Cada pregunta tiene palabras clave (sin tildes, en minúscula). El asistente responde la pregunta cuyas palabras
clave aparezcan más en el mensaje; si no hay una coincidencia clara, el mensaje pasa a RifaPlus.
"""

import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Pregunta:
    """Una pregunta frecuente con su respuesta."""

    clave: str
    titulo: str
    palabras: tuple[str, ...]
    respuesta: str


PREGUNTAS = [
    Pregunta(
        "crear",
        "¿Cómo creo una rifa?",
        ("crear", "creo", "nueva", "hacer", "armar"),
        "En el menú toque «Nueva rifa». Escriba el nombre y el premio, escoja la lotería y la fecha, la cantidad "
        "de boletas, el precio y la forma de pago. Abajo verá cómo quedará la boleta. Al guardar, RifaPlus genera "
        "todas las boletas con sus números, sin repetir.",
    ),
    Pregunta(
        "precios",
        "¿Cuánto cuesta RifaPlus?",
        ("cuesta", "precio", "precios", "plan", "planes", "valor", "cobran", "gratis", "tarifa"),
        "Se paga una sola vez por cada rifa, según sus boletas: hasta 10 boletas es gratis; hasta 25, $6.000; "
        "hasta 100, $19.900; hasta 500, $59.900; hasta 1.000, $89.900; hasta 2.500, $149.900; y hasta 10.000, "
        "$299.900. No hay mensualidades.",
    ),
    Pregunta(
        "publicar",
        "¿Cómo publico mi rifa y pago el plan?",
        ("publicar", "publico", "pagar", "pago", "llave", "bre-b", "breb", "nequi", "daviplata", "comprobante"),
        "En su rifa toque «Publicar rifa». Si es gratis, queda en venta de inmediato. Si es de pago, verá el valor "
        "y la cuenta de RifaPlus (llave Bre-B) a donde debe pagar. Pague, escriba la referencia o suba la foto "
        "del comprobante, y su rifa quedará publicada en cuanto confirmemos el pago.",
    ),
    Pregunta(
        "aprobacion",
        "¿Cuánto tarda la aprobación del pago?",
        ("tarda", "demora", "aprobacion", "aprueban", "revision", "cuando"),
        "Revisamos los pagos en horario laboral, normalmente el mismo día. En cuanto lo aprobamos, su rifa queda "
        "publicada sola. Si hay algún problema, verá el motivo en la rifa y podrá enviar el pago de nuevo.",
    ),
    Pregunta(
        "vender",
        "¿Cómo vendo una boleta?",
        ("vender", "vendo", "venta", "comprador", "boleta", "asignar"),
        "Abra su rifa, toque una boleta disponible (o búsquela por número) y llene los datos del comprador. Si ya "
        "le pagó, registre el valor y el medio de pago. Después puede avisarle por WhatsApp o por correo con el "
        "enlace a su boleta.",
    ),
    Pregunta(
        "abonos",
        "¿Cómo registro abonos y cuotas?",
        ("abono", "abonos", "cuota", "cuotas", "saldo", "debe", "atrasado", "atrasada"),
        "En la boleta vendida use «Registrar un pago»: puede ser un abono o el valor completo. RifaPlus suma los "
        "pagos, muestra lo que falta y qué cuotas están pagadas o vencidas. En la rifa, el filtro «Atrasadas» "
        "le muestra quién debe cuotas vencidas.",
    ),
    Pregunta(
        "vendedores",
        "¿Cómo manejo a mis vendedores?",
        ("vendedor", "vendedores", "comision", "comisiones", "liquidar", "liquidacion"),
        "En «Vendedores» agregue a cada uno con su porcentaje de comisión. Al vender, escoja quién vendió la "
        "boleta. En la ficha del vendedor verá su comisión ganada y podrá registrar los pagos hasta dejarlo a paz "
        "y salvo.",
    ),
    Pregunta(
        "ganador",
        "¿Cómo registro el resultado y el ganador?",
        ("ganador", "gano", "resultado", "sorteo", "loteria", "jugo", "premio"),
        "En su rifa, en «Premios y sorteos», escriba el número completo que cayó en la lotería. RifaPlus toma las "
        "últimas cifras, busca la boleta y aplica sus reglas (al día, pagada, acumulado). Luego puede avisarle al "
        "ganador y marcar el premio como entregado.",
    ),
    Pregunta(
        "editar",
        "¿Puedo corregir mi rifa?",
        ("editar", "corregir", "cambiar", "modificar", "error", "equivoque"),
        "Sí. En borrador puede cambiar todo con «Editar rifa». Ya publicada, con «Corregir datos» puede cambiar el "
        "nombre, la descripción, los premios que no han jugado y agregar premios secos. La fecha, el precio y las "
        "boletas no cambian, para proteger a quien ya compró.",
    ),
    Pregunta(
        "eliminar",
        "¿Cómo elimino una rifa?",
        ("eliminar", "borrar", "elimino", "borro", "quitar"),
        "Mientras la rifa no tenga boletas vendidas ni pagos, al final de su página está el botón «Eliminar rifa». "
        "Si ya tiene ventas, escríbanos por aquí y lo revisamos con usted.",
    ),
    Pregunta(
        "verificar",
        "¿Cómo verifica el comprador su boleta?",
        ("verificar", "qr", "codigo", "autentica", "falsa", "imprimir"),
        "Cada boleta tiene un código y un QR. El comprador lo escanea o lo escribe en «Verificar boleta» y ve "
        "que es auténtica, sus números, si está pagada y si ganó. En la boleta vendida, «Ver boleta para "
        "imprimir» la deja lista para imprimir o guardar en PDF.",
    ),
    Pregunta(
        "equipo",
        "¿Alguien me puede ayudar con mis rifas?",
        ("ayudante", "ayude", "equipo", "colaborador", "socio", "persona", "acceso", "compartir"),
        "Sí. En el menú, «Equipo», agregue a la persona con su nombre y su correo. Le llega una clave temporal para "
        "entrar con su propio usuario. Puede crear y editar rifas, vender y registrar pagos; no puede eliminar rifas "
        "ni manejar el equipo. Si deja de ayudarle, toque «Quitar acceso».",
    ),
    Pregunta(
        "vencer",
        "¿Qué pasa cuando se vence mi rifa?",
        ("vence", "vencio", "vencida", "bloqueada", "bloqueo", "renovar", "renovacion", "meses", "tiempo"),
        "Cada rifa se paga por un tiempo (por ejemplo 6 meses o 1 año) desde que se publica. Antes de vencer, "
        "RifaPlus le avisa en su panel y por correo. Si la rifa sigue, toque «Renovar» en su rifa y pague otro "
        "período. Si no renueva, la rifa se bloquea: no podrá vender ni registrar pagos hasta renovarla. Sus "
        "compradores sí pueden seguir verificando sus boletas.",
    ),
    Pregunta(
        "clave",
        "Olvidé o quiero cambiar mi clave",
        ("clave", "contrasena", "password", "olvide", "ingresar"),
        "Para cambiarla, en el menú toque «Cambiar clave». Si la olvidó, escríbanos por aquí desde otra cuenta o "
        "contacte a RifaPlus para restablecerla.",
    ),
]


def normalizar(texto: str) -> str:
    """Minúsculas y sin tildes, para comparar palabras: 'Comisión' -> 'comision'."""
    sin_tildes = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in sin_tildes if not unicodedata.combining(c))


def por_clave(clave: str) -> Pregunta | None:
    """La pregunta con esa clave (cuando el organizador toca un botón de pregunta frecuente)."""
    return next((p for p in PREGUNTAS if p.clave == clave), None)


def buscar(texto: str) -> Pregunta | None:
    """La pregunta que mejor coincide con lo que escribió el organizador, o None si no hay coincidencia clara."""
    palabras = set(normalizar(texto).replace("¿", " ").replace("?", " ").replace(",", " ").split())
    puntajes = sorted(
        ((sum(1 for p in pregunta.palabras if p in palabras), pregunta) for pregunta in PREGUNTAS), key=lambda x: -x[0]
    )
    mejor_puntaje, mejor = puntajes[0]
    empate = len(puntajes) > 1 and puntajes[1][0] == mejor_puntaje
    if mejor_puntaje >= 2 and not empate:
        return mejor
    if mejor_puntaje == 1 and not empate and len(palabras) <= 6:
        return mejor
    return None
