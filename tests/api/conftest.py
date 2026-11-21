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


@pytest.fixture
def cliente(directorio_datos):
    """Cliente de pruebas con los datos inventados (tests/conftest.py)."""
    from fastapi.testclient import TestClient
    from sitewise_api.config import Ajustes
    from sitewise_api.main import crear_app

    return TestClient(crear_app(Ajustes(directorio_datos)))


@pytest.fixture
def cliente_sin_datos(tmp_path):
    """Cliente cuya carpeta de datos no existe: simula no haber recibido la entrega."""
    from fastapi.testclient import TestClient
    from sitewise_api.config import Ajustes
    from sitewise_api.main import crear_app

    return TestClient(crear_app(Ajustes(tmp_path / "no_existe")))
