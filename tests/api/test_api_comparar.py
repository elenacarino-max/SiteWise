"""Pruebas de /comparar. Datos y reglas inventados (tests/api/conftest.py).

Notas esperadas (calculadas a mano en test_api_actividades.py):
  01001 -> atractivo 55,56 / riesgo 25,0 / cumple
  41001 -> atractivo 50,0 (parcial) / riesgo no evaluable / mínimos no evaluable
"""

import pytest

URL = "/comparar"


def test_compara_dos_municipios(cliente_con_reglas):
    r = cliente_con_reglas.get(URL, params={"municipios": ["01001", "41001"], "actividad": "logistica_prueba"})
    assert r.status_code == 200
    cuerpo = r.json()
    assert [f["cod_ine"] for f in cuerpo["resumen"]] == ["01001", "41001"]  # respeta el orden pedido
    a, b = cuerpo["resumen"]
    assert a["atractivo_nota"] == pytest.approx(55.56, abs=0.01)
    assert a["riesgo_nota"] == pytest.approx(25.0)
    assert a["cumple_minimos"] == "cumple"
    assert b["riesgo_nota"] is None and b["riesgo_estado"] == "no_evaluable"
    assert b["atractivo_estado"] == "calculada_parcial"
    assert b["cumple_minimos"] == "no_evaluable"
    assert cuerpo["reglas_provisionales"] is True
    assert "ganador" in cuerpo["aviso_comparacion"]
    assert len(cuerpo["evaluaciones"]) == 2


def test_tabla_de_indicadores_por_municipio(cliente_con_reglas):
    r = cliente_con_reglas.get(URL, params={"municipios": "01001,41001", "actividad": "logistica_prueba"})
    indicadores = {i["id_indicador"]: i for i in r.json()["indicadores"]}
    assert set(indicadores) == {"suelo_ha", "autovia_km", "estres"}
    assert indicadores["suelo_ha"]["uso"] == "atractivo" and indicadores["estres"]["uso"] == "riesgo"
    suelo = indicadores["suelo_ha"]["valores"]
    assert suelo["01001"]["valor"] == 50 and suelo["01001"]["utilizable"] is True
    # En 41001 el cero del suelo NO es un cero real: sale marcado como no utilizable.
    assert suelo["41001"]["utilizable"] is False
    assert "sin_poligonos_en_catalogo" in suelo["41001"]["motivo_no_utilizable"]


def test_acepta_tres_municipios_y_comas(cliente_con_reglas):
    r = cliente_con_reglas.get(URL, params={"municipios": "01001,28001,41001", "actividad": "logistica_prueba"})
    assert r.status_code == 200
    assert [f["cod_ine"] for f in r.json()["resumen"]] == ["01001", "28001", "41001"]


@pytest.mark.parametrize("municipios", [["01001"], ["01001", "28001", "41001", "99999"], ["01001", "01001"], ["1001", "28001"]])
def test_comparacion_invalida(cliente_con_reglas, municipios):
    r = cliente_con_reglas.get(URL, params={"municipios": municipios, "actividad": "logistica_prueba"})
    assert r.status_code == 400
    assert r.json()["error"] == "comparacion_invalida"


def test_municipio_inexistente(cliente_con_reglas):
    r = cliente_con_reglas.get(URL, params={"municipios": ["01001", "99999"], "actividad": "logistica_prueba"})
    assert r.status_code == 404
    assert r.json()["error"] == "municipio_no_encontrado"
    assert "99999" in r.json()["mensaje"]


def test_actividad_inexistente(cliente_con_reglas):
    r = cliente_con_reglas.get(URL, params={"municipios": ["01001", "28001"], "actividad": "no_existe"})
    assert r.status_code == 404
    assert r.json()["error"] == "actividad_no_encontrada"
