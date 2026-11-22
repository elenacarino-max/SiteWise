"""Pruebas del repositorio y el cargador de PostgreSQL.

Necesitan una base de datos real. Si no defino SITEWISE_TEST_DATABASE_URL (o falta psycopg), se omiten.
Cada prueba trabaja en su propio esquema, que borro al terminar, para no tocar nada mÃ¡s de la base.

Ejemplo:
    SITEWISE_TEST_DATABASE_URL=postgresql://usuario:clave@127.0.0.1:5432/sitewise python -m pytest -q
"""

import os
import uuid

import pytest

psycopg = pytest.importorskip("psycopg")

URL = os.environ.get("SITEWISE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="Define SITEWISE_TEST_DATABASE_URL para probar PostgreSQL")

from sitewise.db.cargador import ErrorCarga, cargar_csv
from sitewise.db.esquema import con_tiempo_limite, validar_esquema
from sitewise.db.postgres import RepositorioPostgres
from sitewise.db.repositorio import DatosNoDisponibles, RepositorioCSV


@pytest.fixture
def esquema():
    nombre = f"prueba_{uuid.uuid4().hex[:10]}"
    yield nombre
    with psycopg.connect(URL, autocommit=True) as conexion:
        conexion.execute(f"DROP SCHEMA IF EXISTS {nombre} CASCADE")


@pytest.fixture
def repo_pg(directorio_datos, esquema):
    cargar_csv(directorio_datos, URL, esquema)
    return RepositorioPostgres(URL, esquema)


def test_carga_devuelve_el_resumen(directorio_datos, esquema):
    resumen = cargar_csv(directorio_datos, URL, esquema)
    assert (resumen["municipios"], resumen["indicadores"], resumen["valores"]) == (3, 3, 9)


def test_cargar_dos_veces_no_duplica(directorio_datos, esquema):
    cargar_csv(directorio_datos, URL, esquema)
    cargar_csv(directorio_datos, URL, esquema)
    assert RepositorioPostgres(URL, esquema).info()["observaciones"] == 9


def test_info_dice_el_origen(repo_pg):
    assert repo_pg.info() == {"origen": "postgresql", "municipios": 3, "indicadores": 3, "observaciones": 9}


def test_conserva_el_cero_inicial(repo_pg):
    assert repo_pg.municipio("01001")["nombre"] == "Villaverde Alta"
    assert repo_pg.municipio("1001") is None


def test_da_lo_mismo_que_el_repositorio_csv(directorio_datos, repo_pg):
    csv = RepositorioCSV(directorio_datos)
    # Mismo orden y mismos datos en la bÃºsqueda, el maestro, las observaciones y el detalle.
    assert repo_pg.buscar_municipios() == csv.buscar_municipios()
    assert repo_pg.buscar_municipios(provincia="alava") == csv.buscar_municipios(provincia="alava")
    for cod in ("01001", "28001", "41001"):
        assert repo_pg.municipio(cod) == csv.municipio(cod)
        assert repo_pg.observaciones(cod) == csv.observaciones(cod)
        assert repo_pg.detalle_indicadores(cod) == csv.detalle_indicadores(cod)
    assert repo_pg.observaciones("99999") == {}


def test_un_hueco_es_none_y_no_cero(repo_pg):
    obs = repo_pg.observaciones("41001")
    assert obs["estres"].valor is None
    assert obs["estres"].estado == "pendiente"
    assert obs["suelo_ha"].valor == 0.0 and obs["suelo_ha"].estado == "sin_poligonos_en_catalogo"


def test_valores_que_apuntan_a_un_municipio_inexistente(directorio_datos, esquema):
    with (directorio_datos / "valores.csv").open("a", encoding="utf-8") as f:
        f.write("99999,suelo_ha,1,real,municipal,2020,f1,observado,m,u\n")
    with pytest.raises(ErrorCarga, match="no existe"):
        cargar_csv(directorio_datos, URL, esquema)


def test_una_carga_fallida_deja_los_datos_anteriores(directorio_datos, esquema):
    cargar_csv(directorio_datos, URL, esquema)
    with (directorio_datos / "valores.csv").open("a", encoding="utf-8") as f:
        f.write("99999,suelo_ha,1,real,municipal,2020,f1,observado,m,u\n")
    with pytest.raises(ErrorCarga):
        cargar_csv(directorio_datos, URL, esquema)
    assert RepositorioPostgres(URL, esquema).info()["observaciones"] == 9  # sigue como estaba


def test_filas_duplicadas(directorio_datos, esquema):
    with (directorio_datos / "valores.csv").open("a", encoding="utf-8") as f:
        f.write("01001,suelo_ha,1,real,municipal,2020,f1,observado,m,u\n")
    with pytest.raises(ErrorCarga, match="duplicadas"):
        cargar_csv(directorio_datos, URL, esquema)


def test_falta_una_columna_obligatoria(directorio_datos, esquema):
    (directorio_datos / "municipios.csv").write_text("nombre\nX\n", encoding="utf-8")
    with pytest.raises(ErrorCarga, match="cod_ine"):
        cargar_csv(directorio_datos, URL, esquema)


def test_columnas_que_no_guardo_se_avisan(directorio_datos, esquema):
    texto = (directorio_datos / "municipios.csv").read_text(encoding="utf-8").splitlines()
    nuevo = [texto[0] + ",extra"] + [linea + ",x" for linea in texto[1:]]
    (directorio_datos / "municipios.csv").write_text("\n".join(nuevo) + "\n", encoding="utf-8")
    resumen = cargar_csv(directorio_datos, URL, esquema)
    assert resumen["columnas_ignoradas"] == {"municipios": ["extra"]}


def test_base_sin_tablas(esquema):
    with pytest.raises(DatosNoDisponibles, match="cargador"):
        RepositorioPostgres(URL, esquema)


def test_no_se_puede_conectar():
    with pytest.raises(DatosNoDisponibles, match="conectarme"):
        RepositorioPostgres("postgresql://nadie@127.0.0.1:1/nada?connect_timeout=2")


@pytest.mark.parametrize("malo", ["public; DROP TABLE x", "Mayusculas", "con espacio", ""])
def test_esquema_no_valido(malo):
    with pytest.raises(ValueError):
        validar_esquema(malo)


def test_la_api_lee_de_postgres(directorio_datos, esquema):
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))
    from fastapi.testclient import TestClient
    from sitewise_api.config import Ajustes
    from sitewise_api.main import crear_app

    cargar_csv(directorio_datos, URL, esquema)
    reglas = directorio_datos / "reglas.csv"
    from tests.api.conftest import REGLAS_INVENTADAS

    reglas.write_text(REGLAS_INVENTADAS, encoding="utf-8")
    con_pg = TestClient(crear_app(Ajustes(directorio_datos, reglas, URL, esquema)))
    con_csv = TestClient(crear_app(Ajustes(directorio_datos, reglas)))

    assert con_pg.get("/health").json()["origen"] == "postgresql"
    assert con_csv.get("/health").json()["origen"] == "csv"
    for ruta in (
        "/municipios/01001/evaluacion/logistica_prueba",
        "/municipios/41001/ficha",
        "/actividades/logistica_prueba/ranking",
    ):
        assert con_pg.get(ruta).json() == con_csv.get(ruta).json()


def test_tiempo_limite_de_conexion():
    assert con_tiempo_limite("postgresql://u:p@h:5432/b") == "postgresql://u:p@h:5432/b?connect_timeout=10"
    assert con_tiempo_limite("postgresql://u@h/b?sslmode=disable").endswith("&connect_timeout=10")
    assert con_tiempo_limite("postgresql://u@h/b?connect_timeout=3").endswith("connect_timeout=3")
    assert con_tiempo_limite("host=h dbname=b") == "host=h dbname=b connect_timeout=10"


def test_postgis_si_la_base_lo_tiene(directorio_datos, esquema):
    with psycopg.connect(URL) as conexion:
        hay = conexion.execute("SELECT 1 FROM pg_available_extensions WHERE name = 'postgis'").fetchone()
    if hay is None:
        pytest.skip("Esta base de datos no tiene PostGIS")
    resumen = cargar_csv(directorio_datos, URL, esquema)
    assert resumen["postgis"] is True
    with psycopg.connect(URL) as conexion:
        distancia = conexion.execute(
            f"SELECT ST_Distance(a.geom, b.geom) / 1000 FROM {esquema}.municipios a, {esquema}.municipios b "
            "WHERE a.cod_ine = '01001' AND b.cod_ine = '28001'"
        ).fetchone()[0]
    assert 270 < distancia < 290  # los dos municipios de prueba están a unos 279 km en línea recta
    # El repositorio sigue funcionando igual con la columna extra.
    assert RepositorioPostgres(URL, esquema).municipio("01001")["nombre"] == "Villaverde Alta"
