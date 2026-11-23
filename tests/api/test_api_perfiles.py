"""Pruebas de los perfiles de municipios en la API (datos inventados)."""


def test_la_ficha_incluye_el_perfil(cliente_con_perfiles):
    perfil = cliente_con_perfiles.get("/municipios/28001/ficha").json()["perfil"]
    assert perfil["cluster"] == 1
    assert perfil["nombre"] == "Perfil de prueba B"
    assert "No es una nota de riesgo ni de atractivo" in perfil["aviso"]


def test_la_evaluacion_incluye_el_perfil_aparte_de_las_notas(cliente_con_perfiles):
    cuerpo = cliente_con_perfiles.get("/municipios/28001/evaluacion/logistica_prueba").json()
    assert cuerpo["perfil"]["nombre"] == "Perfil de prueba B"
    assert "riesgo" in cuerpo["evaluacion"] and "atractivo" in cuerpo["evaluacion"]
    assert "perfil" not in cuerpo["evaluacion"]  # el perfil no entra en las notas


def test_sin_perfiles_el_campo_es_null_y_todo_funciona(cliente):
    cuerpo = cliente.get("/municipios/28001/ficha").json()
    assert cuerpo["perfil"] is None
    assert cliente.get("/health").json()["perfiles_version"] is None


def test_health_dice_la_version_de_los_perfiles(cliente_con_perfiles):
    assert cliente_con_perfiles.get("/health").json()["perfiles_version"] == "v01"


def test_listar_perfiles(cliente_con_perfiles):
    cuerpo = cliente_con_perfiles.get("/perfiles").json()
    assert [p["nombre"] for p in cuerpo["perfiles"]] == ["Perfil de prueba A", "Perfil de prueba B"]
    assert cuerpo["perfiles"][1]["medianas"]["poblacion_2025"] == 200.0
    assert "No es una nota" in cuerpo["aviso"]


def test_similares(cliente_con_perfiles):
    cuerpo = cliente_con_perfiles.get("/municipios/28001/similares").json()
    assert cuerpo["perfil"]["cluster"] == 1
    assert cuerpo["total"] == 1
    assert [m["cod_ine"] for m in cuerpo["similares"]] == ["41001"]
    assert 350 < cuerpo["similares"][0]["distancia_km"] < 430


def test_similares_sin_ningun_otro_municipio_devuelve_lista_vacia(cliente_con_perfiles):
    cuerpo = cliente_con_perfiles.get("/municipios/01001/similares").json()
    assert cuerpo["total"] == 0 and cuerpo["similares"] == []


def test_similares_municipio_inexistente(cliente_con_perfiles):
    r = cliente_con_perfiles.get("/municipios/99999/similares")
    assert r.status_code == 404
    assert r.json()["error"] == "municipio_no_encontrado"


def test_similares_sin_perfiles_cargados(cliente):
    r = cliente.get("/municipios/28001/similares")
    assert r.status_code == 404
    assert r.json()["error"] == "perfil_no_disponible"


def test_similares_codigo_mal_escrito(cliente_con_perfiles):
    assert cliente_con_perfiles.get("/municipios/abc/similares").status_code == 422


def test_comparar_incluye_el_perfil_de_cada_municipio(cliente_con_perfiles):
    r = cliente_con_perfiles.get("/comparar?municipios=28001,41001&actividad=logistica_prueba").json()
    assert [e["perfil"]["cluster"] for e in r["evaluaciones"]] == [1, 1]
