"""Lo que cambia el superadministrador: planes y precios, loterías, valor del cobro de una rifa y prueba de correo."""

import datetime
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.seguridad import cifrar_clave
from app.main import app
from app.modulos.acceso.modelos import Organizador, Usuario
from app.modulos.pagos.modelos import CobroRifa, Plan
from app.modulos.rifas.modelos import Loteria, Rifa


@pytest.fixture
def admin(db):
    if not db.scalar(select(Usuario).where(Usuario.email == "catalogos@rifaplus.co")):
        db.add(
            Usuario(
                nombre="Giovanni",
                email="catalogos@rifaplus.co",
                password_hash=cifrar_clave("Admin2026"),
                rol="superadmin",
                organizador_id=None,
                debe_cambiar_clave=False,
            )
        )
        db.commit()
    c = TestClient(app)
    c.post("/ingresar", data={"email": "catalogos@rifaplus.co", "clave": "Admin2026"})
    return c


def crear_rifa(organizador, db, opcion="2-4"):
    loteria = str(db.scalar(select(Loteria.id).where(Loteria.nombre == "Lotería de Boyacá")))
    r = organizador.post(
        "/panel/rifas/nueva",
        follow_redirects=False,
        data=dict(
            nombre="Rifa del plan",
            premio_mayor="Televisor",
            loteria_id=loteria,
            opcion=opcion,
            valor_boleta="10000",
            fecha_sorteo=(datetime.date.today() + datetime.timedelta(days=20)).isoformat(),
            acepta_declaracion="true",
        ),
    )
    db.expire_all()
    return r.headers["location"].split("?")[0], db.scalars(select(Rifa).order_by(Rifa.id.desc())).first()


def tipo(db, boletas):
    return db.scalar(select(Plan).where(Plan.boletas_min == boletas, Plan.boletas_max == boletas))


def formulario_precios(admin):
    """Los datos actuales de la tabla de precios, tal como los enviaría el navegador."""
    import re as _re

    pagina = admin.get("/admin/planes").text
    datos = dict(_re.findall(r'name="(precio_\d+_\d+)"[^>]*value="([^"]*)"', pagina))
    datos |= {f"activo_{t}": "true" for t in _re.findall(r'name="activo_(\d+)" value="true" checked', pagina)}
    return datos


def test_tabla_de_precios_por_tipo_de_rifa(admin):
    pagina = admin.get("/admin/planes").text
    assert "Boletas que vende" in pagina and "Cifras por boleta" in pagina and "Números del sorteo" in pagina
    assert pagina.count('name="activo_') == 13 and "del 00 al 99" in pagina


def test_cambiar_el_precio_de_un_tipo_de_rifa(admin, organizador, db):
    from app.modulos.pagos.modelos import Duracion

    t = tipo(db, 25)
    seis = db.scalar(select(Duracion).where(Duracion.meses == 6))
    datos = formulario_precios(admin)
    original = datos[f"precio_{t.id}_{seis.id}"]
    r = admin.post("/admin/planes", data=datos | {f"precio_{t.id}_{seis.id}": "7.500"}, follow_redirects=False)
    assert r.status_code == 303
    _, rifa = crear_rifa(organizador, db, opcion="2-4")
    assert int(db.scalar(select(CobroRifa).where(CobroRifa.rifa_id == rifa.id)).valor) == 7500
    admin.post("/admin/planes", data=datos | {f"precio_{t.id}_{seis.id}": original})


def test_desactivar_un_tipo_de_rifa(admin, organizador, db):
    t = tipo(db, 1250)
    assert 'value="4-8"' in organizador.get("/panel/rifas/nueva").text
    datos = formulario_precios(admin)
    admin.post("/admin/planes", data={k: v for k, v in datos.items() if k != f"activo_{t.id}"})
    assert 'value="4-8"' not in organizador.get("/panel/rifas/nueva").text
    admin.post("/admin/planes", data=datos)


def test_el_organizador_ve_las_palabras_nuevas(organizador):
    pagina = organizador.get("/panel/rifas/nueva").text
    assert "cifras por boleta" in pagina and "Números del sorteo: del 00 al 99" in pagina


def test_agregar_loteria(admin, organizador):
    admin.post("/admin/loterias", data={"nombre": "Lotería del Atlántico", "dias": "Viernes", "activa": "true"})
    assert "Lotería del Atlántico" in organizador.get("/panel/rifas/nueva").text


def test_cortesia_en_el_cobro_de_una_rifa(admin, organizador, db):
    url, rifa = crear_rifa(organizador, db)
    r = admin.post(f"/admin/rifas/{rifa.id}/cobro", data={"valor": "0", "motivo": ""})
    assert r.status_code == 422 and "motivo" in r.text
    admin.post(f"/admin/rifas/{rifa.id}/cobro", data={"valor": "0", "motivo": "Cortesía de lanzamiento"})
    organizador.post(f"{url}/publicar")
    db.expire_all()
    assert db.get(Rifa, rifa.id).estado == "en_venta"


def test_prueba_de_correo_sin_configurar(admin):
    assert "El correo no está configurado" in admin.get("/admin").text
    r = admin.post("/admin/probar-correo")
    assert r.status_code == 422 and "SMTP_USUARIO" in r.text


def test_recuperar_clave_en_desarrollo_sin_correo(organizador, cliente):
    r = cliente.post("/recuperar-clave", data={"email": organizador.email})
    enlace = re.search(r'href="(/restablecer-clave/[^"]+)"', r.text).group(1)
    assert "Cree su clave nueva" in cliente.get(enlace).text


def test_superadmin_ve_organizador(admin, organizador, db):
    org = db.scalar(select(Organizador).where(Organizador.email == organizador.email))
    assert "Restablecer clave" in admin.get(f"/admin/organizadores/{org.id}").text


def test_borrar_datos_de_prueba(admin, organizador, db):
    from app.core import limpieza
    from app.modulos.acceso.modelos import Usuario as U

    crear_rifa(organizador, db, opcion="1-1")
    antes = limpieza.contar(db)
    assert antes["rifas"] >= 1 and antes["organizadores"] >= 1
    limpieza.borrar_datos_de_prueba(db)
    despues = limpieza.contar(db)
    assert all(v == 0 for v in despues.values())
    assert db.scalar(select(U).where(U.rol == "superadmin")) is not None  # el superadmin se conserva
    assert "Precios de las rifas" in admin.get("/admin").text  # sigue pudiendo entrar


def test_si_no_hay_tipos_de_rifa_se_pueden_crear(admin, db):
    from sqlalchemy import update

    db.execute(update(Plan).values(activo=False))
    db.commit()
    tipos = list(db.scalars(select(Plan).where(Plan.boletas_min == Plan.boletas_max)))
    ids = [t.id for t in tipos]
    # Simula la tabla vacía cambiando los tipos a planes por rango
    db.execute(update(Plan).where(Plan.id.in_(ids)).values(boletas_min=Plan.boletas_max - 1))
    db.commit()
    pagina = admin.get("/admin/planes").text
    assert "No hay tipos de rifa creados" in pagina
    admin.post("/admin/planes/crear-tipos")
    pagina = admin.get("/admin/planes").text
    assert pagina.count('name="activo_') == 13 and "No hay tipos de rifa" not in pagina


def test_la_base_no_deja_repetir_tipos_de_rifa(db):
    from sqlalchemy.exc import IntegrityError

    db.add(Plan(nombre="Repetido", boletas_min=100, boletas_max=100, numeros_min=1, numeros_max=1, valor=1))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_semillas_no_duplican(db):
    from app.core.semillas import cargar

    antes = db.scalar(select(func.count()).select_from(Plan))
    cargar(db)
    assert db.scalar(select(func.count()).select_from(Plan)) == antes
