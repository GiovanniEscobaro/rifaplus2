"""Reglas matemáticas de la rifa: reparto de números en boletas y búsqueda del ganador."""

import secrets
from dataclasses import dataclass

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.core.excepciones import ErrorNegocio
from app.core.seguridad import generar_codigo_verificacion
from app.modulos.pagos.modelos import Plan
from app.modulos.rifas.modelos import Boleta, NumeroBoleta, Rifa

CIFRAS_PERMITIDAS = (1, 2, 3, 4)


@dataclass(frozen=True)
class Opcion:
    """Una forma válida de armar una rifa: cuántas cifras, cuántos números por boleta y su plan."""

    cifras: int
    numeros_por_boleta: int
    boletas: int
    plan_id: int
    plan_nombre: str
    valor: int

    @property
    def clave(self) -> str:
        """Identificador de la opción en el formulario: 'cifras-números', por ejemplo '4-4'."""
        return f"{self.cifras}-{self.numeros_por_boleta}"

    @property
    def total_numeros(self) -> int:
        """Cantidad de números de la rifa: 10, 100, 1.000 o 10.000."""
        return 10**self.cifras

    @property
    def rango(self) -> str:
        """Rango para mostrar, por ejemplo '00 al 99'."""
        return f"{'0' * self.cifras} al {'9' * self.cifras}"


def calcular_boletas(cifras: int, numeros_por_boleta: int) -> int:
    """La rifa usa todos los números de sus cifras; la división entre boletas debe ser exacta."""
    if cifras not in CIFRAS_PERMITIDAS:
        raise ErrorNegocio("La rifa debe ser de 1, 2, 3 o 4 cifras.")
    if numeros_por_boleta < 1:
        raise ErrorNegocio("Cada boleta debe tener al menos un número.")
    total = 10**cifras
    if total % numeros_por_boleta:
        raise ErrorNegocio(
            f"No se puede: {total:,} números no se reparten exacto en boletas de {numeros_por_boleta} números.".replace(
                ",", "."
            )
        )
    return total // numeros_por_boleta


def opciones_disponibles(db: Session) -> list[Opcion]:
    """Todas las combinaciones válidas según los planes activos (se calculan, no se escriben a mano)."""
    planes = list(db.scalars(select(Plan).where(Plan.activo.is_(True))))
    if not planes:
        return []
    maximo_numeros = max(p.numeros_max for p in planes)
    opciones = []
    for cifras in CIFRAS_PERMITIDAS:
        total = 10**cifras
        for numeros in range(1, maximo_numeros + 1):
            if total % numeros:
                continue
            boletas = total // numeros
            for plan in planes:
                if plan.boletas_min <= boletas <= plan.boletas_max and plan.numeros_min <= numeros <= plan.numeros_max:
                    opciones.append(Opcion(cifras, numeros, boletas, plan.id, plan.nombre, int(plan.valor)))
                    break
    return sorted(opciones, key=lambda o: (o.boletas, o.numeros_por_boleta))


def buscar_opcion(db: Session, cifras: int, numeros_por_boleta: int) -> Opcion:
    """Busca la opción válida para esas cifras y números por boleta, o explica por qué no existe."""
    for opcion in opciones_disponibles(db):
        if opcion.cifras == cifras and opcion.numeros_por_boleta == numeros_por_boleta:
            return opcion
    calcular_boletas(cifras, numeros_por_boleta)  # da el mensaje exacto si la división no cuadra
    raise ErrorNegocio("Esa combinación de boletas no está disponible en ningún plan. Escoja una de las opciones.")


def repartir_numeros(cifras: int, total_numeros: int, series_por_boleta: int) -> list[list[str]]:
    """Mezcla los números de forma no predecible (secrets) y los reparte en boletas."""
    numeros = [str(n).zfill(cifras) for n in range(total_numeros)]
    secrets.SystemRandom().shuffle(numeros)
    return [sorted(numeros[i : i + series_por_boleta]) for i in range(0, total_numeros, series_por_boleta)]


def generar_boletas(db: Session, rifa: Rifa) -> None:
    """Crea todas las boletas y sus números. Se llama dentro de la transacción que crea la rifa."""
    repartos = repartir_numeros(rifa.cifras, rifa.total_numeros, rifa.series_por_boleta)
    un_numero = rifa.series_por_boleta == 1
    if un_numero:
        # Boletas de un solo número: la boleta ES su número (la boleta 07 juega el 07), en orden
        repartos = [[str(n).zfill(rifa.cifras)] for n in range(rifa.total_numeros)]
        consecutivos = list(range(rifa.total_numeros))
    else:
        consecutivos = list(range(1, len(repartos) + 1))
    codigos: set[str] = set()
    filas = []
    for consecutivo in consecutivos:
        codigo = generar_codigo_verificacion()
        while codigo in codigos:
            codigo = generar_codigo_verificacion()
        codigos.add(codigo)
        filas.append(
            {
                "rifa_id": rifa.id,
                "consecutivo": consecutivo,
                "codigo_verificacion": codigo,
                "formato": "virtual",
                "estado": "disponible",
            }
        )
    creadas = db.execute(insert(Boleta).returning(Boleta.id, Boleta.consecutivo), filas).all()
    id_por_consecutivo = {consecutivo: id_ for id_, consecutivo in creadas}
    db.execute(
        insert(NumeroBoleta),
        [
            {"rifa_id": rifa.id, "boleta_id": id_por_consecutivo[c], "numero": numero}
            for c, numeros in zip(consecutivos, repartos, strict=True)
            for numero in numeros
        ],
    )


def numero_jugado(rifa: Rifa, resultado_loteria: str) -> str:
    """Últimas cifras del resultado de la lotería según las cifras de la rifa."""
    digitos = "".join(c for c in resultado_loteria if c.isdigit())
    if len(digitos) < rifa.cifras:
        raise ErrorNegocio(f"El resultado debe tener al menos {rifa.cifras} dígitos.")
    return digitos[-rifa.cifras :]


def buscar_ganador(db: Session, rifa: Rifa, resultado_loteria: str) -> NumeroBoleta | None:
    """Número de boleta que tiene las últimas cifras del resultado de la lotería."""
    numero = numero_jugado(rifa, resultado_loteria)
    return db.scalar(select(NumeroBoleta).where(NumeroBoleta.rifa_id == rifa.id, NumeroBoleta.numero == numero))
