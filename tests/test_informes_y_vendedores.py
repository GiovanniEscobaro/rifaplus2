"""Informes con filtros y descarga, liquidación de vendedores y boleta individual."""

import datetime
import re

import pytest
from sqlalchemy import select

from app.modulos.pagos.modelos import MedioPago
from app.modulos.rifas.modelos import Boleta, Loteria, Rifa


@pytest.fixture
def escenario(organizador, db):
    """Rifa gratis de 10 boletas a $20.000 con un vendedor al 10 % y dos ventas."""
    loteria = db.scalar(select(Loteria.id).where(Loteria.nombre == "Lotería de Boyacá"))
    hoy = datetime.date.today()
    r = organizador.post(
        "/panel/rifas/nueva",
        follow_redirects=False,
        data=dict(
            nombre="Rifa informes",
            premio_mayor="Moto eléctrica",
            valor_premio="5.000.000",
            loteria_id=str(loteria),
            fecha_sorteo=(hoy + datetime.timedelta(days=30)).isoformat(),
            opcion="1-1",
            valor_boleta="20.000",
            acepta_declaracion="true",
            seco_descripcion_1="Licuadora",
            seco_loteria_id_1=str(loteria),
            seco_valor_estimado_1="500.000",
            seco_fecha_juego_1=(hoy + datetime.timedelta(days=10)).isoformat(),
        ),
    )
    url = r.headers["location"].split("?")[0]
    organizador.post(f"{url}/publicar")
    organizador.post(
        "/panel/vendedores",
        data={
            "nombre": "Ana Gómez",
            "tipo_documento": "CC",
            "numero_documento": "55443322",
            "celular": "3005556677",
            "comision_porcentaje": "10",
            "llave_bre_b": "@VENDEDOR",
        },
    )
    db.expire_all()
    rifa = db.scalars(select(Rifa).order_by(Rifa.id.desc())).first()
    vendedor_id = re.search(r'href="/panel/vendedores/(\d+)"', organizador.get("/panel/vendedores").text).group(1)
    efectivo = str(db.scalar(select(MedioPago.id).where(MedioPago.codigo == "efectivo")))

    def vender(n, nombre, doc, ciudad, monto, vendedor=""):
        b = db.scalar(select(Boleta).where(Boleta.rifa_id == rifa.id, Boleta.consecutivo == n))
        organizador.post(
            f"{url}/boletas/{b.id}/vender",
            data={
                "tipo_documento": "CC",
                "numero_documento": doc,
                "nombre": nombre,
                "celular": "3001112222",
                "whatsapp": "3001112222",
                "email": f"{doc}@c.co",
                "direccion": "Calle 1 # 2-3",
                "ciudad": ciudad,
                "vendedor_id": vendedor,
                "monto": monto,
                "medio_pago_id": efectivo,
            },
        )
        return b

    b1 = vender(1, "Pepito Pérez", "111111", "Soledad", "20.000", vendedor_id)
    vender(2, "Luisa Díaz", "222222", "Barranquilla", "5.000", vendedor_id)
    vender(3, "Carlos Ruiz", "333333", "Soledad", "20.000")
    return url, rifa, vendedor_id, efectivo, b1


def test_premios_con_valor_y_visibles(organizador, escenario, db):
    url, rifa, *_ = escenario
    seco = next(p for p in rifa.premios if p.tipo == "seco")
    assert int(seco.valor_estimado) == 500000
    assert "Moto eléctrica" in organizador.get("/panel").text
    pagina = organizador.get(url).text
    assert "Moto eléctrica" in pagina and "$5.000.000" in pagina


def test_informe_por_ciudad_vendedor_y_estado(organizador, escenario):
    _, rifa, vendedor_id, *_ = escenario
    por_ciudad = organizador.get("/panel/informes", params={"ciudad": "soledad"}).text
    assert "Pepito Pérez" in por_ciudad and "Carlos Ruiz" in por_ciudad and "Luisa Díaz" not in por_ciudad
    por_vendedor = organizador.get("/panel/informes", params={"vendedor": vendedor_id}).text
    assert "Carlos Ruiz" not in por_vendedor and "$25.000" in por_vendedor
    deben = organizador.get("/panel/informes", params={"estado": "deben"}).text
    assert "Luisa Díaz" in deben and "Pepito Pérez" not in deben
    assert organizador.get("/panel/compradores", params={"buscar": "pepito"}, follow_redirects=False).status_code == 303


def test_informe_en_excel(organizador, escenario):
    r = organizador.get("/panel/informes.csv", params={"rifa": str(escenario[1].id)})
    assert r.headers["content-disposition"].startswith("attachment")
    texto = r.content.decode("utf-8-sig")
    assert texto.splitlines()[0].startswith("Rifa;Boleta;Números;Comprador") and "Luisa Díaz" in texto


def test_liquidacion_del_vendedor_llega_a_cero(organizador, escenario):
    _, _, vendedor_id, efectivo, _ = escenario
    pagina = organizador.get(f"/panel/vendedores/{vendedor_id}").text
    assert "$25.000" in pagina and "Le debe $2.500" in pagina  # 10 % de $25.000
    r = organizador.post(f"/panel/vendedores/{vendedor_id}/pagos", data={"monto": "3.000", "medio_pago_id": efectivo})
    assert r.status_code == 422 and "supera lo que se le debe" in r.text
    organizador.post(f"/panel/vendedores/{vendedor_id}/pagos", data={"monto": "1.000", "medio_pago_id": efectivo})
    assert "Le debe $1.500" in organizador.get(f"/panel/vendedores/{vendedor_id}").text
    organizador.post(f"/panel/vendedores/{vendedor_id}/pagos", data={"monto": "1.500", "medio_pago_id": efectivo})
    assert "A paz y salvo" in organizador.get(f"/panel/vendedores/{vendedor_id}").text
    assert "A paz y salvo" in organizador.get("/panel/vendedores").text


def test_cambiar_comision_del_vendedor(organizador, escenario):
    vendedor_id = escenario[2]
    organizador.post(
        f"/panel/vendedores/{vendedor_id}", data={"comision_porcentaje": "20", "activo": "true", "llave_bre_b": "@ANA"}
    )
    assert "$5.000" in organizador.get(f"/panel/vendedores/{vendedor_id}").text  # 20 % de $25.000


def test_boleta_individual(organizador, escenario, cliente):
    url, _, _, _, b1 = escenario
    imprimible = organizador.get(f"{url}/boletas/{b1.id}/imprimir").text
    assert "Moto eléctrica" in imprimible and "Licuadora" in imprimible and "111111" in imprimible
    assert "<svg" in imprimible and "Boleta pagada" in imprimible
    publica = cliente.get(f"/boleta/{b1.codigo_verificacion}").text
    assert "Pepito P." in publica and "111111" not in publica and "Pérez" not in publica


def test_enviar_por_correo_y_vista_previa(organizador, escenario, cliente):
    url, _, _, _, b1 = escenario
    pagina = organizador.get(f"{url}/boletas/{b1.id}").text
    correo = re.search(r'href="(mailto:[^"]+)"', pagina).group(1)
    assert correo.startswith("mailto:111111@c.co?subject=") and "/boleta/" in correo
    assert "Enviar por correo" in organizador.get(f"{url}/boletas/{b1.id}/imprimir").text
    publica = cliente.get(f"/boleta/{b1.codigo_verificacion}").text
    assert 'property="og:title" content="Boleta 1 · Rifa informes"' in publica
    assert "Premio mayor: Moto eléctrica" in publica and "rifaplus-vista-previa.png" in publica
    assert "Enviar por correo" not in publica
    assert 'property="og:title" content="RifaPlus' in cliente.get("/").text


def test_la_llave_bre_b_del_vendedor_es_obligatoria(organizador):
    datos = {"nombre": "Sin Llave", "tipo_documento": "CC", "numero_documento": "12121212", "celular": "3001231234"}
    r = organizador.post("/panel/vendedores", data=datos)
    assert r.status_code == 422 and "llave" in r.text.lower()
    r = organizador.post("/panel/vendedores", data=datos | {"llave_bre_b": "@SINLLAVE"}, follow_redirects=False)
    assert r.status_code == 303
    vendedor_id = re.findall(r'href="/panel/vendedores/(\d+)"', organizador.get("/panel/vendedores").text)[-1]
    assert "Páguele a su llave Bre-B" in organizador.get(f"/panel/vendedores/{vendedor_id}").text
