"""Configuración de pruebas.

Las pruebas usan una base de datos PostgreSQL aparte, definida en DATABASE_URL_PRUEBAS.
¡Esa base se borra y se vuelve a crear en cada ejecución! Nunca apunte a la base real.

    DATABASE_URL_PRUEBAS=postgresql+psycopg://rifaplus:rifaplus@localhost:5432/rifaplus_pruebas pytest
"""

import os
import random
import re
import tempfile

import pytest

URL = os.environ.get("DATABASE_URL_PRUEBAS")
if not URL:
    pytest.exit("Defina DATABASE_URL_PRUEBAS con una base de datos exclusiva para pruebas.", returncode=2)
os.environ["DATABASE_URL"] = URL
os.environ["APP_ENTORNO"] = "desarrollo"
os.environ["CARPETA_ARCHIVOS"] = tempfile.mkdtemp(prefix="rifaplus-pruebas-")

from fastapi.testclient import TestClient  # noqa: E402

from app.core import semillas  # noqa: E402
from app.core.database import Base, SesionLocal, motor  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def base_de_datos():
    Base.metadata.drop_all(motor)
    Base.metadata.create_all(motor)
    with SesionLocal() as db:
        semillas.cargar(db)
    yield
    Base.metadata.drop_all(motor)


@pytest.fixture
def db():
    with SesionLocal() as sesion:
        yield sesion


@pytest.fixture
def cliente():
    return TestClient(app)


_contador = {"n": 0}


@pytest.fixture
def organizador(cliente):
    """Registra un organizador nuevo, cambia su clave y devuelve el cliente ya conectado."""
    _contador["n"] += 1
    email = f"organizador{_contador['n']}@prueba.com"
    r = cliente.post(
        "/registro",
        data=dict(
            tipo_persona="natural",
            nombre="Organizador de prueba",
            email=email,
            tipo_documento="CC",
            numero_documento=f"7{_contador['n']:07d}{random.randint(10, 99)}",
            celular="300 123 4567",
            mismo_numero="true",
            acepta_datos="true",
            acepta_terminos="true",
        ),
    )
    clave_temporal = re.search(r"<code[^>]*>([^<]+)</code>", r.text).group(1)
    cliente.post("/ingresar", data=dict(email=email, clave=clave_temporal))
    cliente.post(
        "/cambiar-clave",
        data=dict(clave_actual=clave_temporal, clave_nueva="RifaPlus2026", confirmacion="RifaPlus2026"),
    )
    cliente.email = email
    return cliente
