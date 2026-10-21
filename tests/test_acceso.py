"""Registro, primer ingreso con cambio de clave obligatorio y bloqueo por intentos fallidos."""

import re


def registrar(cliente, email, **extra):
    datos = (
        dict(
            tipo_persona="natural",
            nombre="Giovanni Prueba",
            email=email,
            tipo_documento="CC",
            numero_documento=str(abs(hash(email)) % 10**10 + 10**9),
            celular="300 123 4567",
            mismo_numero="true",
            acepta_datos="true",
            acepta_terminos="true",
        )
        | extra
    )
    return cliente.post("/registro", data=datos)


def clave_de(respuesta):
    return re.search(r"<code[^>]*>([^<]+)</code>", respuesta.text).group(1)


def test_inicio_muestra_los_planes(cliente):
    r = cliente.get("/")
    assert r.status_code == 200
    assert "$6.000" in r.text and "$299.900" in r.text and "Administramos rifas, no rifamos" in r.text


def test_registro_exitoso(cliente):
    r = registrar(cliente, "nuevo@prueba.com")
    assert "Su cuenta está creada" in r.text


def test_registro_rechaza_correo_repetido(cliente):
    registrar(cliente, "repetido@prueba.com")
    r = registrar(cliente, "REPETIDO@prueba.com")
    assert r.status_code == 422 and "Ya existe una cuenta" in r.text


def test_registro_exige_aceptar_politica_de_datos(cliente):
    r = registrar(cliente, "sinpolitica@prueba.com", acepta_datos="")
    assert r.status_code == 422 and "tratamiento de datos" in r.text


def test_registro_exige_aceptar_terminos(cliente):
    r = registrar(cliente, "sinterminos@prueba.com", acepta_terminos="")
    assert r.status_code == 422 and "términos y condiciones" in r.text


def test_registro_guarda_las_aceptaciones(cliente, db):
    from sqlalchemy import select

    from app.modulos.acceso.modelos import Usuario
    from app.modulos.legal.modelos import Aceptacion

    registrar(cliente, "aceptaciones@prueba.com")
    usuario_id = db.scalar(select(Usuario.id).where(Usuario.email == "aceptaciones@prueba.com"))
    documentos = set(db.scalars(select(Aceptacion.documento).where(Aceptacion.usuario_id == usuario_id)))
    assert {"terminos", "tratamiento_datos"} <= documentos


def test_paginas_legales(cliente):
    assert "no es operador, gestor ni organizador" in cliente.get("/terminos").text
    assert "Ley 1581" in cliente.get("/tratamiento-de-datos").text


def test_primer_ingreso_obliga_a_cambiar_la_clave(cliente):
    clave = clave_de(registrar(cliente, "primer@prueba.com"))
    r = cliente.post("/ingresar", data=dict(email="primer@prueba.com", clave=clave), follow_redirects=False)
    assert r.headers["location"] == "/cambiar-clave"
    assert cliente.get("/panel", follow_redirects=False).headers["location"] == "/cambiar-clave"

    r = cliente.post("/cambiar-clave", data=dict(clave_actual=clave, clave_nueva="abc", confirmacion="abc"))
    assert "al menos 8" in r.text
    r = cliente.post(
        "/cambiar-clave", data=dict(clave_actual=clave, clave_nueva="Segura2026", confirmacion="Segura2027")
    )
    assert "no coinciden" in r.text
    r = cliente.post(
        "/cambiar-clave",
        data=dict(clave_actual=clave, clave_nueva="Segura2026", confirmacion="Segura2026"),
        follow_redirects=False,
    )
    assert r.headers["location"] == "/panel?bienvenida=1"
    assert "Todavía no tiene rifas" in cliente.get("/panel").text


def test_cerrar_sesion(organizador):
    organizador.post("/salir")
    assert organizador.get("/panel", follow_redirects=False).headers["location"] == "/ingresar"


def test_bloqueo_tras_cinco_intentos_fallidos(organizador):
    organizador.post("/salir")
    for _ in range(5):
        organizador.post("/ingresar", data=dict(email=organizador.email, clave="incorrecta"))
    r = organizador.post("/ingresar", data=dict(email=organizador.email, clave="RifaPlus2026"))
    assert "bloqueada" in r.text


def test_campos_de_clave_tienen_ojito(cliente):
    assert "ver-clave.js" in cliente.get("/ingresar").text


def test_versiculo_en_el_pie(cliente):
    assert "Proverbios 16:3" in cliente.get("/").text


def test_health_responde_ok(cliente):
    r = cliente.get("/health")
    assert r.status_code == 200 and r.text == "OK"


def test_database_url_acepta_postgresql_simple():
    from app.core.config import Configuracion

    cfg = Configuracion(database_url="postgresql://usuario:clave@postgres:5432/rifaplus", _env_file=None)
    assert cfg.database_url == "postgresql+psycopg://usuario:clave@postgres:5432/rifaplus"


def test_produccion_exige_claves_reales():
    import pytest as _pytest
    from pydantic import ValidationError

    from app.core.config import Configuracion

    with _pytest.raises(ValidationError, match="CLAVE_SECRETA"):
        Configuracion(
            app_entorno="produccion",
            clave_secreta="corta",
            app_url="https://rifaplus.gedev.co",
            database_url="postgresql://u:c@postgres:5432/rifaplus",
            _env_file=None,
        )


def test_el_documento_es_obligatorio_y_unico(cliente):
    r = registrar(cliente, "sindoc@correo.co", tipo_documento="", numero_documento="")
    assert r.status_code == 422 and "tipo de documento" in r.text.lower()
    registrar(cliente, "uno@correo.co", numero_documento="1.098.765.432")
    r = registrar(cliente, "dos@correo.co", numero_documento="1098765432")
    assert r.status_code == 422 and "Ya existe una cuenta con ese número de documento" in r.text
