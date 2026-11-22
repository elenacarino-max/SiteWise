"""Pruebas de ranking y mapa. Datos y reglas inventados (tests/api/conftest.py).

Notas (calculadas a mano; ver test_api_actividades.py):
  01001 Álava    -> atractivo 55,56 | riesgo 25,0 | mínimos cumple
  28001 Madrid   -> atractivo 44,44 | riesgo 75,0 | mínimos cumple
  41001 Sevilla  -> atractivo 50,00 (parcial) | riesgo sin nota | mínimos no_evaluable
"""

import pytest

RANKING = "/actividades/logistica_prueba/ranking"
MAPA = "/actividades/logistica_prueba/mapa"


def codigos(cuerpo):
    return [f["cod_ine"] for f in cuerpo["filas"]]


def test_ranking_por_atractivo_mayor_primero(cliente_con_reglas):
    cuerpo = cliente_con_reglas.get(RANKING).json()
    assert codigos(cuerpo) == ["01001", "41001", "28001"]
    assert [f["posicion"] for f in cuerpo["filas"]] == [1, 2, 3]
    assert cuerpo["filas"][0]["atractivo_nota"] == pytest.approx(55.56, abs=0.01)
    assert cuerpo["total"] == 3 and cuerpo["sin_nota"] == 0
    assert cuerpo["reglas_provisionales"] is True


def test_ranking_por_riesgo_menor_primero_y_deja_fuera_los_sin_nota(cliente_con_reglas):
    cuerpo = cliente_con_reglas.get(RANKING, params={"ordenar_por": "riesgo"}).json()
    assert codigos(cuerpo) == ["01001", "28001"]  # 25 antes que 75: menos riesgo es mejor
    assert cuerpo["total"] == 2
    assert cuerpo["sin_nota"] == 1  # 41001 no tiene nota de riesgo: no se inventa un 0


def test_peor_primero_invierte_el_orden(cliente_con_reglas):
    cuerpo = cliente_con_reglas.get(RANKING, params={"orden": "peor_primero"}).json()
    assert codigos(cuerpo) == ["28001", "41001", "01001"]


def test_filtro_cumple_minimos(cliente_con_reglas):
    cuerpo = cliente_con_reglas.get(RANKING, params={"cumple_minimos": "cumple"}).json()
    assert codigos(cuerpo) == ["01001", "28001"]
    cuerpo = cliente_con_reglas.get(RANKING, params={"cumple_minimos": "no_evaluable"}).json()
    assert codigos(cuerpo) == ["41001"]


def test_filtro_provincia_y_ccaa_sin_tildes(cliente_con_reglas):
    assert codigos(cliente_con_reglas.get(RANKING, params={"provincia": "alava"}).json()) == ["01001"]
    assert codigos(cliente_con_reglas.get(RANKING, params={"ccaa": "COMUNIDAD DE MADRID"}).json()) == ["28001"]


def test_paginacion(cliente_con_reglas):
    cuerpo = cliente_con_reglas.get(RANKING, params={"limite": 1, "desplazamiento": 1}).json()
    assert codigos(cuerpo) == ["41001"]
    assert cuerpo["filas"][0]["posicion"] == 2  # la posición cuenta desde el principio, no desde la página
    assert cuerpo["total"] == 3


def test_mapa_devuelve_todos_con_coordenadas(cliente_con_reglas):
    cuerpo = cliente_con_reglas.get(MAPA).json()
    assert cuerpo["total"] == 3
    madrid = next(f for f in cuerpo["filas"] if f["cod_ine"] == "28001")
    assert madrid["lat"] == pytest.approx(40.4) and madrid["lon"] == pytest.approx(-3.7)
    assert madrid["cumple_minimos"] == "cumple"
    sevilla = next(f for f in cuerpo["filas"] if f["cod_ine"] == "41001")
    assert sevilla["riesgo_nota"] is None and sevilla["riesgo_estado"] == "no_evaluable"


def test_mapa_con_filtro(cliente_con_reglas):
    cuerpo = cliente_con_reglas.get(MAPA, params={"cumple_minimos": "cumple"}).json()
    assert {f["cod_ine"] for f in cuerpo["filas"]} == {"01001", "28001"}


@pytest.mark.parametrize("ruta", ["ranking", "mapa"])
def test_actividad_inexistente(cliente_con_reglas, ruta):
    r = cliente_con_reglas.get(f"/actividades/no_existe/{ruta}")
    assert r.status_code == 404
    assert r.json()["error"] == "actividad_no_encontrada"


def test_valores_invalidos_se_rechazan(cliente_con_reglas):
    assert cliente_con_reglas.get(RANKING, params={"ordenar_por": "nota_final"}).status_code == 422
    assert cliente_con_reglas.get(RANKING, params={"cumple_minimos": "quizas"}).status_code == 422
    assert cliente_con_reglas.get(RANKING, params={"limite": 0}).status_code == 422
