"""Pruebas del endpoint de municipios cercanos (datos inventados)."""

from fastapi.testclient import TestClient
from sitewise_api.config import Ajustes
from sitewise_api.main import crear_app


def test_cercanos_ordenados_por_posicion(cliente_con_perfiles):
    r = cliente_con_perfiles.get("/municipios/28001/cercanos")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["municipio"]["cod_ine"] == "28001"
    assert [m["cod_ine"] for m in cuerpo["cercanos"]] == ["41001", "01001"]
    assert [m["posicion"] for m in cuerpo["cercanos"]] == [1, 2]
    assert cuerpo["cercanos"][0]["distancia_km"] == 12.5
    assert cuerpo["cercanos"][0]["nombre"]  # trae los datos del municipio


def test_cercanos_no_depende_del_perfil(directorio_datos, directorio_perfiles):
    # 41001 tiene perfil, pero los cercanos salen igual aunque no hubiera perfiles
    carpeta = directorio_perfiles
    solo = carpeta.parent / "solo_cercanos"
    solo.mkdir(exist_ok=True)
    (solo / "municipios_cercanos_v01.csv").write_text(
        (carpeta / "municipios_cercanos_v01.csv").read_text(encoding="utf-8"), encoding="utf-8"
    )
    cliente = TestClient(crear_app(Ajustes(directorio_datos, directorio_datos / "no.csv", directorio_perfiles=solo)))
    assert cliente.get("/municipios/28001/cercanos").status_code == 200
    assert cliente.get("/municipios/28001/similares").status_code == 404


def test_cercanos_municipio_inexistente(cliente_con_perfiles):
    r = cliente_con_perfiles.get("/municipios/99999/cercanos")
    assert r.status_code == 404
    assert r.json()["error"] == "municipio_no_encontrado"


def test_cercanos_municipio_sin_filas(cliente_con_perfiles):
    r = cliente_con_perfiles.get("/municipios/01001/cercanos")
    assert r.status_code == 404
    assert r.json()["error"] == "cercanos_no_disponibles"


def test_cercanos_sin_fichero(cliente):
    r = cliente.get("/municipios/28001/cercanos")
    assert r.status_code == 404
    assert r.json()["error"] == "cercanos_no_disponibles"
