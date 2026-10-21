"""Superadministrador: organizadores, suspensión, cobros y borrados con confirmación."""

import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.seguridad import cifrar_clave
from app.main import app
from app.modulos.acceso.modelos import Organizador, Usuario
from app.modulos.pagos.modelos import CobroRifa
from app.modulos.rifas.modelos import Boleta, Loteria, Rifa


@pytest.fixture
def admin(db):
    if not db.scalar(select(Usuario).where(Usuario.email == "admin@rifaplus.co")):
        db.add(
            Usuario(
                nombre="Giovanni",
                email="admin@rifaplus.co",
                password_hash=cifrar_clave("Admin2026"),
                rol="superadmin",
                organizador_id=None,
                debe_cambiar_clave=False,
            )
        )
        db.commit()
    c = TestClient(app)
    c.post("/ingresar", data={"email": "admin@rifaplus.co", "clave": "Admin2026"})
    return c


def crear_rifa(organizador, db, opcion="1-1", nombre="Rifa del admin"):
    loteria = db.scalar(select(Loteria).where(Loteria.nombre == "Lotería de Boyacá"))
    r = organizador.post(
        "/panel/rifas/nueva",
        follow_redirects=False,
        data=dict(
            nombre=nombre,
            premio_mayor="Licuadora",
            loteria_id=str(loteria.id),
            opcion=opcion,
            valor_boleta="10000",
            fecha_sorteo=(datetime.date.today() + datetime.timedelta(days=15)).isoformat(),
            acepta_declaracion="true",
        ),
    )
    db.expire_all()
    return r.headers["location"].split("?")[0], db.scalars(select(Rifa).order_by(Rifa.id.desc())).first()


def org_de(db, cliente):
    db.expire_all()
    return db.scalar(select(Organizador).where(Organizador.email == cliente.email))


def test_superadmin_ingresa_desde_la_pagina_principal(admin, db):
    c = TestClient(app)
    assert 'href="/ingresar"' in c.get("/").text
    r = c.post("/ingresar", data={"email": "admin@rifaplus.co", "clave": "Admin2026"}, follow_redirects=False)
    assert r.headers["location"] == "/admin"
    assert "Ir al superadministrador" in c.get("/").text


def test_solo_el_superadmin_entra(organizador, admin):
    assert organizador.get("/admin", follow_redirects=False).headers["location"] == "/panel"
    assert admin.get("/panel", follow_redirects=False).headers["location"] == "/admin"
    assert "Resumen de RifaPlus" in admin.get("/admin").text


def test_lista_y_busqueda(organizador, admin):
    assert organizador.email in admin.get("/admin/organizadores", params={"buscar": organizador.email}).text
    assert "No hay organizadores" in admin.get("/admin/organizadores", params={"buscar": "zzz-no-existe"}).text


def test_suspender_y_reactivar(organizador, admin, db):
    o = org_de(db, organizador)
    admin.post(f"/admin/organizadores/{o.id}/estado", data={"nuevo": "suspendido"})
    assert organizador.get("/panel", follow_redirects=False).headers["location"] == "/ingresar"
    r = organizador.post("/ingresar", data={"email": organizador.email, "clave": "RifaPlus2026"})
    assert "suspendida" in r.text
    admin.post(f"/admin/organizadores/{o.id}/estado", data={"nuevo": "activo"})
    r = organizador.post(
        "/ingresar", data={"email": organizador.email, "clave": "RifaPlus2026"}, follow_redirects=False
    )
    assert r.headers["location"] == "/panel"


def nequi(db):
    from app.modulos.pagos.modelos import MedioPago

    return str(db.scalar(select(MedioPago.id).where(MedioPago.codigo == "nequi")))


def test_pago_del_plan_al_publicar_y_aprobacion(organizador, admin, db):
    admin.post("/admin/cuentas", data={"medio_pago_id": nequi(db), "numero_cuenta": "300 999 8877", "titular": "GE"})
    url, rifa = crear_rifa(organizador, db, opcion="2-4", nombre="Rifa de pago")
    pagar = organizador.get(f"{url}/pagar").text
    assert "$6.000" in pagar and "300 999 8877" in pagar
    r = organizador.post(f"{url}/pagar", data={"medio_pago_id": nequi(db)})
    assert r.status_code == 422 and "referencia" in r.text
    organizador.post(f"{url}/pagar", data={"medio_pago_id": nequi(db), "referencia": "M123456"})
    pagina = organizador.get(url).text
    assert "Pago en revisión" in pagina and "Editar rifa" not in pagina
    assert organizador.post(f"{url}/editar", data={}).status_code == 422
    cobro = db.scalar(select(CobroRifa).where(CobroRifa.rifa_id == rifa.id))
    assert "M123456" in admin.get("/admin/cobros").text
    r = admin.post(f"/admin/cobros/{cobro.id}", data={"accion": "rechazar"})
    assert r.status_code == 422 and "motivo" in r.text
    admin.post(f"/admin/cobros/{cobro.id}", data={"accion": "aprobar", "referencia": "M123456"})
    db.expire_all()
    assert db.get(Rifa, rifa.id).estado == "en_venta"


def test_pago_rechazado_se_puede_reenviar(organizador, admin, db):
    url, rifa = crear_rifa(organizador, db, opcion="2-4", nombre="Rifa rechazada")
    organizador.post(f"{url}/pagar", data={"medio_pago_id": nequi(db), "referencia": "X1"})
    cobro = db.scalar(select(CobroRifa).where(CobroRifa.rifa_id == rifa.id))
    admin.post(f"/admin/cobros/{cobro.id}", data={"accion": "rechazar", "motivo": "No llegó el dinero"})
    pagina = organizador.get(url).text
    assert "No llegó el dinero" in pagina and "Enviar el pago de nuevo" in pagina
    organizador.post(f"{url}/pagar", data={"medio_pago_id": nequi(db), "referencia": "X2"})
    assert "X2" in admin.get("/admin/cobros").text


def test_rifa_sin_enviar_pago_no_aparece_en_revision(organizador, admin, db):
    crear_rifa(organizador, db, opcion="2-4", nombre="Rifa sin pagar")
    assert "Rifa sin pagar" not in admin.get("/admin/cobros").text


def test_eliminar_rifa_exige_escribir_su_nombre(organizador, admin, db):
    url, rifa = crear_rifa(organizador, db, nombre="Rifa para borrar")
    organizador.post(f"{url}/publicar")
    boleta = db.scalar(select(Boleta).where(Boleta.rifa_id == rifa.id, Boleta.consecutivo == 2))
    organizador.post(
        f"{url}/boletas/{boleta.id}/vender",
        data={
            "tipo_documento": "CC",
            "numero_documento": "998877",
            "nombre": "Ana Ruiz",
            "celular": "3001112222",
            "whatsapp": "3001112222",
            "email": "a@a.co",
            "direccion": "Calle 1 # 2-3",
            "ciudad": "Soledad",
            "monto": "10000",
            "medio_pago_id": "1",
        },
    )
    r = admin.post(f"/admin/rifas/{rifa.id}/eliminar", data={"confirmacion": "otra cosa"})
    assert r.status_code == 422 and "escriba exactamente" in r.text
    rifa_id = rifa.id
    admin.post(f"/admin/rifas/{rifa_id}/eliminar", data={"confirmacion": "rifa para borrar"})
    db.expire_all()
    assert db.get(Rifa, rifa_id) is None


def test_eliminar_organizador(organizador, admin, db):
    _, rifa = crear_rifa(organizador, db)
    o = org_de(db, organizador)
    r = admin.post(f"/admin/organizadores/{o.id}/eliminar", data={"confirmacion": o.email})
    assert r.status_code == 422 and "Primero elimine las rifas" in r.text
    admin.post(f"/admin/rifas/{rifa.id}/eliminar", data={"confirmacion": rifa.nombre})
    organizador_id, email = o.id, o.email
    admin.post(f"/admin/organizadores/{organizador_id}/eliminar", data={"confirmacion": email})
    db.expire_all()
    assert db.get(Organizador, organizador_id) is None
    r = organizador.post("/ingresar", data={"email": organizador.email, "clave": "RifaPlus2026"})
    assert r.status_code == 401


def test_llave_bre_b_para_pagar_el_plan(organizador, admin, db):
    from app.modulos.pagos.modelos import MedioPago

    bre_b = str(db.scalar(select(MedioPago.id).where(MedioPago.codigo == "bre_b")))
    admin.post("/admin/cuentas", data={"medio_pago_id": bre_b, "numero_cuenta": "@GESOFTWARE", "titular": "GE"})
    url, _ = crear_rifa(organizador, db, opcion="2-4", nombre="Rifa Bre-B")
    pagina = organizador.get(f"{url}/pagar").text
    assert "Llave Bre-B" in pagina and "@GESOFTWARE" in pagina
    r = organizador.post(f"{url}/pagar", data={"medio_pago_id": bre_b, "referencia": "BREB-77"}, follow_redirects=False)
    assert r.status_code == 303
