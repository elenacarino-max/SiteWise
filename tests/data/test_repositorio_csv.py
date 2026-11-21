import pytest

from sitewise.db.repositorio import DatosNoDisponibles, RepositorioCSV
from sitewise.scoring.modelos import EstadoMinimo
from sitewise.scoring.motor import MotorPuntuacion
from sitewise.scoring.normalizacion import Normalizador
from sitewise.scoring.reglas import cargar_reglas


@pytest.fixture
def repo(directorio_datos):
    return RepositorioCSV(directorio_datos)


def test_info(repo):
    assert repo.info()["municipios"] == 3
    assert repo.info()["observaciones"] == 9


def test_falta_el_directorio(tmp_path):
    with pytest.raises(DatosNoDisponibles):
        RepositorioCSV(tmp_path / "no_existe")


def test_conserva_el_cero_inicial(repo):
    # Si pandas leyera cod_ine como número, "01001" pasaría a 1001.
    assert repo.municipio("01001")["nombre"] == "Villaverde Alta"
    assert repo.municipio("1001") is None


def test_municipio_inexistente(repo):
    assert repo.municipio("99999") is None


def test_busqueda_sin_acentos_ni_mayusculas(repo):
    total, encontrados = repo.buscar_municipios(provincia="alava")  # sin tilde
    assert total == 1 and encontrados[0]["cod_ine"] == "01001"
    total, encontrados = repo.buscar_municipios(q="VALLEHONDO")
    assert total == 1 and encontrados[0]["cod_ine"] == "28001"
    assert repo.buscar_municipios(ccaa="andalucia")[0] == 1


def test_paginacion(repo):
    total, pagina = repo.buscar_municipios(limite=2, desplazamiento=1)
    assert total == 3 and len(pagina) == 2


def test_observaciones_distinguen_hueco_de_cero(repo):
    obs = repo.observaciones("41001")
    assert obs["estres"].valor is None  # hueco (NaN) -> None, NO 0
    assert obs["estres"].estado == "pendiente"
    assert obs["suelo_ha"].valor == 0.0  # el CSV dice 0, pero el estado avisa
    assert obs["suelo_ha"].estado == "sin_poligonos_en_catalogo"
    assert repo.observaciones("99999") == {}


def test_detalle_con_trazabilidad(repo):
    detalle = {d["id_indicador"]: d for d in repo.detalle_indicadores("28001")}
    assert detalle["estres"]["estado"] == "aproximado"
    assert detalle["estres"]["nivel_origen"] == "provincial"
    assert detalle["suelo_ha"]["unidad"] == "ha"
    assert detalle["suelo_ha"]["limitaciones"] == "No equivale a suelo disponible"
    assert detalle["estres"]["limitaciones"] is None  # celda vacía -> None


def test_del_csv_al_motor(repo, tmp_path):
    """Prueba de punta a punta: datos -> percentiles -> evaluación de un municipio."""
    ruta = tmp_path / "reglas.csv"
    ruta.write_text(
        "actividad,id_indicador,uso_en_actividad,peso,es_requisito_minimo,operador,umbral,unidad,sentido\n"
        "demo,suelo_ha,atractivo,2,si,>=,10,ha,directa\n"
        "demo,estres,riesgo,1,no,,,%,directa\n",
        encoding="utf-8",
    )
    motor = MotorPuntuacion(cargar_reglas(ruta), Normalizador(repo.valores))

    sevilla = motor.evaluar("41001", "demo", repo.observaciones("41001"))
    assert sevilla.cumple_minimos == EstadoMinimo.NO_EVALUABLE  # sin polígonos: no es "no cumple"
    assert sevilla.riesgo.estado == "no_evaluable"  # su estrés está pendiente

    madrid = motor.evaluar("28001", "demo", repo.observaciones("28001"))
    assert madrid.cumple_minimos == EstadoMinimo.CUMPLE  # 30 ha >= 10
