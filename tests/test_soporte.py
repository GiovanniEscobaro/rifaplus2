"""Chat de soporte: respuestas automáticas, paso a RifaPlus y respuesta del superadministrador."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.seguridad import cifrar_clave
from app.main import app
from app.modulos.acceso.modelos import Usuario
from app.modulos.soporte.preguntas import buscar


@pytest.fixture
def admin(db):
    if not db.scalar(select(Usuario).where(Usuario.email == "soporte@rifaplus.co")):
        db.add(
            Usuario(
                nombre="Giovanni",
                email="soporte@rifaplus.co",
                password_hash=cifrar_clave("Admin2026"),
                rol="superadmin",
                organizador_id=None,
                debe_cambiar_clave=False,
            )
        )
        db.commit()
    c = TestClient(app)
    c.post("/ingresar", data={"email": "soporte@rifaplus.co", "clave": "Admin2026"})
    return c


@pytest.mark.parametrize(
    "texto,clave",
    [
        ("¿cómo creo una rifa?", "crear"),
        ("cuánto cuesta", "precios"),
        ("pagué con la llave bre-b el plan", "publicar"),
        ("hola", None),
        ("necesito una factura a nombre de mi empresa por favor", None),
    ],
)
def test_el_asistente_reconoce_las_preguntas_comunes(texto, clave):
    encontrada = buscar(texto)
    assert (encontrada.clave if encontrada else None) == clave


def test_chat_con_respuestas_automaticas(organizador):
    inicio = organizador.get("/panel/soporte").json()
    assert inicio["mensajes"][0]["autor"] == "asistente" and len(inicio["preguntas"]) >= 10
    datos = organizador.post("/panel/soporte", json={"pregunta": "precios"}).json()
    assert datos["mensajes"][-1]["autor"] == "asistente" and "$19.900" in datos["mensajes"][-1]["texto"]
    datos = organizador.post("/panel/soporte", json={"texto": "¿cómo vendo una boleta?"}).json()
    assert "comprador" in datos["mensajes"][-1]["texto"] and datos["estado"] == "atendida"
    assert 'id="chat-soporte"' in organizador.get("/panel").text


def test_lo_que_no_sabe_pasa_a_rifaplus_y_usted_responde(organizador, admin):
    datos = organizador.post(
        "/panel/soporte", json={"texto": "Necesito factura electrónica a nombre de mi empresa"}
    ).json()
    assert datos["estado"] == "pendiente" and "equipo de RifaPlus" in datos["mensajes"][-1]["texto"]
    bandeja = admin.get("/admin/soporte").text
    assert "Por responder" in bandeja and "factura electrónica" in bandeja
    assert "consultas de soporte por responder" in admin.get("/admin").text
    conv_id = int(bandeja.split('href="/admin/soporte/')[1].split('"')[0])
    admin.post(f"/admin/soporte/{conv_id}", data={"texto": "Claro, se la enviamos hoy al correo."})
    datos = organizador.get("/panel/soporte").json()
    assert datos["mensajes"][-1]["autor"] == "rifaplus" and datos["sin_leer"] and datos["estado"] == "atendida"


def test_hablar_con_una_persona(organizador):
    datos = organizador.post("/panel/soporte", json={"persona": True}).json()
    assert datos["estado"] == "pendiente"
    assert organizador.post("/panel/soporte", json={"texto": "   "}).status_code == 422


def test_el_chat_es_solo_para_organizadores(cliente, admin):
    assert cliente.get("/panel/soporte", follow_redirects=False).status_code == 303
    assert admin.get("/panel/soporte", follow_redirects=False).status_code == 303
