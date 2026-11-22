"""Pruebas de la API base: salud, municipios y ficha. Usan los datos inventados de tests/conftest.py."""


def test_health_con_datos(cliente):
    r = cliente.get("/health")
    assert r.status_code == 200
    assert r.json()["datos_cargados"] is True
    assert r.json()["municipios"] == 3


def test_health_sin_datos_no_falla(cliente_sin_datos):
    # /health siempre responde 200: sirve para saber si la API está viva aunque falten los datos
    r = cliente_sin_datos.get("/health")
    assert r.status_code == 200
    assert r.json()["datos_cargados"] is False
    assert "Elena" in r.json()["detalle"]


def test_sin_datos_devuelve_503_con_formato_estandar(cliente_sin_datos):
    r = cliente_sin_datos.get("/municipios")
    assert r.status_code == 503
    assert r.json()["error"] == "datos_no_disponibles"
    assert "mensaje" in r.json()


def test_listar_municipios(cliente):
    r = cliente.get("/municipios")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["total"] == 3 and len(cuerpo["municipios"]) == 3
    assert cuerpo["municipios"][0]["cod_ine"] in {"01001", "28001", "41001"}


def test_busqueda_sin_tildes_ni_mayusculas(cliente):
    r = cliente.get("/municipios", params={"provincia": "alava"})
    assert [m["cod_ine"] for m in r.json()["municipios"]] == ["01001"]
    r = cliente.get("/municipios", params={"q": "RIO seco"})
    assert [m["cod_ine"] for m in r.json()["municipios"]] == ["41001"]


def test_paginacion_y_total(cliente):
    r = cliente.get("/municipios", params={"limite": 2, "desplazamiento": 1})
    cuerpo = r.json()
    assert cuerpo["total"] == 3  # el total no depende de la página
    assert len(cuerpo["municipios"]) == 2


def test_parametros_invalidos(cliente):
    assert cliente.get("/municipios", params={"limite": 0}).status_code == 422
    assert cliente.get("/municipios", params={"limite": 500}).status_code == 422
    assert cliente.get("/municipios", params={"desplazamiento": -1}).status_code == 422


def test_municipio_conserva_el_cero_inicial(cliente):
    r = cliente.get("/municipios/01001")
    assert r.status_code == 200
    assert r.json()["nombre"] == "Villaverde Alta"


def test_municipio_inexistente_es_404_con_formato_estandar(cliente):
    r = cliente.get("/municipios/99999")
    assert r.status_code == 404
    assert r.json() == {
        "error": "municipio_no_encontrado",
        "mensaje": "No existe el municipio '99999'.",
    }


def test_codigo_ine_mal_formado_es_422(cliente):
    assert cliente.get("/municipios/1001").status_code == 422  # sin el cero inicial
    assert cliente.get("/municipios/abcde").status_code == 422


def test_ficha_con_trazabilidad(cliente):
    r = cliente.get("/municipios/28001/ficha")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["municipio"]["nombre"] == "Vallehondo"
    assert "parcela" in cuerpo["aviso_alcance"]
    ind = {i["id_indicador"]: i for i in cuerpo["indicadores"]}
    assert ind["suelo_ha"]["unidad"] == "ha"
    assert ind["suelo_ha"]["fuente"] == "Fuente 1"
    assert ind["suelo_ha"]["url_fuente"] == "u"
    assert ind["suelo_ha"]["limitaciones"] == "No equivale a suelo disponible"
    assert ind["suelo_ha"]["utilizable"] is True
    # Dato aproximado y provincial: se marca, pero se puede usar
    assert ind["estres"]["aproximado"] is True


def test_ficha_distingue_hueco_de_cero(cliente):
    ind = {i["id_indicador"]: i for i in cliente.get("/municipios/41001/ficha").json()["indicadores"]}
    # El CSV dice 0 en suelo, pero el estado avisa de que NO es un 0 real
    assert ind["suelo_ha"]["valor"] == 0.0
    assert ind["suelo_ha"]["utilizable"] is False
    assert "sin_poligonos" in ind["suelo_ha"]["motivo_no_utilizable"]
    # Un hueco es null, nunca 0
    assert ind["estres"]["valor"] is None
    assert ind["estres"]["utilizable"] is False


def test_ficha_inexistente(cliente):
    assert cliente.get("/municipios/99999/ficha").status_code == 404
