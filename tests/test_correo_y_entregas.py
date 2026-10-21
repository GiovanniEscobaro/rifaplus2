"""Correos (clave temporal, olvidé mi clave, avisos), restablecer clave por el superadmin y entregas de vendedores."""

import datetime
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.seguridad import cifrar_clave
from app.main import app
from app.modulos.acceso.modelos import Organizador, Usuario
from app.modulos.pagos.modelos import MedioPago
from app.modulos.rifas.modelos import Boleta, Loteria, Rifa


@pytest.fixture
def correos(monkeypatch):
    """Captura los correos en lugar de enviarlos."""
    enviados = []

    def falso(destino, asunto, texto):
        enviados.append((destino, asunto, texto))
        return True

    monkeypatch.setattr("app.modulos.acceso.notificaciones.enviar", falso)
    monkeypatch.setattr("app.core.correo.enviar", falso)
    return enviados


@pytest.fixture
def admin(db):
    if not db.scalar(select(Usuario).where(Usuario.email == "jefe@rifaplus.co")):
        db.add(
            Usuario(
                nombre="Giovanni",
                email="jefe@rifaplus.co",
                password_hash=cifrar_clave("Admin2026"),
                rol="superadmin",
                organizador_id=None,
                debe_cambiar_clave=False,
            )
        )
        db.commit()
    c = TestClient(app)
    c.post("/ingresar", data={"email": "jefe@rifaplus.co", "clave": "Admin2026"})
    return c


def test_la_clave_temporal_se_envia_al_correo(cliente, correos):
    cliente.post(
        "/registro",
        data=dict(
            tipo_persona="natural",
            nombre="Ana Torres",
            email="ana@correo.co",
            tipo_documento="CC",
            numero_documento="5566778899",
            celular="3001234567",
            mismo_numero="true",
            acepta_datos="true",
            acepta_terminos="true",
        ),
    )
    destino, asunto, texto = correos[-1]
    assert destino == "ana@correo.co" and "clave temporal" in asunto.lower() and "Clave temporal:" in texto


def test_olvide_mi_clave(organizador, correos, cliente):
    r = cliente.post("/recuperar-clave", data={"email": organizador.email})
    assert "le enviamos un enlace" in r.text
    token = re.search(r"/restablecer-clave/(\S+)", correos[-1][2]).group(1)
    assert "Cree su clave nueva" in cliente.get(f"/restablecer-clave/{token}").text
    r = cliente.post(
        f"/restablecer-clave/{token}",
        data={"clave_nueva": "Nueva2026x", "confirmacion": "Nueva2026x"},
        follow_redirects=False,
    )
    assert r.headers["location"] == "/ingresar?clave_cambiada=1"
    r = cliente.post("/ingresar", data={"email": organizador.email, "clave": "Nueva2026x"}, follow_redirects=False)
    assert r.headers["location"] == "/panel"
    assert "ya se usó o venció" in cliente.get(f"/restablecer-clave/{token}").text


def test_olvide_mi_clave_no_revela_si_el_correo_existe(cliente, correos):
    r = cliente.post("/recuperar-clave", data={"email": "nadie@ningunlado.co"})
    assert "le enviamos un enlace" in r.text and not correos


def test_el_superadmin_restablece_la_clave(organizador, admin, db, correos):
    org = db.scalar(select(Organizador).where(Organizador.email == organizador.email))
    r = admin.post(f"/admin/organizadores/{org.id}/restablecer-clave")
    clave = re.search(r"clave temporal es <code[^>]*>([^<]+)</code>", r.text).group(1)
    assert correos[-1][0] == organizador.email and clave in correos[-1][2]
    nuevo = TestClient(app)
    r = nuevo.post("/ingresar", data={"email": organizador.email, "clave": clave}, follow_redirects=False)
    assert r.headers["location"] == "/cambiar-clave"


def test_avisos_al_superadmin(organizador, correos, db, monkeypatch):
    avisos = []
    monkeypatch.setattr("app.modulos.soporte.rutas.avisar_admin", lambda a, t: avisos.append(a))
    monkeypatch.setattr("app.modulos.rifas.rutas.avisar_admin", lambda a, t: avisos.append(a))
    organizador.post("/panel/soporte", json={"texto": "Necesito una factura electrónica para mi fundación"})
    loteria = str(db.scalar(select(Loteria.id).where(Loteria.nombre == "Lotería de Boyacá")))
    r = organizador.post(
        "/panel/rifas/nueva",
        follow_redirects=False,
        data=dict(
            nombre="Rifa aviso",
            premio_mayor="Televisor",
            loteria_id=loteria,
            opcion="2-4",
            valor_boleta="10000",
            fecha_sorteo=(datetime.date.today() + datetime.timedelta(days=20)).isoformat(),
            acepta_declaracion="true",
        ),
    )
    url = r.headers["location"].split("?")[0]
    medio = organizador.get(f"{url}/pagar").text.split('<option value="')[2].split('"')[0]
    organizador.post(f"{url}/pagar", data={"medio_pago_id": medio, "referencia": "R-1"})
    assert any("Consulta de soporte" in a for a in avisos) and any("Pago por revisar" in a for a in avisos)


def test_entregas_de_efectivo_del_vendedor(organizador, db):
    loteria = str(db.scalar(select(Loteria.id).where(Loteria.nombre == "Lotería de Boyacá")))
    r = organizador.post(
        "/panel/rifas/nueva",
        follow_redirects=False,
        data=dict(
            nombre="Rifa efectivo",
            premio_mayor="Televisor",
            loteria_id=loteria,
            opcion="1-1",
            valor_boleta="20.000",
            fecha_sorteo=(datetime.date.today() + datetime.timedelta(days=20)).isoformat(),
            acepta_declaracion="true",
        ),
    )
    url = r.headers["location"].split("?")[0]
    organizador.post(f"{url}/publicar")
    organizador.post(
        "/panel/vendedores",
        data={
            "nombre": "Luis Pérez",
            "tipo_documento": "CC",
            "numero_documento": "88776655",
            "celular": "3005551122",
            "llave_bre_b": "3005551122",
        },
    )
    vendedor_id = re.findall(r'href="/panel/vendedores/(\d+)"', organizador.get("/panel/vendedores").text)[-1]
    db.expire_all()
    rifa = db.scalars(select(Rifa).order_by(Rifa.id.desc())).first()
    medio = lambda c: str(db.scalar(select(MedioPago.id).where(MedioPago.codigo == c)))  # noqa: E731
    for n, codigo, doc in ((1, "efectivo", "1111"), (2, "nequi", "2222")):
        b = db.scalar(select(Boleta).where(Boleta.rifa_id == rifa.id, Boleta.consecutivo == n))
        organizador.post(
            f"{url}/boletas/{b.id}/vender",
            data={
                "tipo_documento": "CC",
                "numero_documento": doc,
                "nombre": "Cliente Prueba",
                "celular": "3001112222",
                "whatsapp": "3001112222",
                "email": f"{doc}@c.co",
                "direccion": "Calle 1 # 2-3",
                "ciudad": "Soledad",
                "vendedor_id": vendedor_id,
                "monto": "20.000",
                "medio_pago_id": medio(codigo),
            },
        )
    pagina = organizador.get(f"/panel/vendedores/{vendedor_id}").text
    assert "cobró en efectivo" in pagina and pagina.count("$20.000") >= 2  # solo cuenta el pago en efectivo
    r = organizador.post(
        f"/panel/vendedores/{vendedor_id}/entregas",
        data={"rifa_id": str(rifa.id), "monto": "25.000", "medio_pago_id": medio("efectivo")},
    )
    assert r.status_code == 422 and "supera" in r.text
    organizador.post(
        f"/panel/vendedores/{vendedor_id}/entregas",
        data={"rifa_id": str(rifa.id), "monto": "20.000", "medio_pago_id": medio("efectivo")},
    )
    pagina = organizador.get(f"/panel/vendedores/{vendedor_id}").text
    assert "Entrega registrada" not in pagina and "Registrar entrega" not in pagina  # ya no tiene nada por entregar


def test_terminos_y_versiculos(cliente):
    terminos = cliente.get("/terminos").text
    assert "Reembolsos" in terminos and "por completar" in terminos
    inicio = cliente.get("/").text
    assert "Colosenses 3:23" in inicio and "Proverbios 16:3" in inicio
