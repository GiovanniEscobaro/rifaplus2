"""Verificación de identidad del organizador, equipo de colaboradores, cuentas de la rifa y menú para celulares."""

import datetime
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.seguridad import cifrar_clave
from app.main import app
from app.modulos.acceso.modelos import Organizador, Usuario
from app.modulos.rifas.modelos import Loteria, Rifa


@pytest.fixture
def admin(db):
    if not db.scalar(select(Usuario).where(Usuario.email == "verifica@rifaplus.co")):
        db.add(
            Usuario(
                nombre="Giovanni",
                email="verifica@rifaplus.co",
                password_hash=cifrar_clave("Admin2026"),
                rol="superadmin",
                organizador_id=None,
                debe_cambiar_clave=False,
            )
        )
        db.commit()
    c = TestClient(app)
    c.post("/ingresar", data={"email": "verifica@rifaplus.co", "clave": "Admin2026"})
    return c


def crear(organizador, db, nombre="Rifa", **extra):
    loteria = str(db.scalar(select(Loteria.id).where(Loteria.nombre == "Lotería de Boyacá")))
    datos = (
        dict(
            nombre=nombre,
            premio_mayor="Televisor",
            loteria_id=loteria,
            opcion="1-1",
            valor_boleta="10.000",
            fecha_sorteo=(datetime.date.today() + datetime.timedelta(days=30)).isoformat(),
            acepta_declaracion="true",
        )
        | extra
    )
    r = organizador.post("/panel/rifas/nueva", data=datos, follow_redirects=False)
    db.expire_all()
    return r.headers["location"].split("?")[0], db.scalars(select(Rifa).order_by(Rifa.id.desc())).first()


def org_de(db, cliente):
    db.expire_all()
    return db.scalar(select(Organizador).where(Organizador.email == cliente.email))


def test_la_primera_rifa_se_publica_sin_verificar_y_la_segunda_no(organizador, admin, db):
    url1, _ = crear(organizador, db, "Primera")
    organizador.post(f"{url1}/publicar")
    url2, rifa2 = crear(organizador, db, "Segunda")
    r = organizador.post(f"{url2}/publicar", follow_redirects=False)
    assert "aviso_error" in r.headers["location"]
    db.expire_all()
    assert db.get(Rifa, rifa2.id).estado == "borrador"
    assert "por verificar" in organizador.get("/panel").text
    org = org_de(db, organizador)
    assert "Marcar como verificado" in admin.get(f"/admin/organizadores/{org.id}").text
    admin.post(f"/admin/organizadores/{org.id}/verificacion", data={"accion": "verificar"})
    organizador.post(f"{url2}/publicar")
    db.expire_all()
    assert db.get(Rifa, rifa2.id).estado == "en_venta"
    assert "por verificar" not in organizador.get("/panel").text


def test_filtro_por_verificar(admin, organizador, db):
    pagina = admin.get("/admin/organizadores", params={"estado": "por_verificar"}).text
    assert organizador.email in pagina


def test_equipo_del_organizador(organizador, db):
    r = organizador.post("/panel/equipo", data={"nombre": "Laura Ayudante", "email": "laura.ayuda@correo.co"})
    clave = re.search(r"<code[^>]*>([^<]+)</code>", r.text).group(1)
    assert "Laura Ayudante" in r.text
    ayudante = TestClient(app)
    r = ayudante.post("/ingresar", data={"email": "laura.ayuda@correo.co", "clave": clave}, follow_redirects=False)
    assert r.headers["location"] == "/cambiar-clave"
    ayudante.post(
        "/cambiar-clave", data={"clave_actual": clave, "clave_nueva": "Ayudante2026", "confirmacion": "Ayudante2026"}
    )
    assert ayudante.get("/panel").status_code == 200
    assert ayudante.get("/panel/equipo", follow_redirects=False).headers["location"] == "/panel"
    url, rifa = crear(ayudante, db, "Rifa del ayudante")
    assert rifa.organizador_id == org_de(db, organizador).id  # trabaja sobre las rifas del organizador
    r = ayudante.post(f"{url}/eliminar", follow_redirects=False)
    assert "Solo%20el%20organizador" in r.headers["location"]
    colaborador_id = db.scalar(select(Usuario.id).where(Usuario.email == "laura.ayuda@correo.co"))
    organizador.post(f"/panel/equipo/{colaborador_id}", data={"activo": "false"})
    assert ayudante.get("/panel", follow_redirects=False).status_code == 303  # se le cerró la sesión


def test_no_se_repite_el_correo_del_equipo(organizador):
    r = organizador.post("/panel/equipo", data={"nombre": "Otra Persona", "email": organizador.email})
    assert r.status_code == 422 and "ya tiene una cuenta" in r.text


def test_cuentas_de_la_rifa(organizador, db):
    url, _ = crear(
        organizador,
        db,
        "Rifa con cuentas",
        valor_premio="50.000",
        seco_descripcion_1="Gorra",
        seco_loteria_id_1=str(db.scalar(select(Loteria.id).limit(1))),
        seco_valor_estimado_1="10.000",
        seco_fecha_juego_1=(datetime.date.today() + datetime.timedelta(days=10)).isoformat(),
    )
    pagina = organizador.get(url).text
    # 10 boletas × $10.000 = $100.000 − premios $60.000 − RifaPlus $0 = $40.000
    assert "Cuentas de la rifa" in pagina and "$100.000" in pagina and "$40.000" in pagina


def test_menu_para_celulares(organizador, cliente):
    assert 'class="boton-menu"' in organizador.get("/panel").text
    assert 'class="boton-menu"' in cliente.get("/").text
    assert "menu.js" in cliente.get("/").text
