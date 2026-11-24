"""Preparo el entorno de las pruebas de la API.

La API vive en apps/api (no en src/), así que añado esa carpeta al camino de importación.
"""

import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi")  # si no está instalado el extra [api], se omiten estas pruebas
pytest.importorskip("httpx")

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "apps" / "api"))


# Reglas INVENTADAS sobre los indicadores inventados: no son las reglas reales del proyecto.
REGLAS_INVENTADAS = (
    "actividad,id_indicador,uso_en_actividad,peso,es_requisito_minimo,operador,umbral,unidad,sentido,"
    "justificacion,aprobado_por,fecha_aprobacion\n"
    "logistica_prueba,suelo_ha,atractivo,2,si,>=,10,ha,directa,inventada,,\n"
    "logistica_prueba,autovia_km,atractivo,1,,,,km,inversa,inventada,,\n"
    "logistica_prueba,estres,riesgo,1,,,,%,directa,inventada,,\n"
)


@pytest.fixture
def cliente(directorio_datos):
    """Cliente de pruebas con los datos inventados y SIN reglas (el fichero no existe)."""
    from fastapi.testclient import TestClient
    from sitewise_api.config import Ajustes
    from sitewise_api.main import crear_app

    return TestClient(crear_app(Ajustes(directorio_datos, directorio_datos / "no_hay_reglas.csv")))


@pytest.fixture
def cliente_con_reglas(directorio_datos):
    """Cliente de pruebas con los datos inventados y la actividad inventada `logistica_prueba`."""
    from fastapi.testclient import TestClient
    from sitewise_api.config import Ajustes
    from sitewise_api.main import crear_app

    ruta = directorio_datos / "reglas.csv"
    ruta.write_text(REGLAS_INVENTADAS, encoding="utf-8")
    return TestClient(crear_app(Ajustes(directorio_datos, ruta)))


@pytest.fixture
def cliente_con_datos_app(directorio_datos_app):
    """Cliente con datos inventados que incluyen un valores_app.csv (con una estimación de vecinos)."""
    from fastapi.testclient import TestClient
    from sitewise_api.config import Ajustes
    from sitewise_api.main import crear_app

    ruta = directorio_datos_app / "reglas.csv"
    ruta.write_text(REGLAS_INVENTADAS, encoding="utf-8")
    return TestClient(crear_app(Ajustes(directorio_datos_app, ruta)))


@pytest.fixture
def cliente_sin_datos(tmp_path):
    """Cliente cuya carpeta de datos no existe: simula no haber recibido la entrega."""
    from fastapi.testclient import TestClient
    from sitewise_api.config import Ajustes
    from sitewise_api.main import crear_app

    return TestClient(crear_app(Ajustes(tmp_path / "no_existe")))


@pytest.fixture
def cliente_con_perfiles(directorio_datos, directorio_perfiles):
    """Cliente con datos inventados, la actividad inventada y los perfiles inventados."""
    from fastapi.testclient import TestClient
    from sitewise_api.config import Ajustes
    from sitewise_api.main import crear_app

    ruta = directorio_datos / "reglas.csv"
    ruta.write_text(REGLAS_INVENTADAS, encoding="utf-8")
    return TestClient(crear_app(Ajustes(directorio_datos, ruta, directorio_perfiles=directorio_perfiles)))
