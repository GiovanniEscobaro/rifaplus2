"""Base de datos del superadministrador: solo lectura, claves ocultas y consultas seguras."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.seguridad import cifrar_clave
from app.main import app
from app.modulos.acceso.modelos import Usuario


@pytest.fixture
def admin(db):
    if not db.scalar(select(Usuario).where(Usuario.email == "datos@rifaplus.co")):
        db.add(
            Usuario(
                nombre="Giovanni",
                email="datos@rifaplus.co",
                password_hash=cifrar_clave("Admin2026"),
                rol="superadmin",
                organizador_id=None,
                debe_cambiar_clave=False,
            )
        )
        db.commit()
    c = TestClient(app)
    c.post("/ingresar", data={"email": "datos@rifaplus.co", "clave": "Admin2026"})
    return c


def test_lista_de_tablas(admin):
    pagina = admin.get("/admin/datos").text
    assert "organizadores" in pagina and "boletas" in pagina and "mensajes_soporte" in pagina


def test_ver_tabla_oculta_las_claves(admin, organizador):
    pagina = admin.get("/admin/datos/usuarios").text
    assert organizador.email in pagina and "•••" in pagina and "$2b$" not in pagina
    assert organizador.email in admin.get("/admin/datos/usuarios", params={"buscar": organizador.email}).text
    csv = admin.get("/admin/datos/usuarios.csv").content.decode("utf-8-sig")
    assert csv.startswith("id;") and "$2b$" not in csv
    assert admin.get("/admin/datos/no_existe", follow_redirects=False).status_code == 303


def test_consulta_de_solo_lectura(admin):
    r = admin.post("/admin/datos/consulta", data={"sql": "SELECT codigo, nombre FROM medios_pago ORDER BY orden"})
    assert r.status_code == 200 and "bre_b" in r.text


@pytest.mark.parametrize(
    "sql,mensaje",
    [
        ("DELETE FROM rifas", "SELECT o WITH"),
        ("SELECT 1; DELETE FROM rifas", "una sola consulta"),
        ("WITH x AS (DELETE FROM rifas RETURNING id) SELECT * FROM x", "DELETE"),
        ("SELECT nextval('rifas_id_seq')", "error"),
        ("SELECT * FROM tabla_que_no_existe", "error"),
    ],
)
def test_consultas_que_no_se_permiten(admin, sql, mensaje):
    r = admin.post("/admin/datos/consulta", data={"sql": sql})
    assert r.status_code == 422 and mensaje in r.text


def test_solo_para_superadmin(organizador):
    assert organizador.get("/admin/datos", follow_redirects=False).headers["location"] == "/panel"
    assert (
        organizador.post("/admin/datos/consulta", data={"sql": "SELECT 1"}, follow_redirects=False).status_code == 303
    )


def test_solo_se_ofrecen_los_medios_con_cuenta(admin, organizador, db):
    import datetime

    from sqlalchemy import update

    from app.modulos.pagos.modelos import CuentaCobro, MedioPago
    from app.modulos.rifas.modelos import Loteria

    db.execute(update(CuentaCobro).where(CuentaCobro.organizador_id.is_(None)).values(activa=False))  # aislar
    db.commit()
    bre_b = str(db.scalar(select(MedioPago.id).where(MedioPago.codigo == "bre_b")))
    admin.post("/admin/cuentas", data={"medio_pago_id": bre_b, "numero_cuenta": "3001234567", "titular": "Giovanni"})
    loteria = str(db.scalar(select(Loteria.id).where(Loteria.nombre == "Lotería de Boyacá")))
    r = organizador.post(
        "/panel/rifas/nueva",
        follow_redirects=False,
        data=dict(
            nombre="Rifa",
            premio_mayor="Bicicleta",
            loteria_id=loteria,
            opcion="2-4",
            valor_boleta="10000",
            fecha_sorteo=(datetime.date.today() + datetime.timedelta(days=20)).isoformat(),
            acepta_declaracion="true",
        ),
    )
    pagina = organizador.get(r.headers["location"].split("?")[0] + "/pagar").text
    opciones = pagina.split('name="medio_pago_id"')[1].split("</select>")[0]
    assert "Llave Bre-B" in opciones and "Nequi" not in opciones and "Daviplata" not in opciones
