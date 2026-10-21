"""Fotos de premios: subida, vista pública, protección de comprobantes y vista previa de la boleta."""

import datetime
import io

from PIL import Image
from sqlalchemy import select

from app.modulos.rifas.modelos import Loteria, Rifa


def imagen(formato="JPEG") -> bytes:
    salida = io.BytesIO()
    Image.new("RGB", (40, 40), (200, 50, 50)).save(salida, formato)
    return salida.getvalue()


def datos(db, **extra):
    boyaca = str(db.scalar(select(Loteria.id).where(Loteria.nombre == "Lotería de Boyacá")))
    hoy = datetime.date.today()
    return (
        dict(
            nombre="Rifa con fotos",
            premio_mayor="Juego de cocina",
            loteria_id=boyaca,
            opcion="1-1",
            fecha_sorteo=(hoy + datetime.timedelta(days=30)).isoformat(),
            valor_boleta="10.000",
            acepta_declaracion="true",
            seco_descripcion_1="Licuadora",
            seco_loteria_id_1=boyaca,
            seco_fecha_juego_1=(hoy + datetime.timedelta(days=10)).isoformat(),
        )
        | extra
    )


def ultima(db):
    db.expire_all()
    return db.scalars(select(Rifa).order_by(Rifa.id.desc())).first()


def test_crear_rifa_con_fotos(organizador, db, cliente):
    r = organizador.post(
        "/panel/rifas/nueva",
        data=datos(db),
        follow_redirects=False,
        files={
            "foto_mayor": ("cocina.jpg", imagen(), "image/jpeg"),
            "seco_foto_1": ("licuadora.png", imagen("PNG"), "image/png"),
        },
    )
    assert r.status_code == 303
    rifa = ultima(db)
    mayor = next(p for p in rifa.premios if p.tipo == "mayor")
    seco = next(p for p in rifa.premios if p.tipo == "seco")
    assert mayor.foto_url.startswith("fotos/") and seco.foto_url.endswith(".png")
    assert cliente.get(f"/archivos/{mayor.foto_url}").content.startswith(b"\xff\xd8")
    assert f"/archivos/{mayor.foto_url}" in organizador.get(r.headers["location"].split("?")[0]).text


def test_foto_debe_ser_imagen(organizador, db):
    r = organizador.post(
        "/panel/rifas/nueva", data=datos(db), files={"foto_mayor": ("x.pdf", b"%PDF-1.4 x", "application/pdf")}
    )
    assert r.status_code == 422 and "JPG, PNG o WEBP" in r.text


def test_no_se_usan_fotos_ajenas_ni_se_exponen_comprobantes(organizador, db, cliente):
    organizador.post("/panel/rifas/nueva", data=datos(db, foto_mayor_actual="fotos/999999/ajena.jpg"))
    mayor = next(p for p in ultima(db).premios if p.tipo == "mayor")
    assert mayor.foto_url is None
    assert cliente.get("/archivos/comprobantes/1/algo.png").status_code == 404
    assert cliente.get("/archivos/fotos/../comprobantes/1/x.png").status_code == 404


def test_editar_conserva_y_cambia_la_foto(organizador, db):
    r = organizador.post(
        "/panel/rifas/nueva",
        data=datos(db),
        follow_redirects=False,
        files={"foto_mayor": ("cocina.jpg", imagen(), "image/jpeg")},
    )
    url = r.headers["location"].split("?")[0]
    rifa = ultima(db)
    foto = next(p for p in rifa.premios if p.tipo == "mayor").foto_url
    formulario = organizador.get(f"{url}/editar").text
    assert f'value="{foto}"' in formulario
    organizador.post(f"{url}/editar", data=datos(db, nombre="Rifa editada", foto_mayor_actual=foto))
    assert next(p for p in ultima(db).premios if p.tipo == "mayor").foto_url == foto
    organizador.post(f"{url}/publicar")
    mayor_id = next(p for p in ultima(db).premios if p.tipo == "mayor").id
    organizador.post(
        f"{url}/editar",
        data={"nombre": "Rifa editada", f"premio_descripcion_{mayor_id}": "Juego de cocina"},
        files={f"premio_foto_{mayor_id}": ("nueva.png", imagen("PNG"), "image/png")},
    )
    nueva = next(p for p in ultima(db).premios if p.tipo == "mayor").foto_url
    assert nueva != foto and nueva.endswith(".png")


def test_vista_previa_en_el_formulario(organizador):
    pagina = organizador.get("/panel/rifas/nueva").text
    assert "Así se verá la boleta" in pagina and 'data-previa="premio"' in pagina and "boleta.css" in pagina
