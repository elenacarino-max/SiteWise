"""Pruebas de /actividades y de la evaluación. Datos y reglas inventados (tests/api/conftest.py).

Percentiles calculados a mano con el rango medio, 100 * (menores + menores_o_iguales) / (2 * n):
  suelo_ha  (universo 50 y 30; el 0 de 41001 no cuenta)  -> 50 = 75    30 = 25
  autovia_km (80, 10, 40)                                -> 80 = 83,33  10 = 16,67  40 = 50
  estres    (10 y 20; el pendiente de 41001 no cuenta)   -> 10 = 25    20 = 75
"""

import pytest


def test_actividades_sin_reglas(cliente):
    r = cliente.get("/actividades")
    assert r.status_code == 200
    assert r.json()["actividades"] == []
    assert "Todavía no hay reglas" in r.json()["aviso"]


def test_actividades_con_reglas_provisionales(cliente_con_reglas):
    cuerpo = cliente_con_reglas.get("/actividades").json()
    [act] = cuerpo["actividades"]
    assert act["actividad"] == "logistica_prueba"
    assert act["estado_reglas"] == "provisionales"  # nadie las ha firmado
    assert (act["n_reglas"], act["n_minimos"], act["n_puntuables"]) == (3, 1, 3)
    assert "provisionales" in cuerpo["aviso"]


def test_evaluacion_completa(cliente_con_reglas):
    r = cliente_con_reglas.get("/municipios/01001/evaluacion/logistica_prueba")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["municipio"]["nombre"] == "Villaverde Alta"
    assert "no garantiza la aptitud" in cuerpo["aviso_alcance"]
    ev = cuerpo["evaluacion"]
    # atractivo = (2 * 75 + 1 * (100 - 83,33)) / 3 = 55,56 ; riesgo = 25
    assert ev["atractivo"]["estado"] == "calculada"
    assert ev["atractivo"]["nota"] == pytest.approx(55.56, abs=0.01)
    assert ev["riesgo"]["nota"] == pytest.approx(25.0)
    assert ev["cumple_minimos"] == "cumple"
    assert ev["reglas_provisionales"] is True
    assert len(ev["version_reglas"]) == 8
    # Cada componente explica de dónde sale la nota.
    assert {c["id_indicador"] for c in ev["atractivo"]["componentes"]} == {"suelo_ha", "autovia_km"}


def test_dato_que_falta_no_se_trata_como_cero(cliente_con_reglas):
    # 41001: suelo sin polígonos en el catálogo (mínimo no evaluable) y estrés pendiente.
    ev = cliente_con_reglas.get("/municipios/41001/evaluacion/logistica_prueba").json()["evaluacion"]
    assert ev["cumple_minimos"] == "no_evaluable"
    assert "suelo_ha" in ev["motivo_minimos"]
    assert ev["riesgo"]["estado"] == "no_evaluable"
    assert ev["riesgo"]["nota"] is None
    # Atractivo parcial: solo la autovía (40 km -> percentil 50, invertido 50), 1 de 3 de peso.
    assert ev["atractivo"]["estado"] == "calculada_parcial"
    assert ev["atractivo"]["nota"] == pytest.approx(50.0)
    assert ev["atractivo"]["confianza"] == pytest.approx(0.3333, abs=0.001)


def test_municipio_inexistente_en_evaluacion(cliente_con_reglas):
    r = cliente_con_reglas.get("/municipios/99999/evaluacion/logistica_prueba")
    assert r.status_code == 404
    assert r.json()["error"] == "municipio_no_encontrado"


def test_actividad_inexistente(cliente_con_reglas):
    r = cliente_con_reglas.get("/municipios/01001/evaluacion/no_existe")
    assert r.status_code == 404
    assert r.json()["error"] == "actividad_no_encontrada"


def test_evaluacion_sin_reglas_da_actividad_no_encontrada(cliente):
    r = cliente.get("/municipios/01001/evaluacion/logistica_prueba")
    assert r.status_code == 404
    assert r.json()["error"] == "actividad_no_encontrada"


def test_reglas_mal_escritas_devuelven_error_claro(directorio_datos):
    from fastapi.testclient import TestClient
    from sitewise_api.config import Ajustes
    from sitewise_api.main import crear_app

    ruta = directorio_datos / "reglas_rotas.csv"
    ruta.write_text(
        "actividad,id_indicador,uso_en_actividad,peso,operador\nx,suelo_ha,atractivo,2,=>\n",
        encoding="utf-8",
    )
    r = TestClient(crear_app(Ajustes(directorio_datos, ruta))).get("/actividades")
    assert r.status_code == 500
    assert r.json()["error"] == "reglas_invalidas"
    assert "línea 2" in r.json()["mensaje"]


def test_motivo_de_minimos_nombra_los_que_fallan_y_los_no_evaluables(directorio_datos):
    # Mínimo de suelo >= 100 ha: 28001 tiene 30 ha (no cumple) y la autovía no es mínimo;
    # añado un mínimo sobre "estres" que en 41001 está pendiente (no evaluable).
    from fastapi.testclient import TestClient
    from sitewise_api.config import Ajustes
    from sitewise_api.main import crear_app

    ruta = directorio_datos / "reglas_dos_minimos.csv"
    ruta.write_text(
        "actividad,id_indicador,uso_en_actividad,peso,es_requisito_minimo,operador,umbral,unidad,sentido\n"
        "a,suelo_ha,atractivo,1,si,>=,100,ha,directa\n"
        "a,estres,riesgo,1,si,<=,50,%,directa\n",
        encoding="utf-8",
    )
    cliente = TestClient(crear_app(Ajustes(directorio_datos, ruta)))
    # 01001: suelo 50 < 100 (no cumple); estres 10 <= 50 (cumple)
    ev = cliente.get("/municipios/01001/evaluacion/a").json()["evaluacion"]
    assert ev["cumple_minimos"] == "no_cumple"
    assert ev["motivo_minimos"] == "No cumple: suelo_ha."


def test_la_estimacion_de_agua_entra_en_el_calculo(cliente_con_datos_app):
    """Con valores_app.csv, 41001 pasa de "sin riesgo" a tener riesgo, marcado como aproximado."""
    cliente = cliente_con_datos_app
    assert cliente.get("/health").json()["valores_fichero"] == "valores_app.csv"
    ev = cliente.get("/municipios/41001/evaluacion/logistica_prueba").json()["evaluacion"]
    assert ev["riesgo"]["estado"] == "calculada" and ev["riesgo"]["nota"] is not None
    assert ev["riesgo"]["componentes"][0]["aproximado"] is True
    # El suelo sin polígonos sigue sin poder certificar el mínimo.
    assert ev["cumple_minimos"] == "no_evaluable"
    ficha = cliente.get("/municipios/41001/ficha").json()["indicadores"]
    estres = next(i for i in ficha if i["id_indicador"] == "estres")
    assert estres["estimado"] is True and estres["vecinos"] == 5 and estres["utilizable"] is True
