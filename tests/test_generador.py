"""Reglas matemáticas de la rifa (no necesitan base de datos)."""

import pytest

from app.core.excepciones import ErrorNegocio
from app.modulos.rifas.generador import calcular_boletas, repartir_numeros


@pytest.mark.parametrize(
    "cifras,numeros,esperado",
    [(1, 1, 10), (1, 2, 5), (2, 4, 25), (2, 2, 50), (2, 1, 100), (3, 4, 250), (3, 1, 1000), (4, 4, 2500), (4, 8, 1250)],
)
def test_calcula_boletas_usando_todos_los_numeros(cifras, numeros, esperado):
    assert calcular_boletas(cifras, numeros) == esperado


@pytest.mark.parametrize("cifras,numeros", [(2, 3), (3, 3), (1, 3), (4, 3)])
def test_rechaza_division_inexacta(cifras, numeros):
    with pytest.raises(ErrorNegocio, match="no se reparten exacto"):
        calcular_boletas(cifras, numeros)


@pytest.mark.parametrize("cifras", [0, 5])
def test_rechaza_cifras_invalidas(cifras):
    with pytest.raises(ErrorNegocio):
        calcular_boletas(cifras, 1)


def test_reparto_usa_todos_los_numeros_sin_repetir():
    boletas = repartir_numeros(2, 100, 4)
    numeros = [n for b in boletas for n in b]
    assert len(boletas) == 25
    assert all(len(b) == 4 for b in boletas)
    assert sorted(numeros) == [f"{i:02d}" for i in range(100)]


def test_reparto_de_una_cifra():
    assert sorted(n for b in repartir_numeros(1, 10, 2) for n in b) == [str(i) for i in range(10)]


def test_reparto_es_aleatorio():
    assert repartir_numeros(3, 1000, 4) != repartir_numeros(3, 1000, 4)
